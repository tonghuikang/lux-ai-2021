rm -rf errorlogs
rm -rf replays

# locally
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 30000 $(find . -type f -name "main.py")
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 30000 ./main.py ../v3/main.py
# lux-ai-2021 --tournament --storeReplay=false --storeLogs=false ./main.py ../v2/main.py ../v3/main.py
lux-ai-2021 --loglevel 1 --maxtime 30000 ./main.py ../v3/main.py

# on GCP with more CPUs
# export GFOOTBALL_DATA_DIR=C  # to disable saving pickle files
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 ./main.py ../v2/main.py ../v3/main.py
# lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 $(find . -type f -name "main.py")

# Test whether your agent prefers one direction
# lux-ai-2021 --loglevel 1 --maxtime 30000 ./main.py ./main.py
# for run in {1..500}; do lux-ai-2021 --seed $run --loglevel 1 --width 12 --height 12 --maxtime 30000 main.py main.py | tee logs.txt; done
# for run in {1..500}; do lux-ai-2021 --seed $run --loglevel 1 --maxtime 30000 main.py main.py | tee logs.txt; done
# lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 30000 ./main.py ./main.py

# rsync to remote server
# rsync -a --exclude="*.pkl" --exclude="*.pyc" --"exclude=*.log" --exclude=replays/ . hkmac@35.221.209.96:v4