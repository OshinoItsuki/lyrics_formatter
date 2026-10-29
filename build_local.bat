@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "APP_NAME=歌詞改行ツール"
set "PYTHON_CMD=python"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。Python 3.12 以降をインストールしてください。
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] main.py がありません。リポジトリ直下から実行してください。
    pause
    exit /b 1
)
if not exist "icon.ico" (
    echo [ERROR] icon.ico がありません。
    pause
    exit /b 1
)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller をインストールしています...
    python -m pip install pyinstaller
    if errorlevel 1 goto :failed
)

echo.
echo [1/2] EXE を作成しています...
python -m PyInstaller --clean --noconfirm --onefile --windowed --name "%APP_NAME%" --icon "icon.ico" "main.py"
if errorlevel 1 goto :failed

echo.
echo [2/2] 配布フォルダにコピーしています...
if not exist "release" mkdir "release"
if not exist "release\%APP_NAME%_Local" mkdir "release\%APP_NAME%_Local"
copy /y "dist\%APP_NAME%.exe" "release\%APP_NAME%_Local\" >nul
if errorlevel 1 goto :failed
copy /y "icon.ico" "release\%APP_NAME%_Local\" >nul
if errorlevel 1 goto :failed
copy /y "read me.txt" "release\%APP_NAME%_Local\" >nul
if errorlevel 1 goto :failed

echo.
echo [OK] release\%APP_NAME%_Local に出力しました。
pause
exit /b 0

:failed
echo.
echo [ERROR] ビルドに失敗しました。
pause
exit /b 1
