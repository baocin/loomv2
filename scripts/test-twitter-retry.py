#!/usr/bin/env python3
"""
Test script for Twitter extraction retry processor.

This script tests the Twitter extraction retry functionality by:
1. Finding failed extractions in the database
2. Running the retry processor
3. Showing the results
"""

import asyncio
import sys
from pathlib import Path

# Add the scheduler service to path
service_path = Path(__file__).parent.parent / "services" / "process-scheduler"
sys.path.append(str(service_path))

import asyncpg
from app.processors.twitter_retry import TwitterExtractionRetryProcessor


async def check_failed_extractions():
    """Check for failed Twitter extractions in the database."""
    
    database_url = "postgresql://loom:loom@localhost:5432/loom"
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check if twitter_extraction_results table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'twitter_extraction_results'
            )
        """)
        
        if not table_exists:
            print("❌ twitter_extraction_results table does not exist")
            print("   This table is needed for the Twitter extraction retry process")
            await conn.close()
            return False
        
        # Count total extractions
        total_count = await conn.fetchval("SELECT COUNT(*) FROM twitter_extraction_results")
        
        # Count failed extractions (no extracted text or failed status)
        failed_count = await conn.fetchval("""
            SELECT COUNT(*) FROM twitter_extraction_results 
            WHERE (
                (extracted_text IS NULL OR TRIM(extracted_text) = '')
                OR extraction_status = 'failed'
            )
            AND url IS NOT NULL
        """)
        
        # Count by status
        status_counts = await conn.fetch("""
            SELECT 
                COALESCE(extraction_status, 'null') as status,
                COUNT(*) as count
            FROM twitter_extraction_results 
            GROUP BY extraction_status
            ORDER BY count DESC
        """)
        
        # Count by attempts
        attempt_counts = await conn.fetch("""
            SELECT 
                COALESCE(extraction_attempts, 0) as attempts,
                COUNT(*) as count
            FROM twitter_extraction_results 
            GROUP BY extraction_attempts
            ORDER BY attempts ASC
        """)
        
        print(f"📊 Twitter Extraction Results Overview:")
        print(f"   Total extractions: {total_count}")
        print(f"   Failed/empty extractions: {failed_count}")
        print(f"   Success rate: {((total_count - failed_count) / total_count * 100):.1f}%" if total_count > 0 else "N/A")
        
        print(f"\n📈 Status breakdown:")
        for row in status_counts:
            print(f"   {row['status']}: {row['count']}")
        
        print(f"\n🔄 Retry attempts breakdown:")
        for row in attempt_counts:
            print(f"   {row['attempts']} attempts: {row['count']}")
        
        # Show some example failed extractions
        failed_examples = await conn.fetch("""
            SELECT id, url, extraction_status, extraction_attempts, created_at,
                   LENGTH(COALESCE(extracted_text, '')) as text_length
            FROM twitter_extraction_results 
            WHERE (
                (extracted_text IS NULL OR TRIM(extracted_text) = '')
                OR extraction_status = 'failed'
            )
            AND url IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        if failed_examples:
            print(f"\n🔍 Recent failed extractions (sample):")
            for row in failed_examples:
                print(f"   ID {row['id']}: {row['url'][:60]}...")
                print(f"      Status: {row['extraction_status']}, Attempts: {row['extraction_attempts']}, Text length: {row['text_length']}")
        
        await conn.close()
        return failed_count > 0
        
    except Exception as e:
        print(f"❌ Error checking failed extractions: {e}")
        return False


async def test_retry_processor():
    """Test the Twitter extraction retry processor."""
    
    print(f"\n🧪 Testing Twitter Extraction Retry Processor")
    
    # Configuration for testing
    config = {
        "batch_size": 10,  # Small batch for testing
        "max_retry_attempts": 3,
        "min_age_hours": 0,  # Allow immediate retry for testing
        "max_age_days": 30,
        "retry_topic": "task.url.ingest"
    }
    
    try:
        processor = TwitterExtractionRetryProcessor(config)
        results = await processor.process()
        
        print(f"✅ Retry processor completed successfully")
        print(f"   Processed: {results['processed']}")
        print(f"   Republished: {results['republished']}")
        print(f"   Skipped: {results['skipped']}")
        print(f"   Errors: {results['errors']}")
        print(f"   Duration: {results['duration_seconds']:.2f} seconds")
        
        if results['republished'] > 0:
            print(f"\n🎉 Successfully republished {results['republished']} failed extractions for retry!")
        elif results['processed'] == 0:
            print(f"\n✨ No failed extractions found to retry (all good!)")
        else:
            print(f"\n⚠️ Found {results['processed']} failed extractions but none were suitable for retry")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing retry processor: {e}")
        import traceback
        traceback.print_exc()
        return False


async def simulate_failed_extraction():
    """Create a simulated failed extraction for testing purposes."""
    
    database_url = "postgresql://loom:loom@localhost:5432/loom"
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check if table exists first
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'twitter_extraction_results'
            )
        """)
        
        if not table_exists:
            print("❌ twitter_extraction_results table does not exist")
            print("   Cannot create simulated failed extraction")
            await conn.close()
            return False
        
        # Create a test failed extraction
        test_url = f"https://twitter.com/test/status/test_retry_{int(asyncio.get_event_loop().time())}"
        
        extraction_id = await conn.fetchval("""
            INSERT INTO twitter_extraction_results (
                url, extraction_status, extracted_text, extraction_attempts, created_at
            ) VALUES ($1, $2, $3, $4, NOW())
            RETURNING id
        """, test_url, "failed", None, 0)
        
        print(f"✅ Created simulated failed extraction with ID {extraction_id}")
        print(f"   URL: {test_url}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating simulated extraction: {e}")
        return False


async def main():
    """Main test entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Twitter extraction retry processor")
    parser.add_argument("action", choices=["check", "test", "simulate"], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "check":
        await check_failed_extractions()
    elif args.action == "simulate":
        success = await simulate_failed_extraction()
        if success:
            print("\n📝 You can now run 'python scripts/test-twitter-retry.py test' to test the retry processor")
    elif args.action == "test":
        has_failed = await check_failed_extractions()
        if has_failed:
            await test_retry_processor()
        else:
            print("\n💡 No failed extractions found. You can create one with:")
            print("   python scripts/test-twitter-retry.py simulate")


if __name__ == "__main__":
    asyncio.run(main())