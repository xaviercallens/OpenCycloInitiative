# 🌍 Project Genesis — GCP Deployment Automation for PowerShell
# Run this inside the \software\cyclo_earth_web directory

Write-Host "Initiating Project Genesis GCP Deployment..." -ForegroundColor Cyan

# Ensure gcloud is in the PATH if installed in D:\Cloud SDK
$gcloudPath = "D:\Cloud SDK\google-cloud-sdk\bin"
if (Test-Path $gcloudPath) {
    if ($env:PATH -notmatch [regex]::Escape($gcloudPath)) {
        $env:PATH += ";$gcloudPath"
    }
}

if (-Not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "gcloud CLI could not be found. Please ensure it is installed and in your PATH." -ForegroundColor Red
    exit
}

Write-Host "Select your deployment target:"
Write-Host "1) Google Cloud Run (Docker Container - Recommended for rapid scaling)"
Write-Host "2) Google App Engine (Static Files - Recommended for simple hosting)"
$target = Read-Host "Selection (1 or 2)"

if ($target -eq "1") {
    Write-Host "Deploying to Google Cloud Run..." -ForegroundColor Cyan
    # Build container natively and deploy
    gcloud run deploy project-genesis `
        --source . `
        --region us-central1 `
        --allow-unauthenticated `
        --port 8080 `
        --platform managed
    
    Write-Host "Cloud Run deployment complete!" -ForegroundColor Green
}
elseif ($target -eq "2") {
    Write-Host "Deploying to Google App Engine..." -ForegroundColor Cyan
    # Simply push the app.yaml config
    gcloud app deploy app.yaml `
        --version v1 `
        --promote
    
    Write-Host "App Engine deployment complete!" -ForegroundColor Green
    gcloud app browse --no-launch-browser
}
else {
    Write-Host "Invalid selection. Exiting." -ForegroundColor Red
}
