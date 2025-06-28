-- Migration: Add OCR data column to twitter_extraction_results
-- Purpose: Store OCR results from Moondream processing of Twitter screenshots

-- Add ocred_data column to store OCR results
ALTER TABLE twitter_extraction_results
ADD COLUMN IF NOT EXISTS ocred_data JSONB;

-- Add index for efficient querying of OCR data
CREATE INDEX IF NOT EXISTS idx_twitter_extraction_ocred_data
ON twitter_extraction_results USING gin(ocred_data);

-- Add comment to document the column
COMMENT ON COLUMN twitter_extraction_results.ocred_data IS
'OCR results from Moondream processing: {full_text: string, description: string, processing_time_ms: number, model_version: string}';
