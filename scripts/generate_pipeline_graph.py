#!/usr/bin/env python3
"""
Generate pipeline visualization graphs from flow definitions.
This script creates visual representations of the Loom v2 data processing pipelines.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse


def load_flow_definitions(flows_dir: Path) -> Dict:
    """Load all flow definition YAML files."""
    flows = {}
    for yaml_file in flows_dir.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue
        with open(yaml_file) as f:
            flows[yaml_file.stem] = yaml.safe_load(f)
    return flows


def generate_mermaid_graph(flows: Dict) -> str:
    """Generate a Mermaid diagram from flow definitions."""
    lines = ["graph TB", ""]
    
    # Style definitions
    lines.extend([
        "    %% Style definitions",
        "    classDef critical fill:#FF5252,stroke:#333,stroke-width:3px,color:#fff",
        "    classDef high fill:#FF9800,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef medium fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef low fill:#2196F3,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef model fill:#9C27B0,stroke:#333,stroke-width:2px,color:#fff",
        "    classDef storage fill:#795548,stroke:#333,stroke-width:2px,color:#fff",
        ""
    ])
    
    # Track all topics and connections
    topics_to_flows = {}
    flow_nodes = {}
    
    # First pass: collect all topics and create flow nodes
    for flow_name, flow_data in flows.items():
        if not flow_data or 'stages' not in flow_data:
            continue
            
        priority = flow_data.get('priority', 'medium')
        flow_id = flow_name.replace('_', '')
        flow_nodes[flow_id] = {
            'name': flow_data.get('name', flow_name),
            'priority': priority,
            'stages': len(flow_data['stages'])
        }
        
        # Collect input and output topics
        for stage in flow_data['stages']:
            for topic in stage.get('input_topics', []):
                if topic not in topics_to_flows:
                    topics_to_flows[topic] = {'inputs': [], 'outputs': []}
                topics_to_flows[topic]['outputs'].append(flow_id)
                
            for topic in stage.get('output_topics', []):
                if topic not in topics_to_flows:
                    topics_to_flows[topic] = {'inputs': [], 'outputs': []}
                topics_to_flows[topic]['inputs'].append(flow_id)
    
    # Add flow nodes
    lines.append("    %% Flow nodes")
    for flow_id, flow_info in flow_nodes.items():
        label = f"{flow_info['name']}\\n({flow_info['stages']} stages)"
        lines.append(f"    {flow_id}[\"{label}\"]")
        lines.append(f"    class {flow_id} {flow_info['priority']}")
    lines.append("")
    
    # Add key topic nodes (only show important ones to reduce clutter)
    important_topics = {
        'device.audio.raw': 'Audio Input',
        'device.image.camera.raw': 'Camera Input',
        'device.sensor.gps.raw': 'GPS Input',
        'device.sensor.accelerometer.raw': 'Accelerometer',
        'media.text.transcribed.words': 'Transcripts',
        'media.image.objects_detected': 'Objects',
        'location.business.identified': 'Businesses'
    }
    
    lines.append("    %% Important topic nodes")
    for topic, label in important_topics.items():
        if topic in topics_to_flows:
            topic_id = topic.replace('.', '_')
            lines.append(f"    {topic_id}((\"{label}\"))")
    lines.append("")
    
    # Add TimescaleDB node
    lines.append("    %% Storage")
    lines.append("    DB[(TimescaleDB)]")
    lines.append("    class DB storage")
    lines.append("")
    
    # Add connections
    lines.append("    %% Connections")
    connected_flows = set()
    
    # Connect inputs to flows
    for topic, connections in topics_to_flows.items():
        topic_id = topic.replace('.', '_')
        if topic in important_topics:
            for flow_id in connections['outputs']:
                if flow_id in flow_nodes:
                    lines.append(f"    {topic_id} --> {flow_id}")
                    connected_flows.add(flow_id)
    
    # Connect all flows to DB
    for flow_id in flow_nodes:
        lines.append(f"    {flow_id} --> DB")
    
    return "\\n".join(lines)


def generate_graphviz_dot(flows: Dict) -> str:
    """Generate a Graphviz DOT file from flow definitions."""
    lines = [
        "digraph LoomPipelines {",
        "    rankdir=LR;",
        "    node [shape=box, style=rounded];",
        "    edge [fontsize=10];",
        ""
    ]
    
    # Color schemes by priority
    colors = {
        'critical': '#FF5252',
        'high': '#FF9800',
        'medium': '#4CAF50',
        'low': '#2196F3'
    }
    
    # Add flow nodes
    for flow_name, flow_data in flows.items():
        if not flow_data or 'stages' not in flow_data:
            continue
            
        priority = flow_data.get('priority', 'medium')
        color = colors.get(priority, '#999999')
        stages = len(flow_data['stages'])
        
        label = f"{flow_data.get('name', flow_name)}\\n{stages} stages"
        lines.append(f'    "{flow_name}" [label="{label}", fillcolor="{color}", style=filled, fontcolor=white];')
    
    lines.append("")
    
    # Add topic connections (simplified)
    lines.append("    // Topic connections")
    for flow_name, flow_data in flows.items():
        if not flow_data or 'stages' not in flow_data:
            continue
            
        # Just show flow-to-flow connections based on shared topics
        output_topics = set()
        for stage in flow_data['stages']:
            output_topics.update(stage.get('output_topics', []))
        
        # Find flows that consume these topics
        for other_flow, other_data in flows.items():
            if other_flow == flow_name or not other_data or 'stages' not in other_data:
                continue
                
            for stage in other_data['stages']:
                input_topics = set(stage.get('input_topics', []))
                if output_topics & input_topics:
                    lines.append(f'    "{flow_name}" -> "{other_flow}";')
                    break
    
    lines.append("}")
    return "\\n".join(lines)


def generate_json_graph(flows: Dict) -> Dict:
    """Generate a JSON graph structure for D3.js or similar visualization."""
    nodes = []
    links = []
    node_index = {}
    
    # Create nodes for flows
    for i, (flow_name, flow_data) in enumerate(flows.items()):
        if not flow_data or 'stages' not in flow_data:
            continue
            
        node = {
            "id": flow_name,
            "name": flow_data.get('name', flow_name),
            "priority": flow_data.get('priority', 'medium'),
            "stages": len(flow_data['stages']),
            "group": flow_data.get('priority', 'medium'),
            "data_volume": flow_data.get('data_volume', {})
        }
        nodes.append(node)
        node_index[flow_name] = i
    
    # Create links based on topic connections
    topic_producers = {}
    topic_consumers = {}
    
    for flow_name, flow_data in flows.items():
        if not flow_data or 'stages' not in flow_data:
            continue
            
        for stage in flow_data['stages']:
            for topic in stage.get('output_topics', []):
                if topic not in topic_producers:
                    topic_producers[topic] = []
                topic_producers[topic].append(flow_name)
                
            for topic in stage.get('input_topics', []):
                if topic not in topic_consumers:
                    topic_consumers[topic] = []
                topic_consumers[topic].append(flow_name)
    
    # Create links
    for topic, producers in topic_producers.items():
        consumers = topic_consumers.get(topic, [])
        for producer in producers:
            for consumer in consumers:
                if producer in node_index and consumer in node_index:
                    links.append({
                        "source": producer,
                        "target": consumer,
                        "topic": topic,
                        "value": 1
                    })
    
    return {
        "nodes": nodes,
        "links": links,
        "metadata": {
            "total_flows": len(nodes),
            "total_connections": len(links),
            "priorities": {
                priority: sum(1 for n in nodes if n['priority'] == priority)
                for priority in ['critical', 'high', 'medium', 'low']
            }
        }
    }


def main():
    parser = argparse.ArgumentParser(description='Generate pipeline visualization graphs')
    parser.add_argument('--format', choices=['mermaid', 'dot', 'json', 'all'], 
                       default='all', help='Output format')
    parser.add_argument('--output-dir', type=Path, default=Path('docs/flows/visualizations'),
                       help='Output directory for generated files')
    args = parser.parse_args()
    
    # Load flow definitions
    flows_dir = Path('docs/flows')
    flows = load_flow_definitions(flows_dir)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate visualizations
    if args.format in ['mermaid', 'all']:
        mermaid_graph = generate_mermaid_graph(flows)
        output_file = args.output_dir / 'pipeline-graph.mmd'
        output_file.write_text(mermaid_graph)
        print(f"Generated Mermaid graph: {output_file}")
    
    if args.format in ['dot', 'all']:
        dot_graph = generate_graphviz_dot(flows)
        output_file = args.output_dir / 'pipeline-graph.dot'
        output_file.write_text(dot_graph)
        print(f"Generated Graphviz DOT: {output_file}")
    
    if args.format in ['json', 'all']:
        json_graph = generate_json_graph(flows)
        output_file = args.output_dir / 'pipeline-graph.json'
        output_file.write_text(json.dumps(json_graph, indent=2))
        print(f"Generated JSON graph: {output_file}")
    
    # Also generate the simplified visualization config
    viz_config_file = flows_dir / 'pipeline-visualization.yaml'
    if viz_config_file.exists():
        print(f"\\nVisualization config available at: {viz_config_file}")
        print("This file contains structured data optimized for LLM pipeline monitoring")


if __name__ == "__main__":
    main()