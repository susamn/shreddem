@echo off
echo ============================================
echo   Gmail Client - Starting...
echo ============================================
echo.

:: Install backend dependencies
echo [1/2] Installing Python dependencies...
cd backend
pip install -r requirements.txt -q
cd ..

:: Install frontend dependencies
echo [2/2] Installing frontend dependencies...
cd frontend
call npm install --silent
cd ..

:: Start both servers
echo.
echo Starting servers...
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:3000
echo.

start "Gmail Client - Backend" cmd /c "cd backend && python main.py"
timeout /t 2 /nobreak > nul
start "Gmail Client - Frontend" cmd /c "cd frontend && npm run dev"

echo Open http://localhost:3000 in your browser
echo.
pause
