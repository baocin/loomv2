-- Create scheduler topics for triggering fetchers
-- These topics will be used to trigger periodic fetches

-- Create the scheduler trigger topics
INSERT INTO kafka_topics (topic_name, partitions, retention_days, description, schema_version, created_at)
VALUES
    ('scheduler.triggers.calendar_fetch', 1, 1, 'Trigger topic for calendar fetcher - send empty message to trigger fetch', '1.0', NOW()),
    ('scheduler.triggers.email_fetch', 1, 1, 'Trigger topic for email fetcher - send empty message to trigger fetch', '1.0', NOW()),
    ('scheduler.triggers.hn_scrape', 1, 1, 'Trigger topic for HackerNews scraper - send empty message to trigger fetch', '1.0', NOW())
ON CONFLICT (topic_name) DO NOTHING;

-- Connect the scheduler topics to the fetchers
-- First, find the stage IDs for the fetchers
DO $$
DECLARE
    v_calendar_fetcher_id INTEGER;
    v_email_fetcher_id INTEGER;
    v_hn_scraper_id INTEGER;
BEGIN
    -- Get fetcher stage IDs
    SELECT id INTO v_calendar_fetcher_id FROM pipeline_stages WHERE service_name = 'calendar-fetcher';
    SELECT id INTO v_email_fetcher_id FROM pipeline_stages WHERE service_name = 'email-fetcher';
    SELECT id INTO v_hn_scraper_id FROM pipeline_stages WHERE service_name = 'hn-scraper';

    -- Add scheduler topics as inputs to fetchers
    IF v_calendar_fetcher_id IS NOT NULL THEN
        INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
        VALUES (v_calendar_fetcher_id, 'scheduler.triggers.calendar_fetch', 'input')
        ON CONFLICT (stage_id, topic_name, topic_role) DO NOTHING;
        RAISE NOTICE 'Connected calendar fetcher to scheduler trigger';
    END IF;

    IF v_email_fetcher_id IS NOT NULL THEN
        INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
        VALUES (v_email_fetcher_id, 'scheduler.triggers.email_fetch', 'input')
        ON CONFLICT (stage_id, topic_name, topic_role) DO NOTHING;
        RAISE NOTICE 'Connected email fetcher to scheduler trigger';
    END IF;

    IF v_hn_scraper_id IS NOT NULL THEN
        INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
        VALUES (v_hn_scraper_id, 'scheduler.triggers.hn_scrape', 'input')
        ON CONFLICT (stage_id, topic_name, topic_role) DO NOTHING;
        RAISE NOTICE 'Connected HackerNews scraper to scheduler trigger';
    END IF;
END $$;

-- Verify the connections
SELECT
    ps.service_name,
    pst.topic_name,
    pst.topic_role
FROM pipeline_stages ps
JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id
WHERE ps.service_name IN ('calendar-fetcher', 'email-fetcher', 'hn-scraper')
  AND pst.topic_role = 'input'
ORDER BY ps.service_name;
