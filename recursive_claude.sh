#!/bin/bash

# A function to handle graceful shutdown when you press Ctrl+C
cleanup() {
    echo -e "\nCaught interrupt signal. Shutting down."
    # Add any other cleanup commands here if needed
    exit 0
}

# Trap the interrupt signal (Ctrl+C) and call the cleanup function
trap cleanup SIGINT

echo "Starting the hourly Claude process. Press Ctrl+C to stop."
echo "-------------------------------------------------"

# This is the infinite loop that makes the command "recursive"
while true; do
    echo "[$(date)] Waiting for one hour (3600 seconds)..."
    sleep 3600

    echo "[$(date)] Hour is up. Sending 'continue' to Claude..."
    # Your original command
    echo "continue" | claude --dangerously-skip-permissions

    echo "[$(date)] Command finished. The loop will now restart."
    echo "-------------------------------------------------"
done
