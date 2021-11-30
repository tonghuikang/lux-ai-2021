#!/bin/bash
lux-ai-2021 --loglevel 1 --maxtime 30000 --seed $1 --out replay.json --height 24 --width 24 ./main.py ../i21/main.py && lux-ai-vis replay.json
