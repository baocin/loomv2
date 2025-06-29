"""Web browsing consumer for browser history."""

import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List

import structlog

from ..config import settings
from ..models import BaseMessage, WebVisit
from .base_consumer import BaseConsumer

logger = structlog.get_logger(__name__)


class WebConsumer(BaseConsumer):
    """Consumer for web browsing history from browsers."""

    def __init__(self):
        """Initialize web consumer."""
        super().__init__(
            job_type="web_visits",
            interval_minutes=settings.web_activity_check_interval_minutes,
        )
        self._last_sync_time: datetime | None = None

    async def collect_data(self) -> List[BaseMessage]:
        """Collect web browsing data from browser databases.

        Returns:
        -------
            List of WebVisit messages
        """
        messages = []

        try:
            # Try Chrome first, then Firefox
            chrome_visits = await self._get_chrome_history()
            firefox_visits = await self._get_firefox_history()

            messages.extend(chrome_visits)
            messages.extend(firefox_visits)

            # If no real data, return empty list
            if not messages:
                logger.warning("No browser history found, returning empty list")
                return []

            logger.info(f"Collected {len(messages)} web visits")
            return messages

        except Exception as e:
            logger.error("Failed to collect web browsing data", error=str(e))
            return []

    def get_kafka_topic(self) -> str:
        """Get Kafka topic for web visits."""
        return "external.web.visits.raw"

    async def _get_chrome_history(self) -> List[BaseMessage]:
        """Get Chrome browsing history."""
        visits = []

        chrome_path = settings.chrome_history_path
        if not chrome_path:
            # Try default Chrome history location
            home = os.path.expanduser("~")
            chrome_path = os.path.join(home, ".config/google-chrome/Default/History")

        if not os.path.exists(chrome_path):
            logger.debug("Chrome history not found", path=chrome_path)
            return visits

        try:
            # Chrome history is SQLite
            conn = sqlite3.connect(f"file:{chrome_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Get recent visits (last hour)
            since_time = datetime.utcnow() - timedelta(hours=1)
            since_chrome_time = (
                int(since_time.timestamp() * 1000000) + 11644473600000000
            )

            query = """
            SELECT url, title, visit_time, visit_duration
            FROM urls
            JOIN visits ON urls.id = visits.url
            WHERE visit_time > ?
            ORDER BY visit_time DESC
            LIMIT 50
            """

            cursor.execute(query, (since_chrome_time,))
            rows = cursor.fetchall()

            for url, title, visit_time, duration in rows:
                # Convert Chrome timestamp to datetime
                chrome_time = (visit_time - 11644473600000000) / 1000000
                visit_datetime = datetime.fromtimestamp(chrome_time)

                visit = WebVisit(
                    device_id=settings.device_id,
                    url=url,
                    title=title,
                    visit_time=visit_datetime,
                    visit_duration=(
                        duration // 1000000 if duration else None
                    ),  # Convert to seconds
                    browser="chrome",
                )
                visits.append(visit)

            conn.close()
            logger.info(f"Collected {len(visits)} Chrome visits")

        except Exception as e:
            logger.error("Failed to read Chrome history", error=str(e))

        return visits

    async def _get_firefox_history(self) -> List[BaseMessage]:
        """Get Firefox browsing history."""
        visits = []

        firefox_path = settings.firefox_history_path
        if not firefox_path:
            # Try default Firefox profile location
            home = os.path.expanduser("~")
            firefox_profile_path = os.path.join(home, ".mozilla/firefox")
            if os.path.exists(firefox_profile_path):
                # Find default profile
                for item in os.listdir(firefox_profile_path):
                    if item.endswith(".default-release"):
                        firefox_path = os.path.join(
                            firefox_profile_path, item, "places.sqlite"
                        )
                        break

        if not firefox_path or not os.path.exists(firefox_path):
            logger.debug("Firefox history not found", path=firefox_path)
            return visits

        try:
            conn = sqlite3.connect(f"file:{firefox_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Get recent visits (last hour)
            since_time = datetime.utcnow() - timedelta(hours=1)
            since_firefox_time = int(since_time.timestamp() * 1000000)

            query = """
            SELECT url, title, visit_date
            FROM moz_places
            JOIN moz_historyvisits ON moz_places.id = moz_historyvisits.place_id
            WHERE visit_date > ?
            ORDER BY visit_date DESC
            LIMIT 50
            """

            cursor.execute(query, (since_firefox_time,))
            rows = cursor.fetchall()

            for url, title, visit_date in rows:
                # Convert Firefox timestamp to datetime
                visit_datetime = datetime.fromtimestamp(visit_date / 1000000)

                visit = WebVisit(
                    device_id=settings.device_id,
                    url=url,
                    title=title,
                    visit_time=visit_datetime,
                    browser="firefox",
                )
                visits.append(visit)

            conn.close()
            logger.info(f"Collected {len(visits)} Firefox visits")

        except Exception as e:
            logger.error("Failed to read Firefox history", error=str(e))

        return visits

    async def _get_mock_web_data(self) -> List[BaseMessage]:
        """Generate mock web browsing data for testing."""
        mock_visits = []

        # Generate 5-15 mock web visits
        num_visits = random.randint(5, 15)

        sample_sites = [
            {"url": "https://github.com/explore", "title": "Explore GitHub"},
            {"url": "https://news.ycombinator.com", "title": "Hacker News"},
            {
                "url": "https://stackoverflow.com/questions/tagged/python",
                "title": "Python Questions - Stack Overflow",
            },
            {"url": "https://docs.python.org/3/", "title": "Python 3 Documentation"},
            {"url": "https://fastapi.tiangolo.com/", "title": "FastAPI Documentation"},
            {"url": "https://www.reddit.com/r/programming", "title": "r/programming"},
            {"url": "https://techcrunch.com", "title": "TechCrunch"},
            {
                "url": "https://arxiv.org/list/cs.AI/recent",
                "title": "Recent AI Papers - arXiv",
            },
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Interesting Video",
            },
            {
                "url": "https://medium.com/@author/machine-learning-article",
                "title": "ML Article - Medium",
            },
        ]

        for i in range(min(num_visits, len(sample_sites))):
            site = sample_sites[i]

            visit = WebVisit(
                device_id=settings.device_id,
                url=site["url"],
                title=site["title"],
                visit_time=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                visit_duration=random.randint(30, 600),  # 30 seconds to 10 minutes
                browser=random.choice(["chrome", "firefox", "safari"]),
                tab_count=random.randint(3, 15),
                is_incognito=random.choice(
                    [True, False, False, False]
                ),  # 25% incognito
            )
            mock_visits.append(visit)

        logger.info(f"Generated {len(mock_visits)} mock web visits")
        return mock_visits
