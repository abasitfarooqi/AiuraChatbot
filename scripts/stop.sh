#!/bin/bash

# Stop script for AiuraChatbot

echo "Stopping AiuraChatbot..."

# Find and kill uvicorn processes
pkill -f "uvicorn backend.app.main:app"

echo "AiuraChatbot stopped."

