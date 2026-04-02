@echo off
echo.
echo [1/3] Activating Virtual Environment...
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate

echo.
echo [2/3] Installing Dependencies (if missing)...
pip install fastapi uvicorn sqlalchemy pydantic

echo.
echo [3/3] Starting Analytica Dashboard Server on Port 8000...
echo Visit http://localhost:8000 to view the Dashboard.
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
