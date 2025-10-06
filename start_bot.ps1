# --- start_bot.ps1 ---

# 1) Находим папку рабочего стола корректным способом
$desktop = [Environment]::GetFolderPath('Desktop')

# 2) Собираем путь до проекта (папка "affirmatoins_bot")
$proj = Join-Path $desktop 'affirmatoins_bot'

# 3) Переходим туда
Set-Location $proj

# 4) Активируем venv (создаём, если его нет)
if (-not (Test-Path '.\.venv\Scripts\Activate.ps1')) {
    py -m venv .venv
}
. .\.venv\Scripts\Activate.ps1   # точка-пробел: «подключить» скрипт активации

# 5) Запускаем бота
python .\bot.py

# 6) Чтобы окно не захлопнулось
Pause
