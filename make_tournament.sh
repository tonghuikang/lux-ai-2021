rm -rf errorlogs
rm -rf replays

# run game or tournament locally
# lux-ai-2021 --loglevel 1 --maxtime 30000 --out replay.json --height 12 --width 12 ./main.py ../i1/main.py && lux-ai-vis replay.json
# lux-ai-2021 --loglevel 1 --maxtime 30000 --out replay.json ./main.py ../i1/main.py && lux-ai-vis replay.json
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 30000 ./main.py ../i1/main.py
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxtime 30000 $(find . -type f -name "main.py")
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --tournament --storeReplay=false --storeLogs=false ./main.py ../v2/main.py ../v3/main.py

# run game or tournament on VM with more CPUs
# export GFOOTBALL_DATA_DIR=C to disable saving the pickle files
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --rankSystem="wins" --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 ./main.py ../v3/main.py ../v4a/main.py
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 ./main.py ../v3/main.py ../v4a/main.py
# GFOOTBALL_DATA_DIR=C lux-ai-2021 --tournament --storeReplay=false --storeLogs=false --maxConcurrentMatches=16 --maxtime 10000 $(find . -type f -name "main.py")

# Upload agent to remote server
# rsync -a --exclude="*.pkl" --exclude="*.pyc" --"exclude=*.log" --exclude=replays/ . hkmac@35.221.209.96:v4

# play game until you lose, and then visualise
while GFOOTBALL_DATA_DIR=C lux-ai-2021 --loglevel 1 --maxtime 30000 --height 12 --width 12 --out replay.json  ./main.py ../i13/main.py | tee "$(tty)" | grep -q 'rank: 1, agentID: 0'; do
    cp replay.json replay_old.json
done; lux-ai-vis replay.json
