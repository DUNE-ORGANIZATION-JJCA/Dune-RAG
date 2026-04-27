@echo off
echo Starting Dune RAG services for local development...
echo.

echo [1/3] Starting Qdrant...
if exist "..\qdrant\qdrant.exe" (
    Start /B "" "..\qdrant\qdrant.exe" 2>nul
) else (
    echo   Qdrant not found - ensure it's running or in PATH
)
timeout /t 2 /nobreak >nul

echo [2/3] Starting RAG API (port 8000)...
Start /B cmd /c "cd .. && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

echo [3/3] Starting Chatbot UI (port 7860)...
Start /B cmd /c "cd ..\Dune-Chatbot && python app.py"

echo.
echo ========================================
echo Services started:
echo   - Chatbot UI:    http://localhost:7860
echo   - RAG API:      http://localhost:8000
echo   - Qdrant:       http://localhost:6333
echo   - Ollama:       http://localhost:11434
echo ========================================
echo.
echo Press any key to exit...
pause >nul