"""Twitter/X consumer for liked tweets."""

import random
from datetime import datetime, timedelta
from typing import List

import structlog

from ..config import settings
from ..models import BaseMessage, TwitterLike
from .base_consumer import BaseConsumer

logger = structlog.get_logger(__name__)


class TwitterConsumer(BaseConsumer):
    """Consumer for Twitter/X liked tweets."""

    def __init__(self):
        """Initialize Twitter consumer."""
        super().__init__(
            job_type="twitter_likes",
            interval_minutes=settings.social_media_check_interval_minutes,
        )

    async def collect_data(self) -> List[BaseMessage]:
        """Collect liked tweets from Twitter API.

        Returns:
        -------
            List of TwitterLike messages
        """
        messages = []

        try:
            if not settings.twitter_bearer_token:
                logger.warning("Twitter API token not configured, returning mock data")
                return await self._get_mock_twitter_data()

            # TODO: Implement actual Twitter API v2 integration
            # import tweepy
            # client = tweepy.Client(bearer_token=settings.twitter_bearer_token)

            logger.info("Collecting liked tweets from Twitter API")

            # For now, return mock data until Twitter API is implemented
            return await self._get_mock_twitter_data()

        except Exception as e:
            logger.error("Failed to collect Twitter data", error=str(e))
            raise

    def get_kafka_topic(self) -> str:
        """Get Kafka topic for Twitter likes."""
        return "external.twitter.liked.raw"

    async def _get_mock_twitter_data(self) -> List[BaseMessage]:
        """Generate mock Twitter data for testing."""
        mock_tweets = []

        # Generate 3-8 mock liked tweets
        num_tweets = random.randint(3, 8)

        sample_tweets = [
            {
                "author": "elonmusk",
                "name": "Elon Musk",
                "text": "The future is going to be wild",
                "hashtags": ["future", "technology"],
            },
            {
                "author": "OpenAI",
                "name": "OpenAI",
                "text": "Introducing our latest AI model with improved reasoning capabilities",
                "hashtags": ["AI", "OpenAI", "research"],
            },
            {
                "author": "vercel",
                "name": "Vercel",
                "text": "Ship faster with our new deployment features",
                "hashtags": ["webdev", "deployment", "frontend"],
            },
            {
                "author": "fastapi",
                "name": "FastAPI",
                "text": "FastAPI performance benchmarks show 3x improvement",
                "hashtags": ["python", "fastapi", "performance"],
            },
            {
                "author": "github",
                "name": "GitHub",
                "text": "New GitHub Actions features for better CI/CD workflows",
                "hashtags": ["github", "cicd", "devops"],
            },
        ]

        for i in range(min(num_tweets, len(sample_tweets))):
            tweet_data = sample_tweets[i]

            tweet = TwitterLike(
                device_id=settings.device_id,
                tweet_id=f"mock_tweet_{i}_{int(datetime.utcnow().timestamp())}",
                tweet_url=f"https://twitter.com/{tweet_data['author']}/status/{i}",
                author_username=tweet_data["author"],
                author_display_name=tweet_data["name"],
                tweet_text=tweet_data["text"],
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                liked_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 120)),
                retweet_count=random.randint(10, 500),
                like_count=random.randint(50, 2000),
                reply_count=random.randint(5, 100),
                hashtags=tweet_data["hashtags"],
                mentions=[],
                media_urls=[],
            )
            mock_tweets.append(tweet)

        logger.info(f"Generated {len(mock_tweets)} mock Twitter likes")
        return mock_tweets
