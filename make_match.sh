#!/bin/bash
lux-ai-2021 --loglevel 1 --maxtime 30000 --seed $1 --out replay.json --height 18 --width 18 ./main.py ../i1/main.py && lux-ai-vis replay.json
