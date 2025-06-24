"""Database manager for OneFileLLM service."""

from typing import Any

import asyncpg
import structlog

from .config import settings
from .models import ProcessedDocument, ProcessedGitHub

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        """Initialize database manager."""
        self.pool: asyncpg.Pool | None = None
        self.is_connected = False

    async def start(self) -> None:
        """Start database connection pool."""
        logger.info("Starting database connection pool")

        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={
                    "application_name": "onefilellm-service",
                },
            )

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            self.is_connected = True
            logger.info("Database connection pool started successfully")

        except Exception as e:
            logger.error("Failed to start database connection pool", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop database connection pool."""
        logger.info("Stopping database connection pool")

        if self.pool:
            await self.pool.close()

        self.is_connected = False
        logger.info("Database connection pool stopped")

    async def store_processed_github(self, result: ProcessedGitHub) -> None:
        """Store processed GitHub result in database.

        Args:
            result: Processed GitHub content
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        query = """
        INSERT INTO processed_github_parsed (
            schema_version, device_id, recorded_at, timestamp, message_id,
            original_url, repository_name, repository_type, aggregated_content,
            content_summary, file_count, total_size_bytes, processing_duration_ms,
            files_processed, files_skipped, extraction_metadata, onefilellm_version
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
        )
        """

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    result.schema_version,
                    result.device_id,
                    result.recorded_at,
                    result.timestamp,
                    result.message_id,
                    result.original_url,
                    result.repository_name,
                    result.repository_type,
                    result.aggregated_content,
                    result.content_summary,
                    result.file_count,
                    result.total_size_bytes,
                    result.processing_duration_ms,
                    result.files_processed,
                    result.files_skipped,
                    result.extraction_metadata,
                    result.onefilellm_version,
                )

            logger.info(
                "Stored processed GitHub result",
                message_id=result.message_id,
                repository_name=result.repository_name,
            )

        except Exception as e:
            logger.error(
                "Failed to store processed GitHub result",
                message_id=result.message_id,
                error=str(e),
            )
            raise

    async def store_processed_document(self, result: ProcessedDocument) -> None:
        """Store processed document result in database.

        Args:
            result: Processed document content
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        query = """
        INSERT INTO processed_document_parsed (
            schema_version, device_id, recorded_at, timestamp, message_id,
            original_filename, document_type, content_type, extracted_text,
            content_summary, original_size_bytes, processing_duration_ms,
            extraction_method, language_detected, page_count, word_count,
            character_count, extraction_metadata, onefilellm_version
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
        )
        """

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    result.schema_version,
                    result.device_id,
                    result.recorded_at,
                    result.timestamp,
                    result.message_id,
                    result.original_filename,
                    result.document_type,
                    result.content_type,
                    result.extracted_text,
                    result.content_summary,
                    result.original_size_bytes,
                    result.processing_duration_ms,
                    result.extraction_method,
                    result.language_detected,
                    result.page_count,
                    result.word_count,
                    result.character_count,
                    result.extraction_metadata,
                    result.onefilellm_version,
                )

            logger.info(
                "Stored processed document result",
                message_id=result.message_id,
                filename=result.original_filename,
            )

        except Exception as e:
            logger.error(
                "Failed to store processed document result",
                message_id=result.message_id,
                error=str(e),
            )
            raise

    async def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics from database.

        Returns:
            Dictionary with processing statistics
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                github_stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_processed,
                        AVG(processing_duration_ms) as avg_duration_ms,
                        SUM(file_count) as total_files,
                        SUM(total_size_bytes) as total_bytes
                    FROM processed_github_parsed
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """
                )

                document_stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_processed,
                        AVG(processing_duration_ms) as avg_duration_ms,
                        SUM(word_count) as total_words,
                        SUM(original_size_bytes) as total_bytes
                    FROM processed_document_parsed
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """
                )

                return {
                    "github": dict(github_stats) if github_stats else {},
                    "documents": dict(document_stats) if document_stats else {},
                }

        except Exception as e:
            logger.error("Failed to get processing stats", error=str(e))
            return {"github": {}, "documents": {}}
