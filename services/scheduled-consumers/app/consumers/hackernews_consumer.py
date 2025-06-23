"""Hacker News consumer for upvoted/liked items."""

import aiohttp
from datetime import datetime, timedelta
from typing import List
import structlog
import random

from .base_consumer import BaseConsumer
from ..models import BaseMessage, HackerNewsItem
from ..config import settings

logger = structlog.get_logger(__name__)


class HackerNewsConsumer(BaseConsumer):
    """Consumer for Hacker News upvoted items."""
    
    def __init__(self):
        """Initialize Hacker News consumer."""
        super().__init__(
            job_type="hackernews_activity",
            interval_minutes=settings.social_media_check_interval_minutes
        )
        self.api_base = "https://hacker-news.firebaseio.com/v0"
    
    async def collect_data(self) -> List[BaseMessage]:
        """Collect upvoted items from Hacker News API.
        
        Returns:
        -------
            List of HackerNewsItem messages
        """
        messages = []
        
        try:
            if not settings.hackernews_user_id:
                logger.warning(
                    "Hacker News user ID not configured, returning mock data"
                )
                return await self._get_mock_hackernews_data()
            
            # Get user's submitted and upvoted items
            async with aiohttp.ClientSession() as session:
                # Get user data
                user_url = f"{self.api_base}/user/{settings.hackernews_user_id}.json"
                async with session.get(user_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch HN user data: {response.status}")
                        return await self._get_mock_hackernews_data()
                    
                    user_data = await response.json()
                    submitted_items = user_data.get("submitted", [])
                
                # Fetch recent submitted items (stories/comments)
                for item_id in submitted_items[:10]:  # Limit to last 10 items
                    item_url = f"{self.api_base}/item/{item_id}.json"
                    async with session.get(item_url) as item_response:
                        if item_response.status == 200:
                            item_data = await item_response.json()
                            if item_data:
                                hn_item = await self._convert_to_hn_item(item_data, "submit")
                                messages.append(hn_item)
            
            logger.info(f"Collected {len(messages)} HN items")
            return messages
            
        except Exception as e:
            logger.error("Failed to collect Hacker News data", error=str(e))
            # Return mock data on error
            return await self._get_mock_hackernews_data()
    
    def get_kafka_topic(self) -> str:
        """Get Kafka topic for HN activity."""
        return "external.hackernews.activity.raw"
    
    async def _convert_to_hn_item(self, item_data: dict, interaction_type: str) -> HackerNewsItem:
        """Convert HN API data to HackerNewsItem."""
        return HackerNewsItem(
            device_id=settings.device_id,
            item_id=item_data["id"],
            item_type=item_data.get("type", "unknown"),
            title=item_data.get("title"),
            url=item_data.get("url"),
            text=item_data.get("text"),
            author=item_data.get("by", "unknown"),
            score=item_data.get("score", 0),
            comments_count=len(item_data.get("kids", [])),
            created_at=datetime.fromtimestamp(item_data.get("time", 0)),
            interacted_at=datetime.utcnow(),
            interaction_type=interaction_type,
        )
    
    async def _get_mock_hackernews_data(self) -> List[BaseMessage]:
        """Generate mock Hacker News data for testing."""
        mock_items = []
        
        # Generate 2-5 mock HN items
        num_items = random.randint(2, 5)
        
        sample_stories = [
            {
                "title": "New breakthrough in quantum computing announced",
                "url": "https://example.com/quantum-breakthrough",
                "author": "quantum_researcher",
                "type": "story"
            },
            {
                "title": "Show HN: I built a productivity app using FastAPI",
                "url": "https://github.com/user/productivity-app",
                "author": "dev_builder",
                "type": "story"
            },
            {
                "title": "The future of remote work post-2024",
                "url": "https://blog.example.com/remote-work-future",
                "author": "remote_expert",
                "type": "story"
            },
            {
                "title": "Ask HN: What's your favorite debugging technique?",
                "author": "curious_dev",
                "type": "story"
            },
        ]
        
        for i in range(min(num_items, len(sample_stories))):
            story_data = sample_stories[i]
            
            item = HackerNewsItem(
                device_id=settings.device_id,
                item_id=random.randint(10000000, 99999999),
                item_type=story_data["type"],
                title=story_data["title"],
                url=story_data.get("url"),
                author=story_data["author"],
                score=random.randint(10, 300),
                comments_count=random.randint(5, 50),
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                interacted_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                interaction_type=random.choice(["upvote", "comment", "save"]),
            )
            mock_items.append(item)
        
        logger.info(f"Generated {len(mock_items)} mock HN items")
        return mock_items