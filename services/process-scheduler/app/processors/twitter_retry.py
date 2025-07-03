#!/usr/bin/env python3
"""
Twitter Extraction Retry Processor

Finds Twitter extraction results with no extracted text and re-adds them 
to the Kafka topic for retry processing.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import asyncpg
import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger(__name__)


class TwitterExtractionRetryProcessor:
    """Processor for retrying failed Twitter extractions."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.database_url = os.getenv("DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom")
        self.kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.batch_size = config.get("batch_size", 100)
        self.max_retry_attempts = config.get("max_retry_attempts", 3)
        self.min_age_hours = config.get("min_age_hours", 1)  # Don't retry items too recent
        self.retry_topic = config.get("retry_topic", "task.url.ingest")
        
    async def process(self) -> Dict:
        """Main processing method."""
        logger.info(
            "Starting Twitter extraction retry processing",
            batch_size=self.batch_size,
            max_retry_attempts=self.max_retry_attempts,
            min_age_hours=self.min_age_hours
        )
        
        results = {
            "processed": 0,
            "republished": 0,
            "skipped": 0,
            "errors": 0,
            "duration_seconds": 0
        }
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Connect to database
            conn = await asyncpg.connect(self.database_url)
            
            # Connect to Kafka
            producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda v: v.encode('utf-8') if v else None
            )
            await producer.start()
            
            try:
                # Find failed extractions to retry
                failed_extractions = await self._find_failed_extractions(conn)
                results["processed"] = len(failed_extractions)
                
                logger.info(
                    "Found failed extractions to retry",
                    count=len(failed_extractions)
                )
                
                # Process in batches
                for i in range(0, len(failed_extractions), self.batch_size):
                    batch = failed_extractions[i:i + self.batch_size]
                    
                    batch_results = await self._process_batch(conn, producer, batch)
                    results["republished"] += batch_results["republished"]
                    results["skipped"] += batch_results["skipped"]
                    results["errors"] += batch_results["errors"]
                    
                    # Small delay between batches to avoid overwhelming the system
                    if i + self.batch_size < len(failed_extractions):
                        await asyncio.sleep(1)
                
            finally:
                await producer.stop()
                await conn.close()
            
            results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                "Twitter extraction retry processing completed",
                **results
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Error in Twitter extraction retry processing",
                error=str(e),
                exc_info=True
            )
            results["errors"] += 1
            results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
            return results
    
    async def _find_failed_extractions(self, conn: asyncpg.Connection) -> List[Dict]:
        """Find Twitter extractions that failed or have no extracted text."""
        
        # Calculate cutoff time - don't retry items that are too recent
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.min_age_hours)
        
        query = """
        SELECT 
            id,
            url,
            extraction_status,
            extraction_attempts,
            created_at,
            updated_at,
            metadata
        FROM twitter_extraction_results 
        WHERE (
            -- No extracted text
            (extracted_text IS NULL OR TRIM(extracted_text) = '')
            OR 
            -- Extraction failed
            extraction_status = 'failed'
        )
        AND created_at < $1  -- Not too recent
        AND COALESCE(extraction_attempts, 0) < $2  -- Haven't exceeded retry limit
        AND url IS NOT NULL  -- Must have a URL to retry
        ORDER BY created_at ASC  -- Oldest first
        LIMIT $3
        """
        
        rows = await conn.fetch(query, cutoff_time, self.max_retry_attempts, self.batch_size * 10)
        
        return [dict(row) for row in rows]
    
    async def _process_batch(
        self, 
        conn: asyncpg.Connection, 
        producer: AIOKafkaProducer, 
        batch: List[Dict]
    ) -> Dict:
        """Process a batch of failed extractions."""
        
        results = {"republished": 0, "skipped": 0, "errors": 0}
        
        for extraction in batch:
            try:
                # Check if this URL is worth retrying
                if not await self._should_retry_extraction(extraction):
                    results["skipped"] += 1
                    continue
                
                # Create retry message for Kafka
                retry_message = await self._create_retry_message(extraction)
                
                # Publish to Kafka
                await producer.send(
                    self.retry_topic,
                    value=retry_message,
                    key=extraction["url"]
                )
                
                # Update database to track retry attempt
                await self._update_retry_attempt(conn, extraction["id"])
                
                results["republished"] += 1
                
                logger.debug(
                    "Republished failed extraction for retry",
                    extraction_id=extraction["id"],
                    url=extraction["url"],
                    attempts=extraction.get("extraction_attempts", 0) + 1
                )
                
            except Exception as e:
                logger.error(
                    "Error processing extraction for retry",
                    extraction_id=extraction["id"],
                    url=extraction.get("url"),
                    error=str(e)
                )
                results["errors"] += 1
        
        return results
    
    async def _should_retry_extraction(self, extraction: Dict) -> bool:
        """Determine if an extraction should be retried."""
        
        # Check retry attempts
        attempts = extraction.get("extraction_attempts", 0)
        if attempts >= self.max_retry_attempts:
            logger.debug(
                "Skipping extraction - too many attempts",
                extraction_id=extraction["id"],
                attempts=attempts,
                max_attempts=self.max_retry_attempts
            )
            return False
        
        # Check if URL is valid
        url = extraction.get("url")
        if not url or not url.startswith(("http://", "https://")):
            logger.debug(
                "Skipping extraction - invalid URL",
                extraction_id=extraction["id"],
                url=url
            )
            return False
        
        # Check if this is a Twitter URL we can process
        if "twitter.com" not in url and "x.com" not in url:
            logger.debug(
                "Skipping extraction - not a Twitter/X URL",
                extraction_id=extraction["id"],
                url=url
            )
            return False
        
        # Check age - don't retry items that are too old (likely permanently failed)
        created_at = extraction.get("created_at")
        if created_at:
            age_days = (datetime.now(timezone.utc) - created_at).days
            max_age_days = self.config.get("max_age_days", 30)
            
            if age_days > max_age_days:
                logger.debug(
                    "Skipping extraction - too old",
                    extraction_id=extraction["id"],
                    age_days=age_days,
                    max_age_days=max_age_days
                )
                return False
        
        return True
    
    async def _create_retry_message(self, extraction: Dict) -> Dict:
        """Create a Kafka message for retrying the extraction."""
        
        # Parse existing metadata if available
        metadata = extraction.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        
        # Add retry information
        metadata.update({
            "retry_attempt": extraction.get("extraction_attempts", 0) + 1,
            "original_extraction_id": extraction["id"],
            "retry_reason": "no_extracted_text_or_failed",
            "retry_timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Create the retry message
        message = {
            "url": extraction["url"],
            "priority": 3,  # Medium priority for retries
            "extract_options": {
                "include_metadata": True,
                "extract_text": True,
                "extract_images": False,  # Skip images on retry to save resources
                "timeout_seconds": 30
            },
            "metadata": metadata,
            "callback_webhook": None,
            "source": "twitter_extraction_retry"
        }
        
        return message
    
    async def _update_retry_attempt(self, conn: asyncpg.Connection, extraction_id: int):
        """Update the extraction record to track the retry attempt."""
        
        await conn.execute("""
            UPDATE twitter_extraction_results 
            SET 
                extraction_attempts = COALESCE(extraction_attempts, 0) + 1,
                updated_at = NOW(),
                extraction_status = 'retrying'
            WHERE id = $1
        """, extraction_id)


async def main():
    """CLI entry point for running the Twitter retry processor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Retry failed Twitter extractions")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--max-retry-attempts", type=int, default=3, help="Maximum retry attempts per URL")
    parser.add_argument("--min-age-hours", type=int, default=1, help="Minimum age in hours before retrying")
    parser.add_argument("--max-age-days", type=int, default=30, help="Maximum age in days for retries")
    parser.add_argument("--retry-topic", default="task.url.ingest", help="Kafka topic for retry messages")
    
    args = parser.parse_args()
    
    config = {
        "batch_size": args.batch_size,
        "max_retry_attempts": args.max_retry_attempts,
        "min_age_hours": args.min_age_hours,
        "max_age_days": args.max_age_days,
        "retry_topic": args.retry_topic
    }
    
    processor = TwitterExtractionRetryProcessor(config)
    results = await processor.process()
    
    print(f"Twitter extraction retry processing completed:")
    print(f"  Processed: {results['processed']}")
    print(f"  Republished: {results['republished']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Errors: {results['errors']}")
    print(f"  Duration: {results['duration_seconds']:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())