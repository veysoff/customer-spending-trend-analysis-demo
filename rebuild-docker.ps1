# PowerShell script for complete Docker rebuild without cache

Write-Host "Rebuilding Docker..." -ForegroundColor Green
Write-Host ""

# Check if we are in the correct directory
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "Error: docker-compose.yml not found!" -ForegroundColor Red
    Write-Host "Run this script from the project root folder" -ForegroundColor Red
    exit 1
}

# Step 1: Stop and remove containers + volumes
Write-Host "Step 1/4: Stopping containers and removing volumes..." -ForegroundColor Yellow
docker-compose down -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Some containers may have already been removed" -ForegroundColor Yellow
}

Write-Host "Done: Containers and volumes removed" -ForegroundColor Green
Write-Host ""

# Step 2: Clean Docker system
Write-Host "Step 2/4: Cleaning Docker cache..." -ForegroundColor Yellow
docker system prune -f
Write-Host "Done: Docker cache cleaned" -ForegroundColor Green
Write-Host ""

# Step 3: Remove local data
Write-Host "Step 3/4: Removing local application data..." -ForegroundColor Yellow
if (Test-Path "backend/data") {
    Remove-Item -Recurse -Force "backend/data/*" -ErrorAction SilentlyContinue
    Write-Host "Done: Local data removed" -ForegroundColor Green
} else {
    Write-Host "Info: backend/data folder does not exist" -ForegroundColor Cyan
}
Write-Host ""

# Step 4: Rebuild and start
Write-Host "Step 4/4: Rebuilding and starting containers..." -ForegroundColor Yellow
docker-compose up --build --force-recreate -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Docker has been completely rebuilt without cache!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Application is available at:" -ForegroundColor Cyan
    Write-Host "   * Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "   * Backend API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "   * API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "What was done:" -ForegroundColor Cyan
    Write-Host "   - Stopped all containers" -ForegroundColor Cyan
    Write-Host "   - Removed all volumes" -ForegroundColor Cyan
    Write-Host "   - Cleaned Docker build cache" -ForegroundColor Cyan
    Write-Host "   - Removed local data" -ForegroundColor Cyan
    Write-Host "   - Rebuilt images from scratch" -ForegroundColor Cyan
    Write-Host "   - Started new containers" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Database initialization takes 10-15 seconds..." -ForegroundColor Yellow
    Write-Host "Use: docker-compose logs -f backend" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Error during Docker rebuild!" -ForegroundColor Red
    exit 1
}
