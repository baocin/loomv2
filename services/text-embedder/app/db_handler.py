"""Database handler for storing emails and tweets with embeddings."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dateutil import parser

import asyncpg
import structlog

logger = structlog.get_logger()


class DatabaseHandler:
    """Handles database operations for emails and tweets with embeddings."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Connect to the database and create tables if needed."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )

        # Create tables if they don't exist
        await self.create_tables()
        logger.info("Database connection established and tables created")

    async def disconnect(self):
        """Disconnect from the database."""
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        """Create required tables for emails and tweets with embeddings."""
        async with self.pool.acquire() as conn:
            # Create emails table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS emails_with_embeddings (
                    id SERIAL PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    message_id TEXT,
                    device_id TEXT,
                    timestamp TIMESTAMPTZ NOT NULL,
                    received_at TIMESTAMPTZ DEFAULT NOW(),

                    -- Email fields
                    subject TEXT,
                    sender_name TEXT,
                    sender_email TEXT,
                    recipient_email TEXT,
                    body_text TEXT,
                    body_html TEXT,
                    headers JSONB,
                    attachments JSONB,
                    folder TEXT,
                    email_source TEXT,

                    -- Embedding fields
                    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim embeddings
                    embedding_model TEXT,
                    embedding_timestamp TIMESTAMPTZ DEFAULT NOW(),

                    -- Metadata
                    metadata JSONB,

                    -- Constraints
                    UNIQUE(trace_id)
                )
            """
            )

            # Create Twitter likes table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS twitter_likes_with_embeddings (
                    id SERIAL PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    tweet_id TEXT NOT NULL,
                    device_id TEXT,
                    timestamp TIMESTAMPTZ NOT NULL,
                    liked_at TIMESTAMPTZ,
                    received_at TIMESTAMPTZ DEFAULT NOW(),

                    -- Tweet fields
                    tweet_url TEXT,
                    tweet_text TEXT,
                    author_username TEXT,
                    author_name TEXT,
                    author_profile_url TEXT,

                    -- Embedding fields
                    embedding vector(384),
                    embedding_model TEXT,
                    embedding_timestamp TIMESTAMPTZ DEFAULT NOW(),

                    -- Screenshot/extraction reference
                    screenshot_url TEXT,
                    extracted_content JSONB,
                    extraction_timestamp TIMESTAMPTZ,

                    -- Metadata
                    metadata JSONB,

                    -- Constraints
                    UNIQUE(trace_id),
                    UNIQUE(tweet_id)
                )
            """
            )

            # Create indexes for emails table
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_emails_timestamp ON emails_with_embeddings (timestamp DESC)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails_with_embeddings (sender_email)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_emails_device ON emails_with_embeddings (device_id)"
            )

            # Create indexes for twitter table
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_twitter_timestamp ON twitter_likes_with_embeddings (timestamp DESC)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_twitter_author ON twitter_likes_with_embeddings (author_username)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_twitter_device ON twitter_likes_with_embeddings (device_id)"
            )

            # Create vector similarity index for semantic search
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_emails_embedding
                ON emails_with_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_twitter_embedding
                ON twitter_likes_with_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """
            )

            logger.info("Database tables created successfully")

    async def store_email_with_embedding(
        self, email_data: Dict[str, Any], embedding: List[float], trace_id: str
    ) -> int:
        """Store an email with its embedding."""
        async with self.pool.acquire() as conn:
            # Convert embedding to PostgreSQL array format
            embedding_str = f"[{','.join(map(str, embedding))}]"

            # Map incoming data fields to database schema
            # Handle both direct fields and Kafka message format with 'data' wrapper
            data = email_data.get("data", email_data)  # Support both formats

            # Extract sender information - handle multiple field name formats
            sender_email = None
            sender_name = None

            # Parse sender field: "Name <email@domain.com>" or just "email@domain.com"
            sender_raw = (
                data.get("sender")
                or data.get("sender_email")
                or data.get("from_address")
            )
            if sender_raw:
                import re

                # Try to parse "Name <email@domain.com>" format
                match = re.match(r"^(.+?)\s*<(.+?)>$", sender_raw)
                if match:
                    sender_name = match.group(1).strip()
                    sender_email = match.group(2).strip()
                else:
                    # Just an email address
                    sender_email = sender_raw.strip()

            # Extract recipient information
            recipient_email = data.get("receiver") or data.get("recipient_email")
            if (
                not recipient_email
                and data.get("to_addresses")
                and isinstance(data.get("to_addresses"), list)
            ):
                recipient_email = (
                    data.get("to_addresses")[0] if data.get("to_addresses") else None
                )

            query = """
                INSERT INTO emails_with_embeddings (
                    trace_id, message_id, device_id, timestamp,
                    subject, sender_name, sender_email, recipient_email,
                    body_text, body_html, headers, attachments,
                    folder, email_source, embedding, embedding_model,
                    metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15::vector, $16, $17)
                ON CONFLICT (trace_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding_timestamp = NOW()
                RETURNING id
            """

            row = await conn.fetchrow(
                query,
                trace_id,
                data.get("email_id") or data.get("message_id"),
                email_data.get("device_id") or data.get("device_id"),
                self._parse_timestamp(
                    email_data.get("timestamp")
                    or data.get("timestamp")
                    or data.get("date_received")
                ),
                data.get("subject"),
                sender_name,
                sender_email,
                recipient_email,
                data.get("body")
                or data.get("body_text"),  # Use "body" field from actual data
                data.get("body_html"),
                json.dumps(data.get("headers") or data.get("metadata", {})),
                json.dumps(data.get("attachments", [])),
                str(data.get("folder") or data.get("labels", [])),
                data.get("account_name")
                or data.get("source_account")
                or "email_fetcher",
                embedding_str,
                "sentence-transformers/all-MiniLM-L6-v2",
                json.dumps(email_data.get("metadata", {})),
            )

            return row["id"]

    async def store_twitter_with_embedding(
        self,
        tweet_data: Dict[str, Any],
        embedding: List[float],
        trace_id: str,
        tweet_id: str,
    ) -> int:
        """Store a Twitter like with its embedding."""
        async with self.pool.acquire() as conn:
            # Convert embedding to PostgreSQL array format
            embedding_str = f"[{','.join(map(str, embedding))}]"

            query = """
                INSERT INTO twitter_likes_with_embeddings (
                    trace_id, tweet_id, device_id, timestamp, liked_at,
                    tweet_url, tweet_text, author_username, author_name,
                    author_profile_url, embedding, embedding_model, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::vector, $12, $13)
                ON CONFLICT (tweet_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding_timestamp = NOW()
                RETURNING id
            """

            row = await conn.fetchrow(
                query,
                trace_id,
                tweet_id,
                tweet_data.get("device_id"),
                self._parse_timestamp(tweet_data.get("timestamp")),
                self._parse_timestamp(tweet_data.get("time")),  # liked_at from scraper
                tweet_data.get("url", tweet_data.get("tweetLink")),
                tweet_data.get("text", tweet_data.get("content")),
                tweet_data.get("author", tweet_data.get("author_username")),
                tweet_data.get("author_name"),
                tweet_data.get("profile_link", tweet_data.get("profileLink")),
                embedding_str,
                "sentence-transformers/all-MiniLM-L6-v2",
                json.dumps(tweet_data.get("metadata", {})),
            )

            return row["id"]

    async def update_twitter_screenshot(
        self, tweet_id: str, screenshot_url: str, extracted_content: Dict[str, Any]
    ):
        """Update Twitter entry with screenshot and extracted content."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE twitter_likes_with_embeddings
                SET screenshot_url = $1,
                    extracted_content = $2,
                    extraction_timestamp = NOW()
                WHERE tweet_id = $3
            """,
                screenshot_url,
                json.dumps(extracted_content),
                tweet_id,
            )

    async def find_similar_emails(self, embedding: List[float], limit: int = 10):
        """Find similar emails using vector similarity."""
        async with self.pool.acquire() as conn:
            embedding_str = f"[{','.join(map(str, embedding))}]"

            rows = await conn.fetch(
                """
                SELECT id, trace_id, subject, sender_email, timestamp,
                       1 - (embedding <=> $1::vector) as similarity
                FROM emails_with_embeddings
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """,
                embedding_str,
                limit,
            )

            return [dict(row) for row in rows]

    async def find_similar_tweets(self, embedding: List[float], limit: int = 10):
        """Find similar tweets using vector similarity."""
        async with self.pool.acquire() as conn:
            embedding_str = f"[{','.join(map(str, embedding))}]"

            rows = await conn.fetch(
                """
                SELECT id, trace_id, tweet_id, tweet_text, author_username,
                       1 - (embedding <=> $1::vector) as similarity
                FROM twitter_likes_with_embeddings
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """,
                embedding_str,
                limit,
            )

            return [dict(row) for row in rows]

    def _parse_timestamp(self, timestamp_value: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if timestamp_value is None:
            return datetime.utcnow()
        if isinstance(timestamp_value, datetime):
            return timestamp_value
        if isinstance(timestamp_value, str):
            try:
                return parser.isoparse(timestamp_value)
            except (ValueError, TypeError):
                return datetime.utcnow()
        return datetime.utcnow()
