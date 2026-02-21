#!/bin/bash
# 🌍 Project Genesis — GCP Deployment Automation
# Run this inside the /software/cyclo_earth_web directory

echo "Initiating Project Genesis GCP Deployment..."

if ! command -v gcloud &> /dev/null
then
    echo "gcloud CLI could not be found. Please install the Google Cloud SDK."
    exit
fi

echo "Select your deployment target:"
echo "1) Google Cloud Run (Docker Container - Recommended for rapid scaling)"
echo "2) Google App Engine (Static Files - Recommended for simple hosting)"
read -p "Selection (1 or 2): " TARGET

if [ "$TARGET" = "1" ]; then
    echo "Deploying to Google Cloud Run..."
    # Build container natively and deploy
    gcloud run deploy project-genesis \
        --source . \
        --region us-central1 \
        --allow-unauthenticated \
        --port 8080 \
        --platform managed
    
    echo "Cloud Run deployment complete!"
elif [ "$TARGET" = "2" ]; then
    echo "Deploying to Google App Engine..."
    # Simply push the app.yaml config
    gcloud app deploy app.yaml \
        --version v1 \
        --promote
    
    echo "App Engine deployment complete! URL: $(gcloud app browse --no-launch-browser)"
else
    echo "Invalid selection. Exiting."
fi
