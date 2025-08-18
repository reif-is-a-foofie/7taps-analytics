#!/bin/bash

echo "🚀 Setting up Streamlit app for Heroku deployment..."

# Create a new Heroku app for Streamlit
echo "Creating new Heroku app for Streamlit..."
heroku create seven-analytics-streamlit --buildpack heroku/python

# Set environment variables
echo "Setting environment variables..."
heroku config:set OPENAI_API_KEY="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"

# Copy the Streamlit Procfile to the main Procfile
echo "Setting up Procfile for Streamlit..."
cp Procfile.streamlit Procfile

# Add and commit changes
echo "Committing changes..."
git add .
git commit -m "feat: deploy Streamlit chat interface to Heroku"

# Deploy to Heroku
echo "Deploying to Heroku..."
git push heroku main

echo "✅ Streamlit app deployed! Check the URL above."
