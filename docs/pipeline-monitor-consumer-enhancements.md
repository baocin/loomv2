# Pipeline Monitor Consumer Enhancements

## Summary

Enhanced the Loom Pipeline Monitor to provide detailed consumer-level metrics, log viewing, and proper flow visualization with individual consumer nodes.

## Features Added

### 1. Consumer Metrics Display
- **Messages Processed**: Shows total input messages consumed
- **Messages Output**: Shows total output messages produced
- **Pass-through Rate**: Percentage of messages that successfully flow through
- **Consumer Lag**: Real-time lag monitoring
- **Processing Time**: Average message processing time
- **Message Rate**: Messages per second throughput

### 2. Consumer Log Viewer
- View last 500/1000/5000 lines of logs
- Real-time log filtering
- Color-coded log levels (ERROR, WARN, INFO, DEBUG)
- Download logs as text file
- Auto-scroll functionality
- Supports both Docker containers and Kubernetes pods

### 3. Enhanced Flow Visualization
- Each consumer shown as explicit node in the flow
- Database-sourced consumer configurations
- Real-time metrics overlay on nodes
- Visual indicators for:
  - Consumer health status
  - Message flow rates
  - Processing bottlenecks
  - Error conditions

### 4. New API Endpoints

#### Consumer Metrics
- `GET /api/consumers/metrics` - Get processing metrics for all consumers
- `GET /api/consumers/lag` - Get consumer lag information
- `GET /api/consumers/flow` - Get message flow statistics

#### Consumer Operations
- `GET /api/consumers/:serviceName/logs` - Fetch consumer logs
- `GET /api/consumers/:serviceName/status` - Get detailed consumer status

## Implementation Details

### Backend Changes

1. **Database Client Extensions** (`database/client.ts`):
   - `getConsumerMetrics()` - Aggregate metrics from `consumer_processing_metrics` table
   - `getConsumerLag()` - Latest lag data from `consumer_lag_history`
   - `getMessageFlow()` - Calculate input/output message rates
   - `getConsumerLogs()` - Fetch logs via Docker/K8s

2. **New Routes** (`routes/consumers.ts`):
   - Comprehensive consumer monitoring endpoints
   - Docker and Kubernetes log fetching
   - Aggregated status information

### Frontend Changes

1. **ConsumerNode Component** (`NodeTypes.tsx`):
   - Displays message flow metrics
   - Shows processing statistics
   - Integrated log viewer button
   - Visual status indicators

2. **ConsumerLogViewer Component**:
   - Terminal-style log display
   - Real-time filtering
   - Log level color coding
   - Download functionality

3. **PipelineFlowView Component**:
   - Database-driven flow visualization
   - Automatic graph layout with dagre
   - Real-time metric updates
   - Consumer-centric view

## Usage

### View Enhanced Pipeline Flow
1. Open Pipeline Monitor
2. Click "Show Flow View" button
3. Each consumer appears as a detailed node showing:
   - Input/Output message counts
   - Pass-through percentage
   - Current lag
   - Processing metrics

### View Consumer Logs
1. In Flow View, click "Logs" button on any consumer node
2. Log viewer opens with:
   - Last 500 lines by default
   - Real-time filtering
   - Adjustable line count
   - Download option

### Monitor Consumer Performance
- Green status: Healthy, low lag
- Yellow status: Moderate lag (1000-10000 messages)
- Red status: High lag (>10000 messages)
- Pass-through rate indicates processing efficiency

## Database Tables Used

- `pipeline_stages` - Consumer service definitions
- `pipeline_stage_topics` - Topic relationships
- `consumer_processing_metrics` - Performance metrics
- `consumer_lag_history` - Lag tracking
- `pipeline_consumer_configs` - Optimized configurations

## Next Steps

1. **Add Historical Metrics**: Time-series graphs for consumer performance
2. **Alert Integration**: Notifications for high lag or errors
3. **Consumer Control**: Start/stop/restart consumers from UI
4. **Metric Export**: Export consumer metrics to CSV/JSON
5. **Multi-consumer Comparison**: Side-by-side performance analysis
