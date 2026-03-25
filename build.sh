#!/bin/bash

# Build script for Render deployment
# Lightweight build without heavy AI/ML dependencies

echo "🚀 Starting lightweight build process..."

# Update package list
echo "📦 Updating package list..."
apt-get update -y

# Install minimal system dependencies
echo "🛠️ Installing minimal system dependencies..."
apt-get install -y libpq-dev

# Clean up apt cache to reduce image size
echo "🧹 Cleaning up..."
apt-get clean
rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Lightweight build completed successfully!"