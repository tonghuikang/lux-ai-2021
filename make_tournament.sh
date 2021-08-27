rm -rf errorlogs
rm -rf replays
lux-ai-2021 --rankSystem="trueskill" --tournament --storeReplay=false --storeLogs=false $(find . -type f -name "main.py")
