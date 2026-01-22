# Deploy to Cloud Run
# Service Name: news-collector
# Region: asia-east1 (Taiwan)
# Source: Current directory (.)

Write-Host "Starting deployment to Cloud Run..."
gcloud run deploy news-collector `
    --source . `
    --region asia-east1 `
    --allow-unauthenticated `
    --project news-collector-14c2d

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
}
