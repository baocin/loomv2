-- Update the validation function to be more flexible
CREATE OR REPLACE FUNCTION validate_topic_name(p_topic_name TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check basic pattern (alphanumeric, dots, underscores)
    IF p_topic_name !~ '^[a-z0-9._]+$' THEN
        RETURN FALSE;
    END IF;
    
    -- Must have at least 2 parts (category.type)
    IF array_length(string_to_array(p_topic_name, '.'), 1) < 2 THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;