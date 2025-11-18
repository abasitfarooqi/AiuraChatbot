#!/bin/bash

# Start script for AiuraChatbot

echo "Starting AiuraChatbot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Start the application
echo "Starting FastAPI server..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

