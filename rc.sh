#!/bin/bash

# Set the prompt to the first argument, or use default if not provided
if [ $# -eq 0 ]; then
    PROMPT="remember your last tasks and continue. If you run out of tasks think of new ones that would improve the maintainability, usefulness, and reliability of this system"
else
    PROMPT="$1"
fi

# A function to handle graceful shutdown when you press Ctrl+C
cleanup() {
    echo -e "\nCaught interrupt signal. Shutting down."
    # Add any other cleanup commands here if needed
    exit 0
}

# Trap the interrupt signal (Ctrl+C) and call the cleanup function
trap cleanup SIGINT

echo "Starting the hourly Claude process. Press Ctrl+C to stop."
echo "Prompt: $PROMPT"
echo "-------------------------------------------------"

# This is the infinite loop that makes the command "recursive"
while true; do
    echo "[$(date)] Waiting for 1/3 hour (1200 seconds)..."
    sleep 1200

    echo "[$(date)] Hour is up. Sending prompt to Claude..."
    # Send the prompt to Claude
    echo "$PROMPT" | yolo

    echo "[$(date)] Command finished. The loop will now restart."
    echo "-------------------------------------------------"
done
