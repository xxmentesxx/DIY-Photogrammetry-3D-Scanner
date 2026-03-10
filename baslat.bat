@echo off
title MENTECH SCANNER
color 0A
cls
echo =================================================
echo        MENTECH 3D TARAYICI BASLATILIYOR
echo =================================================
echo.
echo Bilgisayar IP Adresi Bulunuyor...
for /f "tokens=14" %%a in ('ipconfig ^| findstr IPv4') do set ip=%%a
echo PC IP Adresi: %ip%
echo.
echo Lutfen telefondan https://%ip%:5000 adresine girin.
echo "Guvenli Degil" uyarisi alirsaniz "Gelismis -> Devam Et" deyin.
echo.
echo =================================================
echo.

python app.py

pause