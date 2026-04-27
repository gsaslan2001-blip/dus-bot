@echo off
REM DUS Günlük Sync — Windows Task Scheduler tarafından çalıştırılır
REM Görev Zamanlayıcısı Ayarı: Her gün 06:00'da çalıştır

set PYTHON=C:\Users\FURKAN\.venv\Scripts\python.exe
set SCRIPT=C:\Users\FURKAN\Desktop\Projeler\Pinecone\scripts\auto_sync_dus.py

echo %DATE% %TIME% - DUS sync basliyor >> C:\Users\FURKAN\Desktop\Projeler\Pinecone\logs\scheduler.log
"%PYTHON%" "%SCRIPT%" >> C:\Users\FURKAN\Desktop\Projeler\Pinecone\logs\scheduler.log 2>&1
echo %DATE% %TIME% - DUS sync bitti >> C:\Users\FURKAN\Desktop\Projeler\Pinecone\logs\scheduler.log
