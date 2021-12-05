#!/bin/bash
lux-ai-2021 --loglevel 1 --maxtime 30000 --seed $1 --out replay.json --height 12 --width 12 ./main.py ../i13/main.py && lux-ai-vis replay.json
