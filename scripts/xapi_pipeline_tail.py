"""Utility for tailing the xAPI ingestion pipeline end-to-end.

Run this script to watch three signals:

1. Recent statements accepted by the FastAPI/Cloud Function ingress.
2. Messages flowing through the Pub/Sub topic.
3. Rows materializing in the BigQuery `statements` table.

Requires Google Cloud credentials with Pub/Sub subscriber and BigQuery
read permissions, plus network access to the FastAPI service if the
recent-statements endpoint is enabled. Execute from the project root:

    PYTHONPATH=. python scripts/xapi_pipeline_tail.py \
        --api-base https://your-cloud-run-url

Use Ctrl+C to exit; the diagnostic Pub/Sub subscription is cleaned up
automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Set

import httpx
from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import bigquery, pubsub_v1
from google.cloud.pubsub_v1.types import ExpirationPolicy
from google.protobuf import duration_pb2

from app.config.gcp_config import get_gcp_config


def utc_timestamp() -> str:
    """Return a short UTC timestamp for log lines."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def emit(kind: str, message: str, details: Optional[str] = None) -> None:
    """Print a single monitoring line to stdout."""
    line = f"{utc_timestamp()} [{kind}] {message}"
    if details:
        line = f"{line} | {details}"
    print(line, flush=True)


class PubSubTail:
    """Tail Pub/Sub messages using a disposable subscription."""

    def __init__(
        self,
        publisher_project: str,
        topic_name: str,
        credentials,
        *,
        subscription_prefix: str = "xapi-tail",
        ack_deadline_seconds: int = 30,
        expiration_seconds: int = 900,
    ) -> None:
        self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        self.topic_path = self.subscriber.topic_path(publisher_project, topic_name)
        unique_suffix = uuid.uuid4().hex[:10]
        subscription_id = f"{subscription_prefix}-{unique_suffix}"
        self.subscription_path = self.subscriber.subscription_path(
            publisher_project, subscription_id
        )
        self.ack_deadline_seconds = ack_deadline_seconds
        self.expiration_seconds = expiration_seconds
        self._future = None

    def ensure_subscription(self) -> None:
        """Create the diagnostic subscription if it does not exist."""
        ttl = duration_pb2.Duration(seconds=self.expiration_seconds)
        expiration_policy = ExpirationPolicy(ttl=ttl)

        try:
            self.subscriber.create_subscription(
                request={
                    "name": self.subscription_path,
                    "topic": self.topic_path,
                    "ack_deadline_seconds": self.ack_deadline_seconds,
                    "expiration_policy": expiration_policy,
                    "labels": {"purpose": "diagnostic-tail"},
                }
            )
            emit(
                "PUBSUB",
                "Created temporary subscription",
                details=self.subscription_path,
            )
        except AlreadyExists:
            emit("PUBSUB", "Reusing existing subscription", self.subscription_path)

    def _handle_message(self, message: pubsub_v1.subscriber.message.Message) -> None:
        published = message.publish_time.isoformat() if message.publish_time else ""
        try:
            payload = json.loads(message.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None

        statement_id = None
        actor = None
        verb = None
        if isinstance(payload, dict):
            statement_id = payload.get("id")
            actor_data = payload.get("actor") or {}
            actor = (
                actor_data.get("name")
                or (actor_data.get("account") or {}).get("name")
                or actor_data.get("mbox")
            )
            verb = (payload.get("verb") or {}).get("id")

        details = f"id={statement_id or 'n/a'}"
        if actor:
            details = f"{details} actor={actor}"
        if verb:
            details = f"{details} verb={verb}"
        if published:
            details = f"{details} published={published}"

        emit("PUBSUB", f"Message {message.message_id} acked", details)
        message.ack()

    def start(self) -> None:
        """Start streaming messages from the diagnostic subscription."""
        self.ensure_subscription()
        self._future = self.subscriber.subscribe(
            self.subscription_path,
            callback=self._handle_message,
            flow_control=pubsub_v1.types.FlowControl(max_messages=10, max_bytes=5_000_000),
        )
        emit("PUBSUB", "Listening for messages", self.subscription_path)

    def close(self) -> None:
        """Stop the subscription and remove it from Pub/Sub."""
        if self._future is not None:
            self._future.cancel()
            try:
                self._future.result(timeout=5)
            except Exception:
                pass
        try:
            self.subscriber.delete_subscription(request={"subscription": self.subscription_path})
            emit("PUBSUB", "Deleted temporary subscription", self.subscription_path)
        except NotFound:
            emit("PUBSUB", "Subscription already removed", self.subscription_path)
        except Exception as exc:
            emit("ERROR", "Failed to delete subscription", str(exc))
        finally:
            self.subscriber.close()


async def poll_recent_statements(
    api_base: str,
    *,
    interval: float,
    seen_ids: Set[str],
    http_timeout: float = 10.0,
) -> None:
    """Poll the `/api/xapi/recent` endpoint for new ingress events."""

    url = api_base.rstrip("/") + "/api/xapi/recent"
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        while True:
            try:
                response = await client.get(url, params={"limit": 50})
                if response.status_code == 200:
                    data = response.json()
                    statements: Iterable[Dict[str, Any]] = data.get("statements", [])
                    for entry in statements:
                        payload = entry.get("payload") or {}
                        statement_id = entry.get("statement_id") or payload.get("id")
                        if not statement_id or statement_id in seen_ids:
                            continue
                        seen_ids.add(statement_id)
                        actor_data = payload.get("actor") or {}
                        actor = (
                            actor_data.get("name")
                            or (actor_data.get("account") or {}).get("name")
                            or actor_data.get("mbox")
                        )
                        verb = (payload.get("verb") or {}).get("id")
                        emit(
                            "INGEST",
                            f"Statement {statement_id} accepted",
                            details=f"actor={actor or 'n/a'} verb={verb or 'n/a'}",
                        )
                else:
                    emit("WARN", "Recent statements endpoint returned", str(response.status_code))
            except Exception as exc:
                emit("ERROR", "Failed to poll recent statements", str(exc))

            # Prevent unbounded growth of the seen set
            if len(seen_ids) > 500:
                for _ in range(len(seen_ids) - 400):
                    seen_ids.pop()

            await asyncio.sleep(interval)


async def poll_bigquery(
    client: bigquery.Client,
    *,
    dataset: str,
    table: str,
    project: str,
    interval: float,
    seen_ids: Set[str],
    limit: int = 25,
) -> None:
    """Poll BigQuery for freshly inserted statements."""

    query = (
        "SELECT statement_id, timestamp, stored, verb_id, actor_id "
        "FROM `{project}.{dataset}.{table}` "
        "ORDER BY stored DESC LIMIT @limit"
    ).format(project=project, dataset=dataset, table=table)

    while True:
        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
            )

            def _run_query():
                return list(client.query(query, job_config=job_config).result())

            rows = await asyncio.to_thread(_run_query)

            for row in rows:
                statement_id = row.statement_id
                if statement_id in seen_ids:
                    continue
                seen_ids.add(statement_id)
                stored = row.stored.isoformat() if row.stored else ""
                verb = row.verb_id or ""
                actor = row.actor_id or ""
                details = f"actor={actor or 'n/a'} verb={verb or 'n/a'} stored={stored or 'n/a'}"
                emit("BIGQUERY", f"Row materialized for {statement_id}", details)
        except Exception as exc:
            emit("ERROR", "Failed to poll BigQuery", str(exc))

        if len(seen_ids) > 500:
            for _ in range(len(seen_ids) - 400):
                seen_ids.pop()

        await asyncio.sleep(interval)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tail xAPI ingestion pipeline events")
    parser.add_argument(
        "--api-base",
        help="Base URL for the FastAPI service (e.g. https://service.run.app)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Polling interval for API and BigQuery checks (seconds)",
    )
    parser.add_argument(
        "--bigquery-interval",
        type=float,
        default=10.0,
        help="Polling interval for BigQuery checks (seconds)",
    )
    parser.add_argument(
        "--bigquery-limit",
        type=int,
        default=25,
        help="Number of recent rows to inspect on each BigQuery poll",
    )
    parser.add_argument(
        "--topic",
        help="Pub/Sub topic name (defaults to configured GCP_PUBSUB_TOPIC)",
    )
    parser.add_argument(
        "--dataset",
        help="BigQuery dataset (defaults to configured dataset)",
    )
    parser.add_argument(
        "--table",
        default="statements",
        help="BigQuery table name to monitor (default: statements)",
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Disable the FastAPI recent statements poller",
    )
    parser.add_argument(
        "--no-pubsub",
        action="store_true",
        help="Disable the Pub/Sub tailer",
    )
    parser.add_argument(
        "--no-bigquery",
        action="store_true",
        help="Disable the BigQuery poller",
    )
    return parser


