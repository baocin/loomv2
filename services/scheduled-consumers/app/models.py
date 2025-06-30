"""Data models for scheduled consumers."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message structure for all Kafka messages."""

    schema_version: str = Field(default="1.0", description="Message schema version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    device_id: str = Field(description="Device identifier")
    message_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique message ID"
    )


class EmailEvent(BaseMessage):
    """Email event data."""

    message_id_external: str = Field(description="External email message ID")
    thread_id: Optional[str] = Field(default=None, description="Email thread ID")
    from_address: str = Field(description="Sender email address")
    to_addresses: List[str] = Field(description="Recipient email addresses")
    cc_addresses: List[str] = Field(
        default_factory=list, description="CC email addresses"
    )
    subject: str = Field(description="Email subject")
    body_text: Optional[str] = Field(
        default=None, description="Email body (plain text)"
    )
    body_html: Optional[str] = Field(default=None, description="Email body (HTML)")
    attachments: List[dict] = Field(
        default_factory=list, description="Email attachments"
    )
    labels: List[str] = Field(default_factory=list, description="Email labels/folders")
    is_read: bool = Field(default=False, description="Whether email is read")
    is_starred: bool = Field(default=False, description="Whether email is starred")
    importance: Optional[str] = Field(
        default=None, description="Email importance level"
    )
    received_date: datetime = Field(description="Email received timestamp")


class CalendarEvent(BaseMessage):
    """Calendar event data."""

    event_id: str = Field(description="External calendar event ID")
    calendar_id: str = Field(description="Calendar ID")
    title: str = Field(description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    location: Optional[str] = Field(default=None, description="Event location")
    start_time: datetime = Field(description="Event start time")
    end_time: datetime = Field(description="Event end time")
    all_day: bool = Field(default=False, description="Whether event is all-day")
    recurring_rule: Optional[str] = Field(default=None, description="Recurrence rule")
    attendees: List[dict] = Field(default_factory=list, description="Event attendees")
    organizer_email: Optional[str] = Field(default=None, description="Organizer email")
    status: str = Field(description="Event status")
    visibility: Optional[str] = Field(default=None, description="Event visibility")
    reminders: List[dict] = Field(default_factory=list, description="Event reminders")


class TwitterLike(BaseMessage):
    """Twitter/X liked tweet data."""

    tweet_id: str = Field(description="Tweet ID")
    tweet_url: str = Field(description="Tweet URL")
    author_username: str = Field(description="Tweet author username")
    author_display_name: str = Field(description="Tweet author display name")
    tweet_text: str = Field(description="Tweet content")
    created_at: datetime = Field(description="Tweet creation timestamp")
    liked_at: datetime = Field(description="When tweet was liked")
    retweet_count: int = Field(default=0, description="Retweet count")
    like_count: int = Field(default=0, description="Like count")
    reply_count: int = Field(default=0, description="Reply count")
    media_urls: List[str] = Field(
        default_factory=list, description="Media URLs in tweet"
    )
    hashtags: List[str] = Field(default_factory=list, description="Hashtags in tweet")
    mentions: List[str] = Field(
        default_factory=list, description="User mentions in tweet"
    )


class HackerNewsItem(BaseMessage):
    """Hacker News item (story/comment) data."""

    item_id: int = Field(description="HN item ID")
    item_type: str = Field(description="Item type (story, comment, job, poll)")
    title: Optional[str] = Field(default=None, description="Item title")
    url: Optional[str] = Field(default=None, description="Item URL")
    text: Optional[str] = Field(default=None, description="Item text content")
    author: str = Field(description="Item author username")
    score: int = Field(default=0, description="Item score/points")
    comments_count: int = Field(default=0, description="Number of comments")
    created_at: datetime = Field(description="Item creation timestamp")
    interacted_at: datetime = Field(description="When user interacted with item")
    interaction_type: str = Field(
        description="Type of interaction (upvote, comment, save)"
    )


class WebVisit(BaseMessage):
    """Web visit/browsing data."""

    url: str = Field(description="Visited URL")
    title: Optional[str] = Field(default=None, description="Page title")
    visit_time: datetime = Field(description="Visit timestamp")
    visit_duration: Optional[int] = Field(
        default=None, description="Time spent on page (seconds)"
    )
    referrer: Optional[str] = Field(default=None, description="Referrer URL")
    browser: str = Field(description="Browser used")
    tab_count: Optional[int] = Field(default=None, description="Number of open tabs")
    is_incognito: bool = Field(
        default=False, description="Whether visit was in incognito mode"
    )


class RSSFeedItem(BaseMessage):
    """RSS feed item data."""

    feed_url: str = Field(description="RSS feed URL")
    feed_title: str = Field(description="RSS feed title")
    item_id: str = Field(description="Feed item ID/GUID")
    item_title: str = Field(description="Item title")
    item_url: str = Field(description="Item URL")
    item_content: Optional[str] = Field(
        default=None, description="Item content/summary"
    )
    author: Optional[str] = Field(default=None, description="Item author")
    published_at: datetime = Field(description="Item publication timestamp")
    categories: List[str] = Field(
        default_factory=list, description="Item categories/tags"
    )


class ScheduledJobStatus(BaseMessage):
    """Status of a scheduled job."""

    job_id: str = Field(description="Unique job identifier")
    job_type: str = Field(description="Type of scheduled job")
    last_run: Optional[datetime] = Field(
        default=None, description="Last execution time"
    )
    next_run: Optional[datetime] = Field(
        default=None, description="Next scheduled execution"
    )
    status: str = Field(description="Job status (running, completed, failed)")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    items_processed: int = Field(default=0, description="Number of items processed")
    execution_duration: Optional[float] = Field(
        default=None, description="Execution duration in seconds"
    )
