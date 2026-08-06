#!/bin/bash
set -e

echo "Starting SparkAssistant Docker Container..."

# Install dependencies if they are not already installed
pip install -r /app/requirements.txt

# Start the FastAPI web server directly
cd /app
python web_server.py
