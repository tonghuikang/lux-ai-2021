rm -rf errorlogs
rm -rf replays
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false $(find . -type f -name "main.py")
lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false ./main.py ../v01-polar/main.py
