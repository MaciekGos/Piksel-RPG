@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Uruchamia kroki 1-4 po kolei i zatrzymuje sie przy pierwszym bledzie.
call 1_przygotuj.bat nopause
if errorlevel 1 goto fail
call 2_zasoby.bat nopause
if errorlevel 1 goto fail
call 3_testy.bat nopause
if errorlevel 1 goto fail
call 4_buduj_instalator.bat nopause
if errorlevel 1 goto fail
echo.
echo ============================================
echo  WSZYSTKO GOTOWE:  dist\PikselRPG-Setup.exe
echo ============================================
choice /m "Uruchomic instalator teraz"
if not errorlevel 2 call 5_uruchom_instalator.bat
exit /b 0
:fail
echo.
echo [BLAD] Przerwano - zobacz komunikat powyzej.
pause
exit /b 1
