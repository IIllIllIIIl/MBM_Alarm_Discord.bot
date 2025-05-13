@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo 🔨 디스코드 봇 EXE 빌드 시작...

pyinstaller --onefile ^
  --icon=discord_alert_icon.ico ^
  --add-binary "ffmpeg.exe;." ^
  --add-binary "opus.dll;." ^
  --add-data "audio;audio" ^
  --hidden-import=pynacl --hidden-import=nacl --hidden-import=six --hidden-import=cffi ^
  code.py


echo ✅ 빌드 완료! dist 폴더를 확인하세요.
pause
