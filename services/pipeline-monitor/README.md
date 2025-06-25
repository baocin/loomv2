# Pipeline Monitor - Frontend

A React-based visualization dashboard for monitoring the Loom v2 data pipeline in real-time.

## Features

- **React Flow Visualization**: Interactive pipeline diagram showing data flow
- **Real-time Monitoring**: WebSocket updates for live status changes
- **Topic Metrics**: Message counts, consumer lag, processing rates
- **Interactive Nodes**: Click to view raw data and detailed metrics
- **Responsive Design**: Built with Tailwind CSS

## Development

```bash
# Install dependencies
make install

# Start development server
make dev

# Build for production
make build

# Run with Docker
make docker
make docker-run
```

## Environment Variables

See `.env.example` for configuration options:
- `VITE_API_URL`: Backend API endpoint (default: http://localhost:8080)
- `VITE_WS_URL`: WebSocket endpoint for real-time updates

## Architecture

The frontend connects to the Pipeline Monitor API to fetch:
- Kafka topic metrics and consumer groups
- TimescaleDB database metrics
- Real-time updates via WebSocket

Built with:
- React 18 + TypeScript
- React Flow for pipeline visualization
- TanStack Query for data fetching
- Tailwind CSS for styling
- Vite for fast development
