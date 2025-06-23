# Loom Scheduled Consumers

Scheduled consumers service for collecting external data from various sources including email, social media, web browsing, and RSS feeds.

## Overview

This service runs scheduled data collection jobs that gather information from external sources and publish it to Kafka topics for processing by the Loom v2 pipeline.

## Supported Data Sources

### 📧 Email (Gmail API)
- **Topic**: `external.email.events.raw`
- **Interval**: 15-30 minutes (configurable)
- **Data**: Email metadata, content, labels, read status
- **Requirements**: Gmail API credentials

### 🐦 Twitter/X Likes
- **Topic**: `external.twitter.liked.raw`
- **Interval**: 60 minutes (configurable)
- **Data**: Liked tweets, metadata, engagement stats
- **Requirements**: Twitter API Bearer Token

### 📰 Hacker News Activity
- **Topic**: `external.hackernews.activity.raw`
- **Interval**: 60 minutes (configurable)
- **Data**: Upvoted stories, comments, submissions
- **Requirements**: Hacker News username

### 🌐 Web Browsing History
- **Topic**: `external.web.visits.raw`
- **Interval**: 10-15 minutes (configurable)
- **Data**: Visited URLs, page titles, visit duration
- **Requirements**: Browser history database access

### 📊 Reddit Activity
- **Topic**: `external.reddit.activity.raw`
- **Interval**: 60 minutes (configurable)
- **Data**: Upvoted posts, saved items, comments
- **Requirements**: Reddit API credentials

### 📰 RSS Feeds
- **Topic**: `external.rss.items.raw`
- **Interval**: 60 minutes (configurable)
- **Data**: Latest feed items, content, categories
- **Requirements**: RSS feed URLs

## Configuration

Set environment variables with the `LOOM_` prefix:

```bash
# Kafka Configuration
LOOM_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
LOOM_DEVICE_ID=my-device

# Scheduling Intervals (minutes)
LOOM_EMAIL_CHECK_INTERVAL_MINUTES=15
LOOM_CALENDAR_SYNC_INTERVAL_MINUTES=30
LOOM_SOCIAL_MEDIA_CHECK_INTERVAL_MINUTES=60
LOOM_WEB_ACTIVITY_CHECK_INTERVAL_MINUTES=10

# API Credentials
LOOM_TWITTER_BEARER_TOKEN=your_bearer_token
LOOM_GMAIL_CREDENTIALS_PATH=/path/to/gmail_credentials.json
LOOM_HACKERNEWS_USER_ID=your_hn_username
LOOM_REDDIT_CLIENT_ID=your_reddit_client_id
LOOM_REDDIT_CLIENT_SECRET=your_reddit_secret

# Browser Paths (optional - auto-detected)
LOOM_CHROME_HISTORY_PATH=/path/to/chrome/History
LOOM_FIREFOX_HISTORY_PATH=/path/to/firefox/places.sqlite

# RSS Feeds (JSON array)
LOOM_RSS_FEEDS='["https://feeds.example.com/rss", "https://blog.example.com/feed"]'
```

## Data Retention Policies

| Data Type | Topic | Retention Period | Reason |
|-----------|-------|------------------|---------|
| Email | `external.email.events.raw` | 90 days | Important communication history |
| Calendar | `external.calendar.events.raw` | 365 days | Long-term scheduling data |
| Twitter | `external.twitter.liked.raw` | 365 days | Social media engagement patterns |
| Reddit | `external.reddit.activity.raw` | 180 days | Discussion participation |
| Hacker News | `external.hackernews.activity.raw` | 180 days | Tech news engagement |
| Web Visits | `external.web.visits.raw` | 30 days | Recent browsing patterns |
| RSS Items | `external.rss.items.raw` | 90 days | Content consumption tracking |
| Job Status | `internal.scheduled.jobs.status` | 7 days | Monitoring and debugging |

## Data Models

