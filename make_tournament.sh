rm -rf errorlogs
rm -rf replays

# run game or tournament locally
# lux-ai-2021 --loglevel 1 --maxtime 30000 --out replay.json --height 12 --width 12 ./main.py ../i1/main.py && lux-ai-vis replay.json
# lux-ai-2021 --loglevel 1 --maxtime 30000 --out replay.json ./main.py ../i1/main.py && lux-ai-vis replay.json
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 30000 ./main.py ../i1/main.py
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 30000 $(find . -type f -name "main.py")
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --tournament --storeReplay=false --storeLogs=false ./main.py ../v2/main.py ../v3/main.py

# play one game and visualise if you lose
# if lux-ai-2021 --loglevel 1 --maxtime 30000 --width 12 --height 12 --out replay.json  ./main.py ../i1/main.py | tee "$(tty)" | grep -q 'rank: 1, agentID: 1'; then
#   lux-ai-vis replay.json
# fi

# play game until you lose, and then visualise
while lux-ai-2021 --loglevel 1 --maxtime 30000 --height 12 --width 12 --out replay.json  ./main.py ../i1/main.py | tee "$(tty)" | grep -q 'rank: 1, agentID: 0'; do
    true
done; lux-ai-vis replay.json
# while lux-ai-2021 --loglevel 1 --maxtime 30000 --out replay.json  ./main.py ../i1/main.py | tee "$(tty)" | grep -q 'rank: 1, agentID: 0'; do
#     true
# done; lux-ai-vis replay.json

# run game or tournament on VM with more CPUs
# export GFOOTBALL_DATA_DIR=C to disable saving the pickle files
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 ./main.py ../v3/main.py ../v4a/main.py
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 ./main.py ../v3/main.py ../v4a/main.py
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 $(find . -type f -name "main.py")

# Test whether your agent is symmetric or prefers one orientation over another
# lux-ai-2021 --loglevel 1 --maxtime 30000 ./main.py ./main.py
# GFOOTBALL_DATA_DIR=C for run in {1..500}; do lux-ai-2021 --seed $run --loglevel 1 --width 12 --height 12 --maxtime 30000 main.py main.py | tee logs.txt; done
# GFOOTBALL_DATA_DIR=C for run in {1..500}; do lux-ai-2021 --seed $run --loglevel 1 --maxtime 30000 main.py main.py | tee logs.txt; done
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 30000 ./main.py ./main.py

# Upload agent to remote server
# rsync -a --exclude="*.pkl" --exclude="*.pyc" --"exclude=*.log" --exclude=replays/ . hkmac@35.221.209.96:v4