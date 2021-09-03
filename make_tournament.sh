rm -rf errorlogs
rm -rf replays
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false $(find . -type f -name "main.py")
lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false ./main.py ../v2/main.py
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 ./v2/main.py ./v3a/main.py
# lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 $(find . -type f -name "main.py")
