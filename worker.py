#!/usr/bin/env python3
"""
ETL Worker for 7taps Analytics

This script runs the ETL streaming processor continuously to process
xAPI statements from Redis Streams and write them to PostgreSQL.
"""

import asyncio
import logging
import os
import signal
import sys
from app.etl_streaming import get_etl_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ETLWorker:
    """ETL Worker that continuously processes xAPI statements."""
    
    def __init__(self):
        self.etl_processor = get_etl_processor()
        self.running = False
        
    async def start(self):
        """Start the ETL worker."""
        logger.info("Starting ETL Worker...")
        self.running = True
        
        try:
            # Ensure stream group exists
            await self.etl_processor.ensure_stream_group()
            logger.info("ETL Worker started successfully")
            
            # Process stream continuously
            while self.running:
                try:
                    # Process up to 10 messages at a time
                    processed = await self.etl_processor.process_stream(max_messages=10)
                    if processed:
                        logger.info(f"Processed {len(processed)} statements")
                    
                    # Wait a bit before next processing cycle
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error processing stream: {e}")
                    await asyncio.sleep(10)  # Wait longer on error
                    
        except Exception as e:
            logger.error(f"ETL Worker failed: {e}")
            raise
            
    def stop(self):
        """Stop the ETL worker."""
        logger.info("Stopping ETL Worker...")
        self.running = False
        
    async def cleanup(self):
        """Cleanup resources."""
        await self.etl_processor.close()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

async def main():
    """Main function to run the ETL worker."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    worker = ETLWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    finally:
        await worker.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
