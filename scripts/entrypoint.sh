#!/bin/bash
set -e

echo "🌱 Irrigation Monitoring System - Starting..."

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h postgres -U irrigation_user; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "✅ PostgreSQL is ready"

# Wait for MQTT broker
echo "⏳ Waiting for MQTT broker..."
sleep 5

echo "✅ MQTT broker should be ready"

# Execute command
exec "$@"