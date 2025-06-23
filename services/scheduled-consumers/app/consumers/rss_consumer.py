"""RSS feed consumer for blog posts and news."""

import feedparser
from datetime import datetime, timedelta
from typing import List
import structlog
import aiohttp

from .base_consumer import BaseConsumer
from ..models import BaseMessage, RSSFeedItem
from ..config import settings

logger = structlog.get_logger(__name__)


class RSSConsumer(BaseConsumer):
    """Consumer for RSS feed items."""
    
    def __init__(self):
        """Initialize RSS consumer."""
        super().__init__(
            job_type="rss_feeds",
            interval_minutes=settings.social_media_check_interval_minutes
        )
        self._seen_items: set = set()
    
    async def collect_data(self) -> List[BaseMessage]:
        """Collect items from RSS feeds.
        
        Returns:
        -------
            List of RSSFeedItem messages
        """
        messages = []
        
        if not settings.rss_feeds:
            logger.warning("No RSS feeds configured, returning empty list")
            return messages
        
        try:
            async with aiohttp.ClientSession() as session:
                for feed_url in settings.rss_feeds:
                    try:
                        feed_items = await self._fetch_feed(session, feed_url)
                        messages.extend(feed_items)
                    except Exception as e:
                        logger.error(
                            "Failed to fetch RSS feed",
                            feed_url=feed_url,
                            error=str(e)
                        )
            
            logger.info(f"Collected {len(messages)} RSS feed items")
            return messages
            
        except Exception as e:
            logger.error("Failed to collect RSS feed data", error=str(e))
            raise
    
    def get_kafka_topic(self) -> str:
        """Get Kafka topic for RSS items."""
        return "external.rss.items.raw"
    
    async def _fetch_feed(self, session: aiohttp.ClientSession, feed_url: str) -> List[BaseMessage]:
        """Fetch and parse a single RSS feed."""
        items = []
        
        try:
            async with session.get(feed_url, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch RSS feed: {response.status}", feed_url=feed_url)
                    return items
                
                content = await response.text()
                
                # Parse with feedparser
                feed = feedparser.parse(content)
                
                if hasattr(feed, 'bozo') and feed.bozo:
                    logger.warning("RSS feed has parsing errors", feed_url=feed_url)
                
                feed_title = getattr(feed.feed, 'title', feed_url)
                
                # Process recent items (last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                for entry in feed.entries[:20]:  # Limit to 20 most recent
                    try:
                        # Parse published date
                        published_at = self._parse_entry_date(entry)
                        
                        # Skip old items
                        if published_at and published_at < cutoff_time:
                            continue
                        
                        # Create unique item ID
                        item_id = getattr(entry, 'id', None) or getattr(entry, 'link', '')
                        if not item_id:
                            continue
                        
                        # Skip if we've seen this item recently
                        if item_id in self._seen_items:
                            continue
                        
                        self._seen_items.add(item_id)
                        
                        # Extract content
                        content = self._extract_content(entry)
                        
                        # Extract categories
                        categories = []
                        if hasattr(entry, 'tags'):
                            categories = [tag.term for tag in entry.tags]
                        
                        item = RSSFeedItem(
                            device_id=settings.device_id,
                            feed_url=feed_url,
                            feed_title=feed_title,
                            item_id=item_id,
                            item_title=getattr(entry, 'title', 'Untitled'),
                            item_url=getattr(entry, 'link', ''),
                            item_content=content,
                            author=getattr(entry, 'author', None),
                            published_at=published_at or datetime.utcnow(),
                            categories=categories,
                        )
                        items.append(item)
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to process RSS entry",
                            feed_url=feed_url,
                            error=str(e)
                        )
                
                logger.info(f"Fetched {len(items)} items from RSS feed", feed_url=feed_url)
                
        except Exception as e:
            logger.error("Failed to fetch RSS feed", feed_url=feed_url, error=str(e))
            raise
        
        return items
    
    def _parse_entry_date(self, entry) -> datetime | None:
        """Parse entry publication date."""
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        import time
                        return datetime.fromtimestamp(time.mktime(time_struct))
                    except (ValueError, TypeError):
                        continue
        
        # Try string fields
        string_fields = ['published', 'updated']
        for field in string_fields:
            if hasattr(entry, field):
                date_str = getattr(entry, field)
                if date_str:
                    try:
                        from dateutil.parser import parse
                        return parse(date_str)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _extract_content(self, entry) -> str | None:
        """Extract content from RSS entry."""
        # Try different content fields
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].value if entry.content else None
        
        if hasattr(entry, 'summary'):
            return entry.summary
        
        if hasattr(entry, 'description'):
            return entry.description
        
        return None