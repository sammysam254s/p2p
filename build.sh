#!/bin/bash

# Build script for Render deployment
# This script installs system dependencies and Python packages

echo "🚀 Starting build process..."

# Update package list
echo "📦 Updating package list..."
apt-get update -y

# Install tesseract-ocr for OCR functionality
echo "🔍 Installing tesseract-ocr..."
apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev

# Install other system dependencies for image processing
echo "🛠️ Installing system dependencies..."
apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# Clean up apt cache to reduce image size
echo "🧹 Cleaning up..."
apt-get clean
rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Verify tesseract installation
echo "🔍 Verifying tesseract installation..."
tesseract --version

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Build completed successfully!"