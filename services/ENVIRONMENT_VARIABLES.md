# Environment Variables Documentation

This document lists all the LOOM-prefixed environment variables used by the calendar, email, and HackerNews fetcher services.

## Common Kafka Configuration

These variables are used by all services for Kafka connectivity:

- `LOOM_KAFKA_BOOTSTRAP_SERVERS` - Kafka bootstrap servers (default: `localhost:9092`)
- `LOOM_KAFKA_TOPIC_PREFIX` - Topic prefix to add to all topics (default: empty)
- `LOOM_LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)

## Calendar Fetcher Service

### Service Configuration
- `LOOM_CALENDAR_FETCH_INTERVAL_MINUTES` - Interval between calendar fetches in minutes (default: `30`)
- `LOOM_CALENDAR_RUN_ON_STARTUP` - Run immediately on startup: true/false (default: `true`)
- `LOOM_KAFKA_OUTPUT_TOPIC` - Output Kafka topic (default: `external.calendar.events.raw`)

### Calendar Settings
- `LOOM_CALENDAR_DAYS_PAST` - Number of days in the past to fetch events (default: `30`)
- `LOOM_CALENDAR_DAYS_FUTURE` - Number of days in the future to fetch events (default: `365`)
- `LOOM_CALENDAR_ENABLE_GPS_LOOKUP` - Enable GPS coordinate lookup for locations: true/false (default: `true`)
- `LOOM_NOMINATIM_BASE_URL` - Nominatim geocoding service URL (default: `http://localhost:8080`)
- `LOOM_CALENDAR_MAX_ACCOUNTS` - Maximum number of calendar accounts to support (default: `10`)

### CalDAV Account Configuration
For each calendar account (where N is 1-10):
- `LOOM_CALDAV_URL_N` - CalDAV server URL for account N
- `LOOM_CALDAV_USERNAME_N` - Username for account N
- `LOOM_CALDAV_PASSWORD_N` - Password for account N
- `LOOM_CALDAV_DISABLED_N` - Disable account N: true/false (default: `false`)
- `LOOM_CALDAV_NAME_N` - Display name for account N (default: `Calendar N`)

Example:
```bash
LOOM_CALDAV_URL_1=https://caldav.example.com/dav/
LOOM_CALDAV_USERNAME_1=user@example.com
LOOM_CALDAV_PASSWORD_1=secret
LOOM_CALDAV_NAME_1=Work Calendar
```

## HackerNews Fetcher Service

### Service Configuration
- `LOOM_HACKERNEWS_FETCH_INTERVAL_MINUTES` - Interval between fetches in minutes (default: `120`)
- `LOOM_HACKERNEWS_RUN_ON_STARTUP` - Run immediately on startup: true/false (default: `true`)
- `LOOM_KAFKA_OUTPUT_TOPIC` - Output Kafka topic (default: `task.likes.hackernews`)

### HackerNews Settings
- `LOOM_HACKERNEWS_USERNAME` - HackerNews username (required)
- `LOOM_HACKERNEWS_PASSWORD` - HackerNews password (optional, for favorites access)
- `LOOM_HACKERNEWS_API_URL` - HackerNews API URL (default: `https://hacker-news.firebaseio.com/v0`)
- `LOOM_HACKERNEWS_BASE_URL` - HackerNews web URL (default: `https://news.ycombinator.com`)
- `LOOM_HACKERNEWS_MAX_ITEMS` - Maximum number of items to fetch (default: `50`)
- `LOOM_HACKERNEWS_FETCH_TYPE` - Type of items to fetch: favorites/submissions (default: `favorites`)
- `LOOM_HACKERNEWS_USE_BROWSER` - Use browser for fetching favorites: true/false (default: `true`)
- `LOOM_HACKERNEWS_RATE_LIMIT_SECONDS` - Rate limit between API requests in seconds (default: `0.5`)

## Email Fetcher Service

### Service Configuration
- `LOOM_EMAIL_FETCH_INTERVAL_MINUTES` - Interval between email fetches in minutes (default: `5`)
- `LOOM_EMAIL_RUN_ON_STARTUP` - Run immediately on startup: true/false (default: `true`)
- `LOOM_KAFKA_OUTPUT_TOPIC` - Output Kafka topic (default: `external.email.events.raw`)

### Email Settings
- `LOOM_EMAIL_MAX_ACCOUNTS` - Maximum number of email accounts to support (default: `10`)
- `LOOM_EMAIL_SEARCH_CRITERIA` - IMAP search criteria: UNSEEN, ALL, etc. (default: `UNSEEN`)
- `LOOM_EMAIL_MAX_FETCH_PER_ACCOUNT` - Maximum emails to fetch per account per run (default: `50`)

