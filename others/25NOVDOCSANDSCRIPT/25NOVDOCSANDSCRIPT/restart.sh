#!/bin/bash

# Restart script for AiuraChatbot

echo "Restarting AiuraChatbot..."

# Stop
./scripts/stop.sh

# Wait a moment
sleep 2

# Start
./scripts/start.sh

