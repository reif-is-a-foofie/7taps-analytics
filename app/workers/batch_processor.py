#!/usr/bin/env python3
"""
Background Batch Processor for AI Safety Analysis

Runs as a separate worker process to handle batch AI analysis
and ensure flagged content is properly processed.
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.batch_ai_safety import batch_processor
from app.logging_config import get_logger

logger = get_logger("batch_worker")

class BatchWorker:
    """Background worker for processing AI safety batches."""
    
    def __init__(self):
        self.running = False
        self.process_interval = 60  # Check every 60 seconds
    
    async def start(self):
        """Start the background batch processor."""
        logger.info("Starting batch AI safety worker...")
        self.running = True
        
        while self.running:
            try:
                # Check if we need to process a batch
                status = batch_processor.get_batch_status()
                
                if status["queue_size"] > 0:
                    logger.info(f"Processing batch with {status['queue_size']} items")
                    await batch_processor._process_batch()
                    logger.info("Batch processing completed")
                else:
                    logger.debug("No items in queue, waiting...")
                
                # Wait before next check
                await asyncio.sleep(self.process_interval)
                
            except Exception as e:
                logger.error(f"Batch worker error: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error
    
    def stop(self):
        """Stop the background processor."""
        logger.info("Stopping batch worker...")
        self.running = False

async def main():
    """Main worker entry point."""
    worker = BatchWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        worker.stop()
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