### IMAP Account Configuration
For each email account (where N is 1-10):
- `LOOM_EMAIL_ADDRESS_N` - Email address for account N
- `LOOM_EMAIL_PASSWORD_N` - Password for account N
- `LOOM_EMAIL_IMAP_SERVER_N` - IMAP server for account N (default: `imap.gmail.com`)
- `LOOM_EMAIL_IMAP_PORT_N` - IMAP port for account N (default: `993`)
- `LOOM_EMAIL_DISABLED_N` - Disable account N: true/false (default: `false`)
- `LOOM_EMAIL_NAME_N` - Display name for account N (default: `Email N`)

Example:
```bash
LOOM_EMAIL_ADDRESS_1=user@example.com
LOOM_EMAIL_PASSWORD_1=app-specific-password
LOOM_EMAIL_IMAP_SERVER_1=imap.gmail.com
LOOM_EMAIL_IMAP_PORT_1=993
LOOM_EMAIL_NAME_1=Personal Gmail
```

## HackerNews URL Processor Service

### Service Configuration
- `LOOM_KAFKA_INPUT_TOPIC` - Input Kafka topic to consume from (default: `task.likes.hackernews`)
- `LOOM_KAFKA_OUTPUT_TOPIC` - Output Kafka topic (default: `task.url.processed.hackernews_archived`)
- `LOOM_KAFKA_CONSUMER_GROUP` - Kafka consumer group ID (default: `hackernews-url-processor`)

### URL Processing Settings
- `LOOM_URL_PROCESSOR_ENABLE_SCREENSHOTS` - Enable webpage screenshots: true/false (default: `true`)
- `LOOM_URL_PROCESSOR_PDF_MAX_PAGES` - Maximum pages to extract from PDFs (default: `100`)
- `LOOM_URL_PROCESSOR_TEXT_MAX_CHARS` - Maximum characters to extract from content (default: `50000`)
- `LOOM_URL_PROCESSOR_REQUEST_TIMEOUT` - HTTP request timeout in seconds (default: `30`)
- `LOOM_URL_PROCESSOR_SCREENSHOT_TIMEOUT` - Screenshot timeout in milliseconds (default: `10000`)

## Docker Compose Example

```yaml
services:
  calendar-fetcher:
    image: loom/calendar-fetcher:latest
    environment:
      LOOM_KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      LOOM_KAFKA_OUTPUT_TOPIC: external.calendar.events.raw
      LOOM_CALENDAR_FETCH_INTERVAL_MINUTES: 30
      LOOM_CALDAV_URL_1: https://caldav.example.com/dav/
      LOOM_CALDAV_USERNAME_1: user@example.com
      LOOM_CALDAV_PASSWORD_1: ${CALDAV_PASSWORD}
      LOOM_CALDAV_NAME_1: Work Calendar

  hackernews-fetcher:
    image: loom/hackernews-fetcher:latest
    environment:
      LOOM_KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      LOOM_KAFKA_OUTPUT_TOPIC: task.likes.hackernews
      LOOM_HACKERNEWS_USERNAME: ${HN_USERNAME}
      LOOM_HACKERNEWS_PASSWORD: ${HN_PASSWORD}
      LOOM_HACKERNEWS_FETCH_INTERVAL_MINUTES: 120
      LOOM_HACKERNEWS_MAX_ITEMS: 100

  hackernews-url-processor:
    image: loom/hackernews-url-processor:latest
    environment:
      LOOM_KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      LOOM_KAFKA_INPUT_TOPIC: task.likes.hackernews
      LOOM_KAFKA_OUTPUT_TOPIC: task.url.processed.hackernews_archived
      LOOM_URL_PROCESSOR_ENABLE_SCREENSHOTS: true
      LOOM_URL_PROCESSOR_TEXT_MAX_CHARS: 100000

  email-fetcher:
    image: loom/email-fetcher:latest
    environment:
      LOOM_KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      LOOM_KAFKA_OUTPUT_TOPIC: external.email.events.raw
      LOOM_EMAIL_FETCH_INTERVAL_MINUTES: 5
      LOOM_EMAIL_ADDRESS_1: user@gmail.com
      LOOM_EMAIL_PASSWORD_1: ${GMAIL_APP_PASSWORD}
      LOOM_EMAIL_NAME_1: Personal Gmail
      LOOM_EMAIL_ADDRESS_2: work@company.com
      LOOM_EMAIL_PASSWORD_2: ${WORK_EMAIL_PASSWORD}
      LOOM_EMAIL_IMAP_SERVER_2: imap.company.com
      LOOM_EMAIL_NAME_2: Work Email
```