async def run_tail(args: argparse.Namespace) -> None:
    gcp_config = get_gcp_config()

    topic = args.topic or gcp_config.pubsub_topic
    dataset = args.dataset or gcp_config.bigquery_dataset
    project = gcp_config.project_id

    tasks = []
    pubsub_tail: Optional[PubSubTail] = None

    if not args.no_api:
        if not args.api_base:
            emit("WARN", "API poller disabled (missing --api-base)")
        else:
            tasks.append(
                asyncio.create_task(
                    poll_recent_statements(
                        args.api_base,
                        interval=args.poll_interval,
                        seen_ids=set(),
                    )
                )
            )
            emit("READY", "Polling recent statements", args.api_base)

    if not args.no_bigquery:
        bigquery_client = gcp_config.bigquery_client
        tasks.append(
            asyncio.create_task(
                poll_bigquery(
                    bigquery_client,
                    dataset=dataset,
                    table=args.table,
                    project=project,
                    interval=args.bigquery_interval,
                    seen_ids=set(),
                    limit=args.bigquery_limit,
                )
            )
        )
        emit("READY", "Polling BigQuery", f"{project}.{dataset}.{args.table}")

    if not args.no_pubsub:
        credentials = gcp_config.credentials
        if credentials is None:
            emit("WARN", "Pub/Sub tailer disabled (missing credentials)")
        else:
            pubsub_tail = PubSubTail(project, topic, credentials)
            pubsub_tail.start()

    if not tasks and pubsub_tail is None:
        emit("ERROR", "Nothing to monitor. Enable at least one watcher.")
        return

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_stop(*_: object) -> None:
        emit("INFO", "Shutting down tailers")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_stop)
        except NotImplementedError:
            # Signals not supported on Windows event loop
            signal.signal(sig, lambda *_: _handle_stop())

    await stop_event.wait()

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    if pubsub_tail:
        pubsub_tail.close()


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        asyncio.run(run_tail(args))
    except KeyboardInterrupt:
        emit("INFO", "Interrupted by user")


if __name__ == "__main__":
    main()
