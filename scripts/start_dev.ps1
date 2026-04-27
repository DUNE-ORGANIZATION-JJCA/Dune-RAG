# Dune RAG Startup Script
# Run this to start all services for local development

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Write-Host "Starting Dune RAG services..." -ForegroundColor Cyan
Write-Host ""

# Qdrant (requires qdrant.exe in project root or in PATH)
Write-Host "[1/4] Starting Qdrant..." -ForegroundColor Yellow
$qdrantExe = Join-Path $PROJECT_ROOT "qdrant\qdrant.exe"
if (Test-Path $qdrantExe) {
    $qdrant = Start-Process -FilePath $qdrantExe -PassThru -WindowStyle Hidden
} else {
    Write-Host "  Qdrant not found at $qdrantExe - skipping (ensure it's running)" -ForegroundColor Yellow
}
Start-Sleep -Seconds 2

# RAG API
Write-Host "[2/4] Starting RAG API..." -ForegroundColor Yellow
$rag = Start-Process python -ArgumentList "-m uvicorn api.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $PROJECT_ROOT -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5

# Chatbot UI (from Dune-Chatbot package)
Write-Host "[3/4] Starting Chatbot UI..." -ForegroundColor Yellow
$chatDir = Join-Path $PROJECT_ROOT "Dune-Chatbot"
$chat = Start-Process python -ArgumentList "app.py" -WorkingDirectory $chatDir -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Services started:" -ForegroundColor Green
Write-Host "  Chatbot UI:  http://localhost:7860" -ForegroundColor White
Write-Host "  RAG API:    http://localhost:8000" -ForegroundColor White
Write-Host "  Qdrant:    http://localhost:6333" -ForegroundColor White
Write-Host "  Ollama:    http://localhost:11434" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green