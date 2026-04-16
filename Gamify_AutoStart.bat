@echo off
cd /d "C:\Users\viraj\OneDrive\Desktop\Gamify"

:: Start the Python server in a minimized window so it stays out of your way
start "" /min python app.py

:: Give the server 3 seconds to fully initialize
timeout /t 3 /nobreak >nul

:: Automatically open the dashboard in your default browser!
