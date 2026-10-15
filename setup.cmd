@echo off
setlocal
cd /d "%~dp0"
python monitor.py setup
if errorlevel 1 pause
