# Loom v2 Data Fetcher Setup Guide

## 🚨 Issues Identified & Solutions

### Problem 1: Kafka Connection Error
**Error**: `Connect attempt to localhost:9092 returned error 111. Disconnecting.`

**Root Cause**: Fetcher services were configured with wrong environment variable names and trying to connect to `localhost` instead of the Docker network.

**Solution**: ✅ **FIXED** - Updated Docker Compose to use correct Kafka configuration:
- Changed from `LOOM_KAFKA_BOOTSTRAP_SERVERS` to `KAFKA_BOOTSTRAP_SERVERS`
- Set correct internal Docker hostname: `kafka:29092`
- Removed topic prefix to use full topic names

### Problem 2: Missing Credentials
**Error**: `X_USERNAME and X_PASSWORD environment variables are required`

**Root Cause**: Fetcher services need authentication credentials to access external APIs.

**Solution**: ✅ **CONFIGURED** - Added `.env` file support with credential templates.

## 🛠️ Setup Instructions

### Step 1: Configure Credentials

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials**:
   ```bash
   # Required for X/Twitter fetching
   X_USERNAME=your-twitter-username
   X_PASSWORD=your-twitter-password

   # Required for email fetching
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-gmail-app-password

   # Optional for calendar fetching
   GOOGLE_CALENDAR_CREDENTIALS_FILE=/app/credentials/google-calendar.json
   ```

### Step 2: Set Up Service-Specific Credentials

#### X/Twitter Fetcher
- **Username**: Your X/Twitter username (without @)
- **Password**: Your X/Twitter password
- **Phone Number**: May be required for some accounts (with country code: +1234567890)

#### Email Fetcher
- **Gmail**: Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password
- **Outlook**: Use your Outlook credentials
- **Custom**: Configure your IMAP server settings

#### Calendar Fetcher
- **Google**: Download credentials JSON from [Google Cloud Console](https://console.cloud.google.com/)
- **Outlook**: Create app registration in [Azure Portal](https://portal.azure.com/)

#### HackerNews Fetcher
- **No credentials required** - fetches public data

### Step 3: Start Services

```bash
# Start all services including fetchers
make dev-compose-up

# Check logs for specific services
docker compose -f docker-compose.local.yml logs -f x-likes-fetcher
docker compose -f docker-compose.local.yml logs -f email-fetcher
docker compose -f docker-compose.local.yml logs -f hackernews-fetcher
```

## 🔧 Service Configuration Details

### Fixed Kafka Configuration
```yaml
environment:
  KAFKA_BOOTSTRAP_SERVERS: kafka:29092  # ✅ Correct internal hostname
  KAFKA_TOPIC_PREFIX: ""                # ✅ No prefix, use full topic names
```

### Fetcher Intervals
- **HackerNews**: Every 15 minutes
- **Email**: Every 5 minutes
- **Calendar**: Every 10 minutes
- **X/Twitter**: Every 30 minutes

### Output Topics
- **HackerNews**: `external.hackernews.favorites.raw`
- **Email**: `external.email.events.raw`
- **Calendar**: `external.calendar.events.raw`
- **X/Twitter**: `external.twitter.liked.raw`

## 🎯 Testing & Verification

### 1. Check Service Health
```bash
# View all service status
docker compose -f docker-compose.local.yml ps

# Check specific service logs
docker compose -f docker-compose.local.yml logs x-likes-fetcher
```

### 2. Monitor Kafka Topics
```bash
# View Kafka UI
open http://localhost:8081

# Check if topics are receiving data
docker exec -it loomv2-kafka-1 kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic external.hackernews.favorites.raw \
  --from-beginning
```

### 3. Verify Data Pipeline
```bash
# Check Pipeline Monitor
open http://localhost:3000

# Should show:
# - All fetcher services as producers
# - Data flowing to external.* topics
# - Processing services consuming data
# - Data persisting to TimescaleDB
```

## 🚦 Expected Behavior

### Successful Startup Logs
```
✅ HackerNews Fetcher:
hackernews-fetcher - INFO - HackerNews fetcher service starting...
hackernews-fetcher - INFO - Successfully processed 10 stories

✅ Email Fetcher:
email-fetcher - INFO - Email fetcher service starting...
email-fetcher - INFO - Loaded 1 email accounts
email-fetcher - INFO - Successfully processed 5 emails

✅ X/Twitter Fetcher:
x-likes-fetcher - INFO - X.com likes fetcher service starting...
x-likes-fetcher - INFO - Successfully logged in to X.com
x-likes-fetcher - INFO - Successfully processed 25 liked tweets
```

## 🔒 Security Considerations

### Credential Management
- **Never commit `.env` to git** (already in `.gitignore`)
- **Use App Passwords** for Gmail, not main account password
- **Enable 2FA** on all accounts before creating app passwords
- **Rotate credentials** regularly

### Service Isolation
- Each fetcher runs in isolated Docker container
- No network access between fetcher containers
- Only Kafka and logging endpoints exposed

### Data Privacy
- Fetchers only collect metadata and URLs, not full content
- Personal emails/messages are not stored in full
- Data is processed locally, not sent to external services

## 🐛 Troubleshooting

### Common Issues

1. **Kafka Connection Refused**
   ```
   Solution: Make sure Kafka is running: docker compose ps kafka
   ```

2. **Authentication Failed (X/Twitter)**
   ```
   Solution: Check credentials in .env file, ensure no 2FA blocks
   ```

3. **Email Connection Failed**
   ```
   Solution: Use App Password for Gmail, enable IMAP access
   ```

4. **Container Build Failures**
   ```
   Solution: docker compose build --no-cache [service-name]
   ```

### Debug Commands
```bash
# Rebuild specific service
docker compose -f docker-compose.local.yml build hackernews-fetcher

# Run service in debug mode
docker compose -f docker-compose.local.yml up hackernews-fetcher

# Check container environment
docker compose exec hackernews-fetcher env | grep KAFKA
```

## 🎉 Result

After following this guide:
- ✅ All fetcher services connect to Kafka properly
- ✅ External data flows into the pipeline
- ✅ Complete end-to-end data processing works
- ✅ Credentials are securely managed via `.env`
- ✅ Real-time monitoring shows data flow
