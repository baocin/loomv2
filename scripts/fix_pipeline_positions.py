#!/usr/bin/env python3
"""
Fix pipeline node positions to have proper layout with consistent spacing.
"""

import json
import sys

def fix_positions(positions_file):
    """Fix node positions to have proper layout."""
    
    # Load the positions file
    with open(positions_file, 'r') as f:
        data = json.load(f)
    
    positions = data['positions']
    
    # Define column X positions
    columns = {
        'api': 50,
        'fetcher': 400,
        'raw_topic': 750,
        'processor': 1350,
        'processed_topic': 1950,
        'kafka_to_db': 2550,
        'table': 3150,
        'error': 1950
    }
    
    # Categorize nodes by type
    node_categories = {
        'headers': [],
        'api': [],
        'fetchers': [],
        'raw_topics': [],
        'processors': [],
        'processed_topics': [],
        'kafka_to_db': [],
        'tables': [],
        'error_topics': []
    }
    
    for node_id in positions:
        if 'header_' in node_id:
            node_categories['headers'].append(node_id)
        elif node_id == 'api_ingestion':
            node_categories['api'].append(node_id)
        elif 'fetcher_' in node_id:
            node_categories['fetchers'].append(node_id)
        elif 'table_' in node_id:
            node_categories['tables'].append(node_id)
        elif 'processor_' in node_id:
            if any(x in node_id for x in ['kafka-to-db', 'kafka_to_db', 'timescale-writer', 'kafka-to-db-saver']):
                node_categories['kafka_to_db'].append(node_id)
            else:
                node_categories['processors'].append(node_id)
        elif 'topic_' in node_id:
            if 'error' in node_id:
                node_categories['error_topics'].append(node_id)
            elif '.raw' in node_id or '_raw' in node_id:
                node_categories['raw_topics'].append(node_id)
            else:
                node_categories['processed_topics'].append(node_id)
    
    # Fix positions
    new_positions = {}
    
    # Headers stay at y=0
    for node_id in node_categories['headers']:
        new_positions[node_id] = positions[node_id]  # Keep original header positions
    
    # Layout other nodes with consistent spacing
    y_spacing = 60  # Vertical spacing between nodes
    start_y = 80
    
    # API nodes
    current_y = start_y
    for node_id in sorted(node_categories['api']):
        new_positions[node_id] = {'x': columns['api'], 'y': current_y}
        current_y += 150 + y_spacing
    
    # Fetcher nodes
    current_y = start_y
    for node_id in sorted(node_categories['fetchers']):
        new_positions[node_id] = {'x': columns['fetcher'], 'y': current_y}
        current_y += 150 + y_spacing
    
    # Raw topics
    current_y = start_y
    for node_id in sorted(node_categories['raw_topics']):
        new_positions[node_id] = {'x': columns['raw_topic'], 'y': current_y}
        current_y += 150 + y_spacing
    
    # Processors
    current_y = start_y
    for node_id in sorted(node_categories['processors']):
        new_positions[node_id] = {'x': columns['processor'], 'y': current_y}
        current_y += 250 + y_spacing  # Processors are taller
    
    # Processed topics
    current_y = start_y
    for node_id in sorted(node_categories['processed_topics']):
        new_positions[node_id] = {'x': columns['processed_topic'], 'y': current_y}
        current_y += 150 + y_spacing
    
    # Kafka-to-DB processors
    current_y = start_y
    for node_id in sorted(node_categories['kafka_to_db']):
        new_positions[node_id] = {'x': columns['kafka_to_db'], 'y': current_y}
        current_y += 250 + y_spacing  # Processors are taller
    
    # Tables
    current_y = start_y
    for node_id in sorted(node_categories['tables']):
        new_positions[node_id] = {'x': columns['table'], 'y': current_y}
        current_y += 100 + y_spacing  # Tables are shorter
    
    # Error topics at the bottom
    if node_categories['error_topics']:
        # Find max Y from all other nodes
        non_header_positions = [pos['y'] for node_id, pos in new_positions.items() if 'header_' not in node_id]
        if non_header_positions:
            max_y = max(non_header_positions)
            current_y = max_y + 200
        else:
            current_y = start_y
        
        for node_id in sorted(node_categories['error_topics']):
            new_positions[node_id] = {'x': columns['error'], 'y': current_y}
            current_y += 150 + y_spacing
    
    # Create output data
    output_data = {
        'metadata': {
            'exportDate': data['metadata']['exportDate'],
            'version': '1.0',
            'nodeCount': len(new_positions)
        },
        'positions': new_positions
    }
    
    # Save fixed positions
    output_file = positions_file.replace('.json', '-fixed.json')
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Fixed positions saved to: {output_file}")
    print(f"Total nodes repositioned: {len(new_positions)}")
    
    # Show statistics
    print("\nNode counts by category:")
    for category, nodes in node_categories.items():
        if nodes:
            print(f"  {category}: {len(nodes)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_pipeline_positions.py <positions_file.json>")
        sys.exit(1)
    
    fix_positions(sys.argv[1])