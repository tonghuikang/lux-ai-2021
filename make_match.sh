#!/bin/bash
lux-ai-2021 --loglevel 1 --maxtime 30000 --seed $1 --out replay.json --height 32 --width 32 ./main.py ../i3/main.py && lux-ai-vis replay.json
