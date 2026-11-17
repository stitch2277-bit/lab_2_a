@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "RECIPE_DOCKER=docker"
where docker >nul 2>nul
if not errorlevel 1 goto ready
set "RECIPE_DOCKER=%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe"
if exist "%RECIPE_DOCKER%" goto found
set "RECIPE_DOCKER=%USERPROFILE%\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
if exist "%RECIPE_DOCKER%" goto found
set "RECIPE_DOCKER=%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"
if not exist "%RECIPE_DOCKER%" goto missing
:found
for %%I in ("%RECIPE_DOCKER%") do set "PATH=%%~dpI;%PATH%"
:ready
"%RECIPE_DOCKER%" version >nul 2>nul
if errorlevel 1 goto stopped
if not exist "data" mkdir "data"
if not exist "data" goto folder_error
"%RECIPE_DOCKER%" container inspect recipes-lab-app >nul 2>nul
if errorlevel 1 goto create
"%RECIPE_DOCKER%" container inspect --format "{{.State.Running}}" recipes-lab-app | findstr /x "true" >nul
if not errorlevel 1 goto running
"%RECIPE_DOCKER%" start -ai recipes-lab-app
goto result
:create
"%RECIPE_DOCKER%" build -t recipes-lab:local .
if errorlevel 1 goto result
"%RECIPE_DOCKER%" run -it --name recipes-lab-app --mount "type=bind,source=%CD%\data,target=/app/data" recipes-lab:local
:result
set "RECIPE_EXIT=%ERRORLEVEL%"
if "%RECIPE_EXIT%"=="0" exit /b 0
echo Docker run failed. Read the error above.
pause
exit /b %RECIPE_EXIT%
:missing
echo Docker is not installed or is not in PATH.
echo Install Docker Desktop and restart this launcher. See DOCKER.md.
pause
exit /b 1
:stopped
echo Docker Engine is not available. Start Docker Desktop and wait until it is ready.
pause
exit /b 1
:folder_error
echo Cannot create the data folder. Check write access to the project folder.
pause
exit /b 1
:running
echo Container recipes-lab-app is already running. Use its existing console.
echo To attach from a terminal, run: docker attach recipes-lab-app
pause
exit /b 1
