"""
ETL Control API for managing Pub/Sub processors.
"""

import threading
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.etl.pubsub_bigquery_processor import get_processor, start_processor_background, stop_processor
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("etl_control")

# Global processor thread tracking
_processor_thread = None
_processor_running = False


@router.post("/etl/start-bigquery-processor")
async def start_bigquery_processor() -> Dict[str, Any]:
    """Start the Pub/Sub → BigQuery ETL processor."""
    global _processor_thread, _processor_running
    
    try:
        if _processor_running:
            return {
                "status": "already_running",
                "message": "BigQuery processor is already running",
                "processor_status": get_processor().get_status()
            }
        
        # Start the processor in background
        start_processor_background()
        _processor_running = True
        
        logger.info("Started BigQuery ETL processor")
        
        return {
            "status": "started",
            "message": "BigQuery ETL processor started successfully",
            "processor_status": get_processor().get_status()
        }
        
    except Exception as e:
        logger.error(f"Failed to start BigQuery processor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processor: {str(e)}")


@router.post("/etl/stop-bigquery-processor")
async def stop_bigquery_processor() -> Dict[str, Any]:
    """Stop the Pub/Sub → BigQuery ETL processor."""
    global _processor_running
    
    try:
        if not _processor_running:
            return {
                "status": "not_running",
                "message": "BigQuery processor is not running"
            }
        
        stop_processor()
        _processor_running = False
        
        logger.info("Stopped BigQuery ETL processor")
        
        return {
            "status": "stopped",
            "message": "BigQuery ETL processor stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop BigQuery processor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop processor: {str(e)}")


@router.post("/etl/trigger-processing")
async def trigger_etl_processing() -> Dict[str, Any]:
    """Trigger ETL processors to wake up and process pending messages."""
    global _processor_running
    
    try:
        # Ensure processors are running
        if not _processor_running:
            logger.info("ETL processors not running, starting them...")
            start_processor_background()
            _processor_running = True
        
        # Get processor status
        processor = get_processor()
        status = processor.get_status()
        
        logger.info("ETL processing triggered - processors should be active")
        
        return {
            "status": "triggered",
            "message": "ETL processors triggered successfully",
            "processor_running": _processor_running,
            "processor_status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger ETL processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {str(e)}")


@router.get("/etl/bigquery-processor-status")
async def get_bigquery_processor_status() -> Dict[str, Any]:
    """Get the status of the BigQuery ETL processor."""
    try:
        processor = get_processor()
        status = processor.get_status()
        
        return {
            "global_running": _processor_running,
            "processor_details": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get processor status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/etl/queue-size")
async def get_queue_size() -> Dict[str, Any]:
    """Get detailed queue size information for the ETL processor."""
    try:
        processor = get_processor()
        queue_info = processor.get_subscription_queue_size()
        
        # Try to get more detailed metrics if possible
        try:
            from google.cloud import monitoring_v3
            from app.config.gcp_config import get_gcp_config
            
            gcp_config = get_gcp_config()
            client = monitoring_v3.MetricServiceClient()
            project_name = f"projects/{gcp_config.project_id}"
            
            # Query for unacked message count
            filter_str = f'metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages" AND resource.labels.subscription_id="{processor.subscription_name}"'
            
            interval = monitoring_v3.TimeInterval({
                "end_time": {"seconds": int(datetime.now(timezone.utc).timestamp())},
                "start_time": {"seconds": int(datetime.now(timezone.utc).timestamp()) - 300}  # 5 minutes ago
            })
            
            results = client.list_time_series(
                request={
                    "name": project_name,
                    "filter": filter_str,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )
            
            unacked_messages = 0
            for result in results:
                if result.points:
                    unacked_messages = int(result.points[-1].value.int64_value)
                    break
            
            queue_info["unacked_messages"] = unacked_messages
            queue_info["monitoring_available"] = True
            
        except Exception as e:
            logger.warning(f"Could not get detailed queue metrics: {e}")
            queue_info["monitoring_available"] = False
            queue_info["monitoring_error"] = str(e)
        
        return {
            "queue_info": queue_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue size: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue size: {str(e)}")


@router.get("/etl/status")
async def get_etl_status() -> Dict[str, Any]:
    """Get overall ETL pipeline status."""
    try:
        return {
            "bigquery_processor": {
                "running": _processor_running,
                "status": get_processor().get_status() if _processor_running else None
            },
            "available_processors": [
                "bigquery_processor"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get ETL status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ETL status: {str(e)}")

