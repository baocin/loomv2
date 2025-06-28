"""Smoke tests for email-fetcher service."""

import pytest
from unittest.mock import patch, MagicMock, call
import time
import os
from datetime import datetime, timezone

from app.main import fetch_emails, main


class TestEmailFetcherSmoke:
    """Smoke tests to ensure the email fetcher service works."""

    def test_fetch_emails_success(self, mock_email_fetcher, mock_kafka_producer):
        """Test successful email fetching and Kafka sending."""
        # Run fetch_emails
        fetch_emails()
        
        # Verify EmailFetcher was initialized and called
        mock_email_fetcher.fetch_all_emails.assert_called_once()
        
        # Verify KafkaProducer was initialized
        mock_kafka_producer.send_message.assert_called()
        mock_kafka_producer.close.assert_called_once()
        
        # Verify correct number of messages sent
        assert mock_kafka_producer.send_message.call_count == 2
        
        # Verify message structure
        first_call = mock_kafka_producer.send_message.call_args_list[0]
        assert first_call[1]['topic'] == "external.email.events.raw"
        assert first_call[1]['key'] == "test-email-1"
        
        message = first_call[1]['value']
        assert message['schema_version'] == "v1"
        assert message['device_id'] is None
        assert 'timestamp' in message
        assert 'data' in message

    def test_fetch_emails_empty_inbox(self, mock_email_fetcher, mock_kafka_producer):
        """Test handling of empty inbox."""
        # Mock empty email list
        mock_email_fetcher.fetch_all_emails.return_value = []
        
        # Run fetch_emails
        fetch_emails()
        
        # Verify EmailFetcher was called
        mock_email_fetcher.fetch_all_emails.assert_called_once()
        
        # Verify no messages were sent to Kafka
        mock_kafka_producer.send_message.assert_not_called()
        
        # Verify producer was still closed
        mock_kafka_producer.close.assert_called_once()

    def test_fetch_emails_error_handling(self, mock_email_fetcher, mock_kafka_producer):
        """Test error handling during email fetch."""
        # Make fetch_all_emails raise an exception
        mock_email_fetcher.fetch_all_emails.side_effect = Exception("IMAP connection failed")
        
        # Run fetch_emails - should not raise exception
        fetch_emails()
        
        # Verify error was handled gracefully
        mock_email_fetcher.fetch_all_emails.assert_called_once()
        mock_kafka_producer.send_message.assert_not_called()

    def test_fetch_emails_kafka_error_handling(self, mock_email_fetcher, mock_kafka_producer):
        """Test error handling during Kafka send."""
        # Make send_message raise an exception on first call
        mock_kafka_producer.send_message.side_effect = [
            Exception("Kafka connection failed"),
            None  # Second call succeeds
        ]
        
        # Run fetch_emails - should handle error and continue
        fetch_emails()
        
        # Verify both emails were attempted
        assert mock_kafka_producer.send_message.call_count == 2
        mock_kafka_producer.close.assert_called_once()

    def test_main_startup_with_immediate_run(self, mock_email_fetcher, mock_kafka_producer, mock_schedule):
        """Test main function with immediate run on startup."""
        # Mock time.sleep to prevent infinite loop
        with patch('time.sleep') as mock_sleep:
            # Make run_pending raise KeyboardInterrupt after first iteration
            mock_schedule.run_pending.side_effect = KeyboardInterrupt()
            
            # Run main
            with pytest.raises(KeyboardInterrupt):
                main()
            
            # Verify schedule was set up
            mock_schedule.every.assert_called_with(5)
            mock_schedule.every().minutes.do.assert_called_once()
            
            # Verify fetch_emails was called immediately (run_on_startup=true)
            mock_email_fetcher.fetch_all_emails.assert_called()

    def test_main_startup_without_immediate_run(self, mock_email_fetcher, mock_kafka_producer, mock_schedule):
        """Test main function without immediate run on startup."""
        # Set environment to not run on startup
        os.environ["LOOM_EMAIL_RUN_ON_STARTUP"] = "false"
        
        # Mock time.sleep to prevent infinite loop
        with patch('time.sleep') as mock_sleep:
            # Make run_pending raise KeyboardInterrupt after first iteration
            mock_schedule.run_pending.side_effect = KeyboardInterrupt()
            
            # Run main
            with pytest.raises(KeyboardInterrupt):
                main()
            
            # Verify schedule was set up
            mock_schedule.every.assert_called_with(5)
            
            # Verify fetch_emails was NOT called immediately
            mock_email_fetcher.fetch_all_emails.assert_not_called()

    def test_custom_fetch_interval(self, mock_email_fetcher, mock_kafka_producer, mock_schedule):
        """Test custom fetch interval from environment."""
        # Set custom interval
        os.environ["LOOM_EMAIL_FETCH_INTERVAL_MINUTES"] = "10"
        
        with patch('time.sleep') as mock_sleep:
            mock_schedule.run_pending.side_effect = KeyboardInterrupt()
            
            with pytest.raises(KeyboardInterrupt):
                main()
            
            # Verify schedule was set up with custom interval
            mock_schedule.every.assert_called_with(10)

    def test_custom_output_topic(self, mock_email_fetcher, mock_kafka_producer):
        """Test custom Kafka output topic."""
        # Set custom topic
        os.environ["LOOM_KAFKA_OUTPUT_TOPIC"] = "custom.email.topic"
        
        # Run fetch_emails
        fetch_emails()
        
        # Verify messages were sent to custom topic
        first_call = mock_kafka_producer.send_message.call_args_list[0]
        assert first_call[1]['topic'] == "custom.email.topic"

    def test_message_structure_compliance(self, mock_email_fetcher, mock_kafka_producer, sample_email_data):
        """Test that messages comply with expected schema."""
        # Set up mock to return our sample data
        mock_email_fetcher.fetch_all_emails.return_value = [sample_email_data]
        
        # Run fetch_emails
        fetch_emails()
        
        # Get the sent message
        call_args = mock_kafka_producer.send_message.call_args
        message = call_args[1]['value']
        
        # Verify message structure
        assert message['schema_version'] == "v1"
        assert message['device_id'] is None
        assert isinstance(message['timestamp'], str)
        assert message['timestamp'] == sample_email_data['date_received'].isoformat()
        
        # Verify data matches input
        assert message['data'] == sample_email_data
        assert message['data']['email_id'] == "sample-email-123"
        assert message['data']['has_attachments'] is True

    def test_multiple_accounts_handling(self, mock_email_fetcher, mock_kafka_producer):
        """Test handling emails from multiple accounts."""
        # Mock emails from different accounts
        mock_email_fetcher.fetch_all_emails.return_value = [
            {
                "email_id": "work-email-1",
                "subject": "Work Email",
                "sender": "boss@work.com",
                "recipients": ["me@work.com"],
                "body_preview": "Work stuff...",
                "has_attachments": False,
                "date_received": datetime.now(timezone.utc),
                "folder": "INBOX",
                "account_name": "work-account"
            },
            {
                "email_id": "personal-email-1",
                "subject": "Personal Email",
                "sender": "friend@gmail.com",
                "recipients": ["me@gmail.com"],
                "body_preview": "Hey there...",
                "has_attachments": False,
                "date_received": datetime.now(timezone.utc),
                "folder": "INBOX",
                "account_name": "personal-account"
            }
        ]
        
        # Run fetch_emails
        fetch_emails()
        
        # Verify both emails were sent
        assert mock_kafka_producer.send_message.call_count == 2
        
        # Verify different accounts
        calls = mock_kafka_producer.send_message.call_args_list
        assert calls[0][1]['value']['data']['account_name'] == "work-account"
        assert calls[1][1]['value']['data']['account_name'] == "personal-account"