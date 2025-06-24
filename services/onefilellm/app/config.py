"""Configuration management for OneFileLLM service."""


from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """OneFileLLM service configuration."""

    # Service configuration
    service_name: str = Field(default="onefilellm", env="SERVICE_NAME")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")

    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        env="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_group_id: str = Field(
        default="onefilellm-service",
        env="KAFKA_GROUP_ID",
    )
    kafka_auto_offset_reset: str = Field(
        default="latest",
        env="KAFKA_AUTO_OFFSET_RESET",
    )

    # Input topics (what we consume)
    topic_github_ingest: str = Field(
        default="task.github.ingest",
        env="TOPIC_GITHUB_INGEST",
    )
    topic_document_ingest: str = Field(
        default="task.document.ingest",
        env="TOPIC_DOCUMENT_INGEST",
    )

    # Output topics (what we produce)
    topic_github_parsed: str = Field(
        default="processed.github.parsed",
        env="TOPIC_GITHUB_PARSED",
    )
    topic_document_parsed: str = Field(
        default="processed.document.parsed",
        env="TOPIC_DOCUMENT_PARSED",
    )

    # Database configuration
    database_url: str = Field(
        default="postgresql://loom:loom@localhost:5432/loom",
        env="DATABASE_URL",
    )

    # Processing configuration
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")
    max_repo_files: int = Field(default=1000, env="MAX_REPO_FILES")
    github_clone_timeout: int = Field(
        default=300, env="GITHUB_CLONE_TIMEOUT"
    )  # seconds
    processing_timeout: int = Field(default=600, env="PROCESSING_TIMEOUT")  # seconds

    # GitHub configuration
    github_token: str = Field(
        default="", env="GITHUB_TOKEN"
    )  # Optional for public repos

    # File type filters
    default_include_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.py",
            "*.js",
            "*.ts",
            "*.jsx",
            "*.tsx",
            "*.java",
            "*.cpp",
            "*.c",
            "*.h",
            "*.cs",
            "*.go",
            "*.rs",
            "*.php",
            "*.rb",
            "*.swift",
            "*.kt",
            "*.scala",
            "*.md",
            "*.txt",
            "*.rst",
            "*.yaml",
            "*.yml",
            "*.json",
            "*.toml",
            "*.cfg",
            "*.ini",
            "*.xml",
            "*.html",
            "*.css",
            "*.sql",
            "*.sh",
            "*.bat",
            "*.ps1",
            "Dockerfile",
            "Makefile",
            "README*",
            "LICENSE*",
            "*.dockerfile",
        ],
    )

    default_exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "__pycache__/*",
            ".git/*",
            ".svn/*",
            "node_modules/*",
            "*.min.js",
            "*.min.css",
            "*.bundle.js",
            "vendor/*",
            "deps/*",
            "target/*",
            "build/*",
            "dist/*",
            "*.log",
            "*.tmp",
            "*.temp",
            "*.cache",
            "*.lock",
            "*.bin",
        ],
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
