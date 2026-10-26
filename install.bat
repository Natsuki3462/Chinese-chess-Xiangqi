@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title XiangqiFloat 安装

echo ============================================
echo   XiangqiFloat 安装
echo ============================================
echo.

set "PYEXE="
where python >nul 2>nul
if not errorlevel 1 (set "PYEXE=python" & goto :havepy)
where py >nul 2>nul
if not errorlevel 1 (set "PYEXE=py -3" & goto :havepy)
echo [x] 未找到 Python。请先安装 Python 3.10+，并勾选 "Add to PATH"。
pause
exit /b 1

:havepy
echo [1/4] Python: %PYEXE%

if exist ".venv\Scripts\python.exe" goto :havevenv
echo       创建虚拟环境 .venv ...
%PYEXE% -m venv .venv
if errorlevel 1 (
    echo [x] 虚拟环境创建失败。
    pause
    exit /b 1
)
:havevenv

set "PIP_CACHE_DIR=%~dp0.cache\pip"
set "TMP=%~dp0.cache\tmp"
set "TEMP=%~dp0.cache\tmp"
if not exist ".cache\tmp" mkdir ".cache\tmp" >nul 2>nul

echo [2/4] 安装依赖 PyQt6 / cchess / python-chess ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --no-cache-dir -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt --no-cache-dir -q
if errorlevel 1 (
    echo [x] 依赖安装失败，请检查网络。
    pause
    exit /b 1
)

echo [3/4] 检查引擎 ...
if exist "engine\pikafish.exe" goto :haveexe
echo.
echo [!] 未找到 engine\pikafish.exe
echo     请下载 Pikafish 后解压，把 exe 改名为 pikafish.exe 放到 engine\ 目录。
echo     下载页: https://github.com/official-pikafish/Pikafish/releases
echo.
pause
exit /b 1

:haveexe
if exist "engine\pikafish.nnue" goto :havennue
echo.
echo [!] 未找到 engine\pikafish.nnue
echo     神经网络权重必须与 pikafish.exe 放在同一目录，否则引擎无法启动。
echo     下载页: https://github.com/official-pikafish/Networks/releases
echo.
pause
exit /b 1

:havennue
echo       引擎与权重就绪

echo [4/4] 运行验证 ...
".venv\Scripts\python.exe" tools\validate_fen.py
if errorlevel 1 (
    echo [!] FEN 兼容性验证未通过。
    pause
    exit /b 1
)

echo.
echo ============================================
echo   安装完成，双击 run.bat 启动
echo ============================================
pause
