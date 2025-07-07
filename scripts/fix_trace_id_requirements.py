#!/usr/bin/env python3
"""
Remove trace_id from required_fields in topic_mappings.yml
This allows the generic kafka-to-db consumer to process messages without trace_id
"""

import yaml
import sys
from pathlib import Path

def fix_trace_id_requirements():
    """Remove trace_id from required_fields in all topic configurations."""
    
    config_path = Path("/home/aoi/code/loomv2/services/kafka-to-db-consumer/config/topic_mappings.yml")
    
    if not config_path.exists():
        print(f"Error: Configuration file not found at {config_path}")
        return False
    
    # Load the YAML configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Track changes
    changes_made = 0
    
    # Process each topic
    for topic_name, topic_config in config.get('topics', {}).items():
        if 'required_fields' in topic_config and 'trace_id' in topic_config['required_fields']:
            print(f"Removing trace_id requirement from topic: {topic_name}")
            topic_config['required_fields'].remove('trace_id')
            changes_made += 1
    
    # Save the updated configuration
    if changes_made > 0:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"\nUpdated {changes_made} topic configurations")
        print("Configuration saved successfully!")
    else:
        print("No changes needed - trace_id is not required in any topics")
    
    return True

if __name__ == "__main__":
    success = fix_trace_id_requirements()
    sys.exit(0 if success else 1)