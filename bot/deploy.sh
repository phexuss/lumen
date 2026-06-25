#!/bin/bash
# Quick production deployment script

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         HDRezka Bot - Production Deployment                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install it first:"
    echo "   curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Check if .env.prod exists
if [ ! -f .env.prod ]; then
    echo "⚠️  .env.prod not found. Creating from example..."
    cp .env.prod.example .env.prod
    echo "✅ Created .env.prod"
    echo
    echo "📝 Please edit .env.prod and set:"
    echo "   - BOT_TOKEN"
    echo "   - PUBLIC_URL"
    echo "   - ADMIN_IDS"
    echo
    echo "Then run this script again."
    exit 0
fi

# Create data directory
mkdir -p data

# Build and start
echo "🔨 Building Docker image..."
docker compose -f docker-compose.prod.yml build

echo "🚀 Starting container..."
docker compose -f docker-compose.prod.yml up -d

echo
echo "✅ Bot deployed!"
echo
echo "📊 Check status:"
echo "   docker compose -f docker-compose.prod.yml ps"
echo
echo "📋 View logs:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo
echo "🏥 Health check:"
echo "   curl http://localhost:8080/health"
echo
