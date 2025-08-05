#!/bin/bash

# Heroku Setup Script for 7taps Analytics
echo "🚀 Setting up Heroku for 7taps Analytics..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first:"
    echo "   brew install heroku/brew/heroku"
    exit 1
fi

# Get app name from user or use default
APP_NAME=${1:-"7taps-analytics"}
echo "📱 Using app name: $APP_NAME"

# Add PostgreSQL add-on
echo "🗄️  Adding PostgreSQL add-on..."
heroku addons:create heroku-postgresql:mini --app $APP_NAME

# Add Redis add-on
echo "🔴 Adding Redis add-on..."
heroku addons:create heroku-redis:mini --app $APP_NAME

# Set environment variables
echo "🔧 Setting environment variables..."
heroku config:set SEVENTAPS_AUTH_ENABLED=true --app $APP_NAME
heroku config:set SEVENTAPS_VERIFY_SIGNATURE=true --app $APP_NAME
heroku config:set LOG_LEVEL=info --app $APP_NAME
heroku config:set ENVIRONMENT=production --app $APP_NAME
heroku config:set PYTHONUNBUFFERED=1 --app $APP_NAME

# Set webhook secret (you'll need to change this)
echo "🔐 Setting webhook secret (change this in production)..."
heroku config:set SEVENTAPS_WEBHOOK_SECRET=your_webhook_secret_here --app $APP_NAME

# Set OpenAI key if available
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "🤖 Setting OpenAI API key..."
    heroku config:set OPENAI_API_KEY=$OPENAI_API_KEY --app $APP_NAME
else
    echo "⚠️  OPENAI_API_KEY not set. NLP features will use fallback mode."
fi

# Upload PEM keys
echo "🔑 Uploading PEM keys..."
heroku config:set SEVENTAPS_PRIVATE_KEY_PATH=keys/7taps_private_key.pem --app $APP_NAME
heroku config:set SEVENTAPS_PUBLIC_KEY_PATH=keys/7taps_public_key.pem --app $APP_NAME

# Copy keys to Heroku
echo "📁 Copying PEM keys to Heroku..."
heroku run "mkdir -p keys" --app $APP_NAME
cat keys/7taps_private_key.pem | heroku run "cat > keys/7taps_private_key.pem" --app $APP_NAME
cat keys/7taps_public_key.pem | heroku run "cat > keys/7taps_public_key.pem" --app $APP_NAME
heroku run "chmod 600 keys/7taps_private_key.pem" --app $APP_NAME

# Show configuration
echo "📋 Current configuration:"
heroku config --app $APP_NAME

echo "✅ Heroku setup complete!"
echo "🌐 Your app URL: https://$APP_NAME.herokuapp.com"
echo "🔗 Webhook URL: https://$APP_NAME.herokuapp.com/api/7taps/webhook"
echo "📊 Dashboard: https://$APP_NAME.herokuapp.com/ui/dashboard" 