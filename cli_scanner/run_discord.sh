#!/bin/bash

set -a
source .env
set +a

#./venv/bin/python scanner.py --date 4/29/2026 -w $DISCORD_WEBHOOK_URL
./venv/bin/python scanner.py -w $DISCORD_WEBHOOK_URL

