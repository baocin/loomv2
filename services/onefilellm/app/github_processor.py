"""GitHub repository processor using OneFileLLM."""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import git
import structlog
from onefilellm import OneFileLLM

from .config import settings
from .models import GitHubTask, ProcessedGitHub, ProcessingError

logger = structlog.get_logger(__name__)


class GitHubProcessor:
    """Processes GitHub repositories using OneFileLLM."""

    def __init__(self, kafka_producer, database):
        """Initialize GitHub processor.

        Args:
            kafka_producer: KafkaProducerManager instance
            database: DatabaseManager instance
        """
        self.kafka_producer = kafka_producer
        self.database = database

    async def process_github_task(self, task: GitHubTask) -> None:
        """Process a GitHub task.

        Args:
            task: GitHub processing task
        """
        start_time = time.time()

        logger.info(
            "Processing GitHub task",
            message_id=task.message_id,
            url=task.url,
            repository_type=task.repository_type,
        )

        try:
            # Parse GitHub URL
            repo_info = self._parse_github_url(task.url)
            if not repo_info:
                raise ValueError(f"Invalid GitHub URL: {task.url}")

            # Clone repository to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = await self._clone_repository(
                    repo_info["clone_url"], temp_dir, task.url
                )

                # Process with OneFileLLM
                result = await self._process_with_onefilellm(
                    task, repo_info, repo_path, start_time
                )

                # Send result to Kafka
                await self.kafka_producer.send_processed_github(result)

                # Store in database
                await self.database.store_processed_github(result)

                logger.info(
                    "GitHub task processed successfully",
                    message_id=task.message_id,
                    processing_time_ms=result.processing_duration_ms,
                    file_count=result.file_count,
                )

        except Exception as e:
            logger.error(
                "Failed to process GitHub task",
                message_id=task.message_id,
                url=task.url,
                error=str(e),
            )

            # Send error to Kafka
            error = ProcessingError(
                schema_version=task.schema_version,
                device_id=task.device_id,
                recorded_at=task.recorded_at,
                original_task_id=task.message_id,
                error_type="github_processing_error",
                error_message=str(e),
                error_details={
                    "url": task.url,
                    "repository_type": task.repository_type,
                },
                is_retryable=self._is_retryable_error(e),
            )

            await self.kafka_producer.send_processing_error(
                error, settings.topic_github_parsed
            )

    def _parse_github_url(self, url: str) -> dict[str, str] | None:
        """Parse GitHub URL to extract repository information.

        Args:
            url: GitHub URL

        Returns:
            Repository information or None if invalid
        """
        try:
            parsed = urlparse(url)
            if parsed.netloc != "github.com":
                return None

            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:
                return None

            owner = path_parts[0]
            repo = path_parts[1]

            # Remove .git suffix if present
            if repo.endswith(".git"):
                repo = repo[:-4]

            return {
                "owner": owner,
                "repo": repo,
                "clone_url": f"https://github.com/{owner}/{repo}.git",
                "full_name": f"{owner}/{repo}",
            }

        except Exception as e:
            logger.error("Failed to parse GitHub URL", url=url, error=str(e))
            return None

    async def _clone_repository(
        self, clone_url: str, temp_dir: str, original_url: str
    ) -> Path:
        """Clone GitHub repository.

        Args:
            clone_url: Git clone URL
            temp_dir: Temporary directory
            original_url: Original GitHub URL

        Returns:
            Path to cloned repository
        """
        repo_path = Path(temp_dir) / "repo"

        logger.info("Cloning repository", clone_url=clone_url)

        try:
            # Run git clone in a subprocess to avoid blocking
            def _clone():
                git.Repo.clone_from(
                    clone_url,
                    str(repo_path),
                    depth=1,  # Shallow clone for efficiency
                )

            # Run clone in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, _clone),
                timeout=settings.github_clone_timeout,
            )

            logger.info("Repository cloned successfully", path=str(repo_path))
            return repo_path

        except TimeoutError:
            raise Exception(
                f"Repository clone timed out after {settings.github_clone_timeout}s"
            )
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")

    async def _process_with_onefilellm(
        self,
        task: GitHubTask,
        repo_info: dict[str, str],
        repo_path: Path,
        start_time: float,
    ) -> ProcessedGitHub:
        """Process repository with OneFileLLM.

        Args:
            task: Original GitHub task
            repo_info: Repository information
            repo_path: Path to cloned repository
            start_time: Processing start time

        Returns:
            Processed GitHub result
        """
        logger.info("Processing with OneFileLLM", repo_path=str(repo_path))

        try:
            # Determine file patterns
            include_patterns = task.include_files or settings.default_include_patterns
            exclude_patterns = task.exclude_files or settings.default_exclude_patterns

            # Initialize OneFileLLM
            one_file_llm = OneFileLLM()

            # Run OneFileLLM processing in thread pool
            def _process():
                return one_file_llm.fit(
                    input_directory=str(repo_path),
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    max_file_size=task.max_file_size,
                )

            loop = asyncio.get_event_loop()
            llm_result = await asyncio.wait_for(
                loop.run_in_executor(None, _process),
                timeout=settings.processing_timeout,
            )

            # Get file processing stats
            files_processed, files_skipped = self._get_file_stats(
                repo_path, include_patterns, exclude_patterns, task.max_file_size
            )

            # Calculate processing duration
            processing_duration_ms = int((time.time() - start_time) * 1000)

            # Create result
            result = ProcessedGitHub(
                schema_version=task.schema_version,
                device_id=task.device_id,
                recorded_at=task.recorded_at,
                original_url=task.url,
                repository_name=repo_info["full_name"],
                repository_type=task.repository_type,
                aggregated_content=llm_result.content,
                content_summary=self._generate_summary(llm_result.content),
                file_count=len(files_processed),
                total_size_bytes=sum(f["size"] for f in files_processed),
                processing_duration_ms=processing_duration_ms,
                files_processed=files_processed,
                files_skipped=files_skipped,
                extraction_metadata={
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns,
                    "max_file_size": task.max_file_size,
                    "repo_info": repo_info,
                },
                onefilellm_version=self._get_onefilellm_version(),
            )

            return result

        except TimeoutError:
            raise Exception(
                f"OneFileLLM processing timed out after {settings.processing_timeout}s"
            )
        except Exception as e:
            raise Exception(f"OneFileLLM processing failed: {str(e)}")

    def _get_file_stats(
        self,
        repo_path: Path,
        include_patterns: list[str],
        exclude_patterns: list[str],
        max_file_size: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Get statistics about processed and skipped files.

        Args:
            repo_path: Repository path
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            max_file_size: Maximum file size

        Returns:
            Tuple of (processed_files, skipped_files)
        """
        import fnmatch

        processed_files = []
        skipped_files = []

        try:
            for file_path in repo_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(repo_path)
                    relative_str = str(relative_path)

                    # Check file size
                    try:
                        file_size = file_path.stat().st_size
                    except Exception:
                        continue

                    file_info = {
                        "path": relative_str,
                        "size": file_size,
                    }

                    # Check exclusion patterns first
                    excluded = any(
                        fnmatch.fnmatch(relative_str, pattern)
                        for pattern in exclude_patterns
                    )

                    if excluded:
                        file_info["reason"] = "excluded_by_pattern"
                        skipped_files.append(file_info)
                        continue

                    # Check inclusion patterns
                    included = any(
                        fnmatch.fnmatch(relative_str, pattern)
                        for pattern in include_patterns
                    )

                    if not included:
                        file_info["reason"] = "not_included_by_pattern"
                        skipped_files.append(file_info)
                        continue

                    # Check file size
                    if file_size > max_file_size:
                        file_info["reason"] = "file_too_large"
                        skipped_files.append(file_info)
                        continue

                    processed_files.append(file_info)

        except Exception as e:
            logger.warning("Failed to get file stats", error=str(e))

        return processed_files, skipped_files

    def _generate_summary(self, content: str) -> str:
        """Generate a brief summary of the aggregated content.

        Args:
            content: Aggregated file content

        Returns:
            Brief summary
        """
        # Simple summary generation
        lines = content.split("\n")
        total_lines = len(lines)
        total_chars = len(content)

        # Extract some file types mentioned
        file_extensions = set()
        for line in lines[:100]:  # Check first 100 lines for file mentions
            if line.strip().startswith("=== ") and line.strip().endswith(" ==="):
                # OneFileLLM typically formats file headers like this
                if "." in line:
                    ext = line.split(".")[-1].split()[0].lower()
                    if len(ext) <= 5:  # Reasonable extension length
                        file_extensions.add(ext)

        summary_parts = [
            f"Repository contains {total_lines:,} lines of code",
            f"({total_chars:,} characters)",
        ]

        if file_extensions:
            ext_list = sorted(file_extensions)[:5]  # Show top 5 extensions
            summary_parts.append(f"Primary file types: {', '.join(ext_list)}")

        return ". ".join(summary_parts) + "."

    def _get_onefilellm_version(self) -> str:
        """Get OneFileLLM version.

        Returns:
            OneFileLLM version string
        """
        try:
            import onefilellm

            return getattr(onefilellm, "__version__", "unknown")
        except Exception:
            return "unknown"

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable.

        Args:
            error: Exception that occurred

        Returns:
            True if error is retryable
        """
        error_str = str(error).lower()

        # Retryable errors
        retryable_indicators = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "rate limit",
        ]

        # Non-retryable errors
        non_retryable_indicators = [
            "not found",
            "invalid",
            "unauthorized",
            "forbidden",
            "permission denied",
        ]

        for indicator in non_retryable_indicators:
            if indicator in error_str:
                return False

        for indicator in retryable_indicators:
            if indicator in error_str:
                return True

        # Default to retryable for unknown errors
        return True
