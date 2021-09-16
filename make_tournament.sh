rm -rf errorlogs
rm -rf replays

# locally
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 10000 $(find . -type f -name "main.py")
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 10000 ./main.py ../v3/main.py
# lux-ai-2021 --tournament --storeReplay=false --storeLogs=false ./main.py ../v2/main.py ../v3/main.py
lux-ai-2021 --loglevel 1 --maxtime 10000 ./main.py ../v3/main.py

# on GCP
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 ./main.py ../v2/main.py ../v3/main.py
# lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 $(find . -type f -name "main.py")
