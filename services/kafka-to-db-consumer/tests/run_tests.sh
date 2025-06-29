#!/bin/bash
# Run tests for kafka-to-db-consumer

set -e

echo "Running kafka-to-db-consumer tests..."
echo "=================================="

# Change to service directory
cd "$(dirname "$0")/.."

# Install test dependencies if needed
echo "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov

# Run smoke tests first
echo ""
echo "Running smoke tests..."
python -m pytest tests/test_smoke.py -v

echo ""
echo "Running generic consumer smoke tests..."
python -m pytest tests/test_generic_consumer_smoke.py -v

echo ""
echo "Running mapping engine tests..."
python -m pytest tests/test_mapping_engine.py -v

# Run all tests with coverage
echo ""
echo "Running all tests with coverage..."
python -m pytest tests/ -v --cov=app --cov-report=term-missing

echo ""
echo "All tests completed!"
