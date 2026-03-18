@echo off
REM Run REBEKA tests

cd /d %~dp0

echo ========================================
echo REBEKA Test Suite
echo ========================================
echo.

python -m pytest tests/unit/ -v --tb=short

echo.
echo ========================================
echo Test run complete!
echo ========================================
pause
