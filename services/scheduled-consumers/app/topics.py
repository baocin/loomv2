"""Kafka topics for scheduled consumers."""

# External data ingestion topics with retention policies
EXTERNAL_DATA_TOPICS = {
    # Email data
    "external.email.events.raw": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "7776000000",  # 90 days
            "compression.type": "producer",
        },
    },
    # Calendar data
    "external.calendar.events.raw": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "31536000000",  # 365 days
            "compression.type": "producer",
        },
    },
    # Social media data
    "external.twitter.liked.raw": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "31536000000",  # 365 days
            "compression.type": "producer",
        },
    },
    # Hacker News data
    "external.hackernews.activity.raw": {
        "partitions": 2,
        "replication_factor": 1,
        "config": {
            "retention.ms": "15552000000",  # 180 days
            "compression.type": "producer",
        },
    },
    # Web browsing data
    "external.web.visits.raw": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {
            "retention.ms": "2592000000",  # 30 days
            "compression.type": "producer",
        },
    },
    # RSS feed data
    "external.rss.items.raw": {
        "partitions": 2,
        "replication_factor": 1,
        "config": {
            "retention.ms": "7776000000",  # 90 days
            "compression.type": "producer",
        },
    },
    # Job status and monitoring
    "internal.scheduled.jobs.status": {
        "partitions": 1,
        "replication_factor": 1,
        "config": {
            "retention.ms": "604800000",  # 7 days
            "compression.type": "producer",
            "cleanup.policy": "compact",  # Keep latest status per job
        },
    },
}