### Email Event
```json
{
  "message_id_external": "gmail_message_id",
  "from_address": "sender@example.com",
  "to_addresses": ["recipient@example.com"],
  "subject": "Email subject",
  "body_text": "Email content...",
  "is_read": true,
  "labels": ["inbox", "important"],
  "received_date": "2024-01-01T12:00:00Z"
}
```

### Twitter Like
```json
{
  "tweet_id": "1234567890",
  "tweet_url": "https://twitter.com/user/status/1234567890",
  "author_username": "username",
  "tweet_text": "Tweet content...",
  "created_at": "2024-01-01T12:00:00Z",
  "liked_at": "2024-01-01T13:00:00Z",
  "like_count": 150,
  "hashtags": ["ai", "tech"]
}
```

### Web Visit
```json
{
  "url": "https://example.com/page",
  "title": "Page Title",
  "visit_time": "2024-01-01T12:00:00Z",
  "visit_duration": 120,
  "browser": "chrome",
  "tab_count": 8
}
```

## Architecture

### Components

1. **Base Consumer**: Abstract class for all scheduled data collectors
2. **Scheduler**: Manages multiple consumers and their execution
3. **Kafka Producer**: Sends collected data to appropriate topics
4. **Individual Consumers**: Specialized collectors for each data source

### Consumer Lifecycle

1. **Initialization**: Consumer registers with scheduler
2. **Scheduled Execution**: Runs at configured intervals
3. **Data Collection**: Fetches data from external source
4. **Data Publishing**: Sends data to Kafka topic
5. **Status Reporting**: Reports execution status for monitoring

### Error Handling

- **Retry Logic**: Failed jobs are retried with exponential backoff
- **Mock Data**: Falls back to mock data when APIs are unavailable
- **Graceful Degradation**: Service continues running if individual consumers fail
- **Status Monitoring**: Job status published to monitoring topic

## Development

### Running Locally

```bash
# Install dependencies
cd services/scheduled-consumers
pip install -e .

# Set environment variables
export LOOM_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export LOOM_DEVICE_ID=dev-device

# Run service
python -m app.main
```

### Adding New Consumers

1. Create consumer class inheriting from `BaseConsumer`
2. Implement `collect_data()` and `get_kafka_topic()` methods
3. Add to scheduler in `scheduler.py`
4. Add topic configuration to ingestion API
5. Update documentation

### Testing

```bash
# Run unit tests
pytest tests/

# Run specific consumer manually
python -c "
from app.consumers.email_consumer import EmailConsumer
import asyncio

async def test():
    consumer = EmailConsumer()
    data = await consumer.collect_data()
    print(f'Collected {len(data)} items')

asyncio.run(test())
"
```

## Monitoring

The service publishes job status to `internal.scheduled.jobs.status` topic:

```json
{
  "job_id": "email_sync_device_123",
  "job_type": "email_sync",
  "last_run": "2024-01-01T12:00:00Z",
  "status": "completed",
  "items_processed": 5,
  "execution_duration": 2.5
}
```

### Key Metrics

- **Items Processed**: Number of items collected per run
- **Execution Duration**: Time taken for each job
- **Success Rate**: Percentage of successful executions
- **Error Rate**: Frequency of failures

## Privacy & Security

- **No Raw Credentials**: API tokens stored as environment variables only
- **Local Processing**: Data processed locally before sending to Kafka
- **Configurable Retention**: Data automatically expires per retention policies
- **Browser Access**: Read-only access to browser history databases
- **Mock Mode**: Service runs with mock data when credentials unavailable

## Future Enhancements

- **Calendar Integration**: Google Calendar, Outlook support
- **Slack/Discord**: Workspace activity tracking
- **LinkedIn**: Professional network activity
- **GitHub**: Repository activity and commits
- **Spotify/Apple Music**: Music listening history
- **Location Services**: GPS location history
- **Health Data**: Fitness tracker integration