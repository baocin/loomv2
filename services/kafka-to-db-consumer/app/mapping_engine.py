"""Mapping engine for converting Kafka messages to database records using YAML configuration."""

import base64
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

import yaml
from dateutil import parser as date_parser
import structlog

logger = structlog.get_logger(__name__)


class MappingEngine:
    """Engine for mapping Kafka topic messages to database tables using YAML configuration."""

    def __init__(self, config_path: str = None):
        """Initialize the mapping engine with configuration."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "topic_mappings.yml"
        
        self.config_path = Path(config_path)
        self.config = None
        self.load_config()

    def load_config(self) -> None:
        """Load mapping configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("Loaded topic mapping configuration", 
                       topics=len(self.config.get('topics', {})),
                       config_path=str(self.config_path))
        except Exception as e:
            logger.error("Failed to load mapping configuration", 
                        error=str(e), 
                        config_path=str(self.config_path))
            raise

    def reload_config(self) -> None:
        """Reload configuration from file (for hot-reloading)."""
        logger.info("Reloading topic mapping configuration")
        self.load_config()

    def get_topic_mapping(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get mapping configuration for a specific topic."""
        if not self.config:
            return None
        
        return self.config.get('topics', {}).get(topic)

    def get_supported_topics(self) -> List[str]:
        """Get list of all supported topics."""
        if not self.config:
            return []
        
        return list(self.config.get('topics', {}).keys())

    def map_message_to_record(self, topic: str, message: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any], str]]:
        """
        Map a Kafka message to a database record.
        
        Returns:
            Tuple of (table_name, record_data, upsert_key) or None if topic not supported
        """
        topic_config = self.get_topic_mapping(topic)
        if not topic_config:
            logger.warning("No mapping configuration found for topic", topic=topic)
            return None

        try:
            table_name = topic_config['table']
            field_mappings = topic_config.get('field_mappings', {})
            data_types = topic_config.get('data_types', {})
            transforms = topic_config.get('transforms', {})
            defaults = self.config.get('defaults', {})
            
            # Get upsert key (with fallback to default)
            upsert_key = topic_config.get('upsert_key', defaults.get('upsert_key', 'trace_id'))
            
            # Start building the record
            record = {}
            
            # Map each field according to configuration
            for source_field, target_column in field_mappings.items():
                value = self._extract_field_value(message, source_field)
                
                if value is not None:
                    # Apply data type conversion
                    if target_column in data_types:
                        value = self._convert_data_type(value, data_types[target_column])
                    
                    # Apply transformations
                    if target_column in transforms:
                        value = self._apply_transformation(value, transforms[target_column])
                    
                    record[target_column] = value

            # Handle special array mappings (like word timestamps)
            array_mappings = topic_config.get('array_mappings', {})
            if array_mappings:
                array_records = self._process_array_mappings(message, array_mappings, record, topic_config)
                if array_records:
                    # For array mappings, return multiple records
                    return table_name, array_records, upsert_key

            # Validate required fields
            required_fields = topic_config.get('required_fields', [])
            missing_fields = []
            for field in required_fields:
                target_column = field_mappings.get(field, field)
                if target_column not in record or record[target_column] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning("Missing required fields in message", 
                              topic=topic, 
                              missing_fields=missing_fields,
                              trace_id=record.get('trace_id'))
                return None

            # Ensure created_at timestamp
            if 'created_at' not in record:
                record['created_at'] = datetime.now(timezone.utc)

            logger.debug("Successfully mapped message to record", 
                        topic=topic, 
                        table=table_name,
                        trace_id=record.get('trace_id'),
                        fields=list(record.keys()))

            return table_name, record, upsert_key

        except Exception as e:
            logger.error("Failed to map message to record", 
                        topic=topic, 
                        error=str(e),
                        message_keys=list(message.keys()) if isinstance(message, dict) else None,
                        exc_info=True)
            return None

    def _extract_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Extract a value from nested dictionary using dot notation."""
        try:
            keys = field_path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
                
                if value is None:
                    return None
            
            return value
        except Exception:
            return None

    def _convert_data_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target data type."""
        if value is None:
            return None

        try:
            if target_type == 'integer':
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str):
                    return int(float(value))
            
            elif target_type == 'float':
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    return float(value)
            
            elif target_type == 'boolean':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            
            elif target_type == 'timestamp':
                if isinstance(value, str):
                    # Parse ISO format timestamp
                    dt = date_parser.isoparse(value)
                    # Ensure timezone awareness
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                elif isinstance(value, (int, float)):
                    # Unix timestamp
                    return datetime.fromtimestamp(value, tz=timezone.utc)
                elif isinstance(value, datetime):
                    return value
            
            elif target_type == 'array':
                if isinstance(value, list):
                    return value
                elif isinstance(value, str):
                    # Try to parse as JSON array
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            return parsed
                    except:
                        pass
                    # Fall back to single-item array
                    return [value]
            
            elif target_type == 'float_array':
                if isinstance(value, list):
                    return [float(x) for x in value if x is not None]
                elif isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            return [float(x) for x in parsed if x is not None]
                    except:
                        pass
            
            elif target_type == 'string':
                return str(value)
            
            # Default: return as-is
            return value
            
        except Exception as e:
            logger.warning("Failed to convert data type", 
                          value=value, 
                          target_type=target_type, 
                          error=str(e))
            return value

    def _apply_transformation(self, value: Any, transform_name: str) -> Any:
        """Apply a transformation to a value."""
        if value is None:
            return None

        try:
            if transform_name == 'base64_decode':
                if isinstance(value, str):
                    return base64.b64decode(value)
            
            elif transform_name == 'timestamp_parse':
                if isinstance(value, str):
                    dt = date_parser.isoparse(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            
            elif transform_name == 'json_stringify':
                return json.dumps(value)
            
            # Default: return as-is
            return value
            
        except Exception as e:
            logger.warning("Failed to apply transformation", 
                          value=str(value)[:100], 
                          transform=transform_name, 
                          error=str(e))
            return value

    def _process_array_mappings(self, message: Dict[str, Any], array_mappings: Dict[str, Any], 
                               base_record: Dict[str, Any], topic_config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Process array mappings that create multiple records from a single message."""
        try:
            records = []
            
            for source_array_path, mapping_config in array_mappings.items():
                array_data = self._extract_field_value(message, source_array_path)
                if not isinstance(array_data, list):
                    continue
                
                element_mappings = mapping_config.get('element_mappings', {})
                sequence_field = mapping_config.get('sequence_field', 'sequence')
                
                for i, element in enumerate(array_data):
                    record = base_record.copy()
                    
                    # Add sequence number
                    record[sequence_field] = i
                    
                    # Map element fields
                    for element_key, target_column in element_mappings.items():
                        if isinstance(element, dict):
                            value = element.get(element_key)
                        else:
                            # Handle simple values
                            if element_key == 'value':
                                value = element
                            else:
                                continue
                        
                        if value is not None:
                            # Apply data type conversion
                            data_types = topic_config.get('data_types', {})
                            if target_column in data_types:
                                value = self._convert_data_type(value, data_types[target_column])
                            
                            record[target_column] = value
                    
                    records.append(record)
            
            return records if records else None
            
        except Exception as e:
            logger.error("Failed to process array mappings", 
                        error=str(e), 
                        array_mappings=array_mappings)
            return None

    def validate_config(self) -> List[str]:
        """Validate the mapping configuration and return any errors."""
        errors = []
        
        if not self.config:
            errors.append("No configuration loaded")
            return errors
        
        # Check schema version
        if self.config.get('schema_version') != 'v1':
            errors.append("Unsupported schema version")
        
        # Validate topics
        topics = self.config.get('topics', {})
        for topic_name, topic_config in topics.items():
            if not isinstance(topic_config, dict):
                errors.append(f"Topic {topic_name}: configuration must be a dictionary")
                continue
            
            # Required fields
            if 'table' not in topic_config:
                errors.append(f"Topic {topic_name}: missing required 'table' field")
            
            if 'field_mappings' not in topic_config:
                errors.append(f"Topic {topic_name}: missing required 'field_mappings' field")
            
            # Validate field mappings
            field_mappings = topic_config.get('field_mappings', {})
            if not isinstance(field_mappings, dict):
                errors.append(f"Topic {topic_name}: 'field_mappings' must be a dictionary")
            
            # Validate data types
            data_types = topic_config.get('data_types', {})
            valid_types = {'string', 'integer', 'float', 'boolean', 'timestamp', 'array', 'float_array', 'json'}
            for field, data_type in data_types.items():
                if data_type not in valid_types:
                    errors.append(f"Topic {topic_name}: invalid data type '{data_type}' for field '{field}'")
        
        return errors