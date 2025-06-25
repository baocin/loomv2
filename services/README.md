# External Data Fetchers and URL Processors

This directory contains self-contained Docker services for fetching external data and processing URLs from your personal accounts.

## Architecture Overview

The services follow a **producer-consumer pattern** using Kafka:

1. **Fetcher services** (producers) scrape personal account data and send URLs to specific Kafka topics
2. **URL processor services** (consumers) take URLs from topics, download/screenshot content, and send processed data to output topics

## Services

### Data Fetchers (Producers)

#### 1. Email Fetcher (`email-fetcher/`)
- **Purpose**: Fetches emails from IMAP accounts
- **Output Topic**: `external.email.events.raw`
- **Schedule**: Every 5 minutes
- **Environment Variables**:
  ```bash
  EMAIL_1=user@example.com
  EMAIL_PASSWORD_1=password
  EMAIL_IMAP_SERVER_1=imap.gmail.com
  EMAIL_PORT_1=993
  EMAIL_DISABLED_1=false
  # ... supports up to EMAIL_10
  ```

#### 2. Calendar Fetcher (`calendar-fetcher/`)
- **Purpose**: Fetches calendar events from CalDAV accounts
- **Output Topic**: `external.calendar.events.raw`
- **Schedule**: Every 30 minutes
- **Environment Variables**:
  ```bash
  CALDAV_URL_1=https://caldav.example.com/
  CALDAV_USERNAME_1=username
  CALDAV_PASSWORD_1=password
  CALDAV_DISABLED_1=false
  # ... supports up to CALDAV_10
  ```

#### 3. X.com Likes Fetcher (`x-likes-fetcher/`)
- **Purpose**: Scrapes your personal X.com liked tweets
- **Output Topic**: `task.likes.x`
- **Schedule**: Every 6 hours
- **Environment Variables**:
  ```bash
  X_USERNAME=your_username
  X_PASSWORD=your_password
  X_PHONE_NUMBER=your_phone  # Optional, for 2FA
  ```

#### 4. Hacker News Favorites Fetcher (`hackernews-fetcher/`)
- **Purpose**: Scrapes your personal HN favorites/upvoted items
- **Output Topic**: `task.likes.hackernews`
- **Schedule**: Every 2 hours
- **Environment Variables**:
  ```bash
  HACKERNEWS_USERNAME=your_hn_username
  HACKERNEWS_PASSWORD=your_hn_password  # Optional
  ```

### URL Processors (Consumers)

#### 5. X.com URL Processor (`x-url-processor/`)
- **Purpose**: Downloads X.com tweets with screenshots and metadata
- **Input Topic**: `task.likes.x`
- **Output Topic**: `task.url.processed.twitter_archived`
- **Features**:
  - Takes full-page screenshots of tweets
  - Extracts tweet metadata via XHR calls
  - Handles deleted/unavailable tweets gracefully

#### 6. Hacker News URL Processor (`hackernews-url-processor/`)
- **Purpose**: Downloads web pages, PDFs with screenshots and text extraction
- **Input Topic**: `task.likes.hackernews`
- **Output Topic**: `task.url.processed.hackernews_archived`
- **Features**:
  - Handles PDFs (text extraction)
  - Handles web pages (text extraction + screenshots)
  - Uses trafilatura for clean text extraction

## Kafka Topics

### Input Topics (Likes/Favorites)
- `task.likes.x` - X.com liked tweet URLs
- `task.likes.hackernews` - HackerNews favorited story URLs

### Direct Data Topics
- `external.email.events.raw` - Email data
- `external.calendar.events.raw` - Calendar event data

### Output Topics (Processed URLs)
- `task.url.processed.twitter_archived` - Processed X.com content
- `task.url.processed.hackernews_archived` - Processed web content

## Common Environment Variables

All services support these Kafka configuration variables:

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=loom
KAFKA_CONSUMER_GROUP=service-name  # Auto-set per service
```

## Deployment

Each service can be built and run independently:

```bash
# Build a service
cd email-fetcher/
docker build -t loom/email-fetcher .

# Run with environment file
docker run --env-file .env loom/email-fetcher

# Or with docker-compose
docker-compose up email-fetcher
```

## Data Flow

```
Personal Accounts → Fetcher Services → Kafka Topics → URL Processors → Processed Data Topics
                                        ↓
                              Direct Data (Email/Calendar)
```

### Example Flow:
1. `x-likes-fetcher` scrapes your X.com likes → sends URLs to `task.likes.x`
2. `x-url-processor` consumes from `task.likes.x` → downloads tweets with screenshots → sends to `task.url.processed.twitter_archived`
3. Downstream AI services can consume processed data for analysis

## Features

- **Self-contained**: Each service has its own dependencies and Dockerfile
- **Resilient**: Comprehensive error handling and rate limiting
- **Respectful**: Follows API rate limits and robots.txt
- **Screenshot capable**: Uses Playwright for visual content capture
- **Content extraction**: Handles PDFs, web pages, and social media
- **Personal focus**: Only fetches data from your own accounts
- **Kafka native**: Integrates seamlessly with existing Loom v2 architecture
