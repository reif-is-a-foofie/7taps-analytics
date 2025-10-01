"""Trigger word alert management for xAPI ingestion."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import bigquery

from app.config.gcp_config import get_gcp_config
from app.logging_config import get_logger

logger = get_logger("trigger_word_alerts")

DEFAULT_TRIGGER_WORDS: Tuple[str, ...] = (
    "suicide",
    "self harm",
    "self-harm",
    "kill myself",
    "hurting myself",
)

ALERT_RETENTION_DAYS = 30
MAX_ALERT_RECORDS = 500


class TriggerWordAlertManager:
    """Manage trigger word detection, alerting, and history."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trigger_words: Set[str] = set()
        self._trigger_metadata: Dict[str, Dict[str, Any]] = {}
        self._alerts: Deque[Dict[str, Any]] = deque(maxlen=MAX_ALERT_RECORDS)
        self._alert_index: Dict[str, Dict[str, Any]] = {}
        self._statement_word_index: Dict[Tuple[str, str], str] = {}
        self._gcp_config = get_gcp_config()
        self._bigquery_client: Optional[bigquery.Client] = None

        self._load_initial_trigger_words()

    # ------------------------------------------------------------------
    # Trigger word configuration
    # ------------------------------------------------------------------
    def _load_initial_trigger_words(self) -> None:
        words = list(DEFAULT_TRIGGER_WORDS)
        env_words = os.getenv("ALERT_TRIGGER_WORDS", "")
        if env_words:
            words.extend(part.strip() for part in env_words.split(",") if part.strip())

        normalized = {self._normalize_word(word) for word in words if word}
        now = datetime.now(timezone.utc)
        for word in normalized:
            self._trigger_words.add(word)
            self._trigger_metadata[word] = {
                "added_at": now,
                "retro_scan_complete": False,
            }

    @staticmethod
    def _normalize_word(word: str) -> str:
        return word.strip().lower()

    def get_trigger_words(self) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for word in sorted(self._trigger_words):
                meta = self._trigger_metadata.get(word, {})
                results.append(
                    {
                        "word": word,
                        "added_at": meta.get("added_at"),
                        "retro_scan_complete": meta.get("retro_scan_complete", False),
                    }
                )
            return results

    def update_trigger_words(self, words: Sequence[str], *, mode: str = "append") -> Dict[str, Any]:
        normalized_input = {self._normalize_word(word) for word in words if word}
        now = datetime.now(timezone.utc)

        with self._lock:
            previous_words = set(self._trigger_words)
            if mode == "replace":
                self._trigger_words = set(normalized_input)
            else:
                self._trigger_words.update(normalized_input)

            removed_words = []
            if mode == "replace":
                removed_words = sorted(previous_words - self._trigger_words)
                for removed in removed_words:
                    self._trigger_metadata.pop(removed, None)

            added_words = sorted(self._trigger_words - previous_words)
            for word in added_words:
                self._trigger_metadata[word] = {
                    "added_at": now,
                    "retro_scan_complete": False,
                }

        if added_words:
            for word in added_words:
                try:
                    self._run_retroactive_scan(word)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Retroactive scan failed", word=word, error=str(exc))

        return {
            "current_words": sorted(self._trigger_words),
            "added_words": added_words,
            "removed_words": removed_words,
        }

    # ------------------------------------------------------------------
    # Detection & alert lifecycle
    # ------------------------------------------------------------------
    def evaluate_statement(
        self,
        statement: Dict[str, Any],
        *,
        source: str,
    ) -> Optional[str]:
        searchable_text = self._extract_searchable_text(statement)
        if not searchable_text:
            return None

        matches = self._find_matches(searchable_text)
        if not matches:
            return None

        alert = self._record_alert(
            statement=statement,
            matches=matches,
            source=source,
            detection_scope="realtime",
        )
        return alert.get("alert_id")

    def attach_publish_metadata(
        self,
        alert_id: Optional[str],
        *,
        message_id: Optional[str],
        topic: Optional[str],
    ) -> None:
        if not alert_id:
            return
        with self._lock:
            alert = self._alert_index.get(alert_id)
            if not alert:
                return
            alert["message_id"] = message_id
            alert["pubsub_topic"] = topic

    def register_historical_alert(self, record: Dict[str, Any], *, word: str) -> None:
        self._record_alert(
            statement=record,
            matches={word},
            source="historical",
            detection_scope="retroactive",
            is_raw_record=True,
        )

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ALERT_RETENTION_DAYS)
        with self._lock:
            filtered = [alert for alert in reversed(self._alerts) if alert["detected_at"] >= cutoff]
            return filtered[:limit]

    def get_summary(self) -> Dict[str, Any]:
        alerts = self.get_recent_alerts(limit=MAX_ALERT_RECORDS)
        total = len(alerts)
        latest = alerts[0] if alerts else None
        return {
            "trigger_words": sorted(self._trigger_words),
            "total_recent_alerts": total,
            "latest_alert": latest,
            "retention_days": ALERT_RETENTION_DAYS,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _record_alert(
        self,
        *,
        statement: Dict[str, Any],
        matches: Set[str],
        source: str,
        detection_scope: str,
        is_raw_record: bool = False,
    ) -> Dict[str, Any]:
        statement_id = statement.get("id") or statement.get("statement_id") or str(uuid.uuid4())
        detected_at = datetime.now(timezone.utc)
        alert_id = str(uuid.uuid4())

        with self._lock:
            unique_keys = {(statement_id, word) for word in matches}
            existing_alert_ids = {
                self._statement_word_index[key]
                for key in unique_keys
                if key in self._statement_word_index
            }
            if existing_alert_ids:
                existing_id = next(iter(existing_alert_ids))
                return self._alert_index.get(existing_id, {})

            for key in unique_keys:
                self._statement_word_index[key] = alert_id

            safe_statement = json.loads(json.dumps(statement, default=str)) if not is_raw_record else statement

            alert_record = {
                "alert_id": alert_id,
                "statement_id": statement_id,
                "matches": sorted(matches),
                "detected_at": detected_at,
                "source": source,
                "detection_scope": detection_scope,
                "statement": safe_statement,
                "message_id": None,
                "pubsub_topic": None,
            }
            self._alerts.append(alert_record)
            self._alert_index[alert_id] = alert_record

        self._send_email_notification(alert_record)
        return alert_record

    def _extract_searchable_text(self, statement: Dict[str, Any]) -> str:
        try:
            parts: List[str] = []
            actor = statement.get("actor") or {}
            if actor:
                parts.append(json.dumps(actor))
            verb = statement.get("verb") or {}
            if verb:
                parts.append(json.dumps(verb))
            obj = statement.get("object") or {}
            if obj:
                parts.append(json.dumps(obj))
            result = statement.get("result") or {}
            if result:
                parts.append(json.dumps(result))
            context = statement.get("context") or {}
            if context:
                parts.append(json.dumps(context))
            if statement.get("raw_json"):
                parts.append(statement["raw_json"])
            if statement.get("statement"):
                parts.append(json.dumps(statement.get("statement")))
            return " \n ".join(parts).lower()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to extract searchable text", error=str(exc))
            return ""

    def _find_matches(self, searchable_text: str) -> Set[str]:
        matches = set()
        for word in list(self._trigger_words):
            if word and word in searchable_text:
                matches.add(word)
        return matches

    def _send_email_notification(self, alert: Dict[str, Any]) -> None:
        recipients_env = os.getenv("ALERT_EMAIL_RECIPIENTS", "")
        if not recipients_env:
            logger.info("Alert generated without email recipients; skipping email notification", alert_id=alert["alert_id"])
            return

        smtp_server = os.getenv("ALERT_EMAIL_SMTP_SERVER")
        smtp_username = os.getenv("ALERT_EMAIL_SMTP_USERNAME")
        smtp_password = os.getenv("ALERT_EMAIL_SMTP_PASSWORD")
        if not smtp_server or not smtp_username or not smtp_password:
            logger.warning(
                "Email notification skipped because SMTP configuration is incomplete",
                alert_id=alert["alert_id"],
            )
            return

        recipients = [addr.strip() for addr in recipients_env.split(",") if addr.strip()]
        if not recipients:
            logger.warning("No valid email recipients parsed for alert notification", alert_id=alert["alert_id"])
            return

        sender = os.getenv("ALERT_EMAIL_SENDER", "no-reply@practiceoflife.com")
        subject = "Trigger word alert: " + ", ".join(alert.get("matches", []))

        statement_id = alert.get("statement_id")
        detected_at = alert.get("detected_at")
        matches = ", ".join(alert.get("matches", []))
        snippet = json.dumps(alert.get("statement", {}))[:500]

        body = (
            "Safety alert detected.\n\n"
            f"Statement ID: {statement_id}\n"
            f"Matches: {matches}\n"
            f"Detected At: {detected_at}\n"
            f"Source: {alert.get('source')}\n"
            f"Detection Scope: {alert.get('detection_scope')}\n"
            f"Pub/Sub Message: {alert.get('message_id') or 'pending'}\n"
            f"Topic: {alert.get('pubsub_topic') or 'pending'}\n\n"
            "Excerpt:\n"
            f"{snippet}\n"
        )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message.set_content(body)

        try:
            port = int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587"))
            use_tls = os.getenv("ALERT_EMAIL_SMTP_USE_TLS", "true").lower() != "false"
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, port) as server:
                if use_tls:
                    server.starttls(context=context)
                server.login(smtp_username, smtp_password)
                server.send_message(message)
            logger.info("Alert notification email sent", alert_id=alert["alert_id"], recipients=recipients)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to send alert notification email", error=str(exc), alert_id=alert["alert_id"])

    def _run_retroactive_scan(self, word: str) -> None:
        client = self._get_bigquery_client()
        if not client:
            logger.warning("Retroactive scan skipped; BigQuery client unavailable", word=word)
            return

        dataset = self._gcp_config.bigquery_dataset
        project = self._gcp_config.project_id
        table = f"`{project}.{dataset}.statements`"
        query = (
            f"SELECT statement_id, timestamp, actor_id, raw_json "
            f"FROM {table} "
            "WHERE LOWER(raw_json) LIKE @pattern "
            "ORDER BY timestamp DESC"
        )

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("pattern", "STRING", f"%{word}%"),
            ]
        )

        logger.info("Starting retroactive scan", word=word)
        try:
            results = client.query(query, job_config=job_config).result()
            count = 0
            for row in results:
                raw_json = row.get("raw_json")
                try:
                    statement = json.loads(raw_json) if raw_json else {}
                except json.JSONDecodeError:
                    statement = {"raw_json": raw_json}
                statement.setdefault("id", row.get("statement_id"))
                timestamp_value = row.get("timestamp")
                if isinstance(timestamp_value, datetime):
                    statement.setdefault("detected_timestamp", timestamp_value.isoformat())
                else:
                    statement.setdefault("detected_timestamp", timestamp_value)
                self.register_historical_alert(statement, word=word)
                count += 1

            with self._lock:
                if word in self._trigger_metadata:
                    self._trigger_metadata[word]["retro_scan_complete"] = True
                    self._trigger_metadata[word]["retro_scan_count"] = count
            logger.info("Retroactive scan complete", word=word, matches=count)
        except NotFound:
            logger.warning("BigQuery statements table not found; retro scan skipped", word=word)
        except GoogleAPICallError as exc:
            logger.exception("BigQuery query failed", word=word, error=str(exc))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Unexpected error during retroactive scan", word=word, error=str(exc))

    def _get_bigquery_client(self) -> Optional[bigquery.Client]:
        if self._bigquery_client is None:
            try:
                self._bigquery_client = self._gcp_config.bigquery_client
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Unable to initialize BigQuery client", error=str(exc))
                self._bigquery_client = None
        return self._bigquery_client


trigger_word_alert_manager = TriggerWordAlertManager()
