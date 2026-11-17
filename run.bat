@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if errorlevel 1 goto folder_error
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "RECIPE_PYTHON=.venv\Scripts\python.exe"
if not exist "%RECIPE_PYTHON%" set "RECIPE_PYTHON=python"
if not exist "data" mkdir "data"
if not exist "data" goto folder_error
title Recipe Calculator
"%RECIPE_PYTHON%" -u "%~dp0main.py" %*
set "RECIPE_EXIT=%ERRORLEVEL%"
if "%RECIPE_EXIT%"=="0" exit /b 0
echo.
echo Application stopped with an error. Code: %RECIPE_EXIT%
echo Read the error above. This window stays open until you press a key.
echo To install dependencies, run:
echo "%RECIPE_PYTHON%" -m pip install -r "%~dp0requirements.txt"
echo.
pause
exit /b %RECIPE_EXIT%
:folder_error
echo Cannot access the application folder or create the data folder.
echo Check that the project is unpacked into a writable folder.
pause
exit /b 1
