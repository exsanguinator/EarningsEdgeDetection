#!/bin/bash

# Local runs read credentials from .env; in GitHub Actions they come from secrets
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

#./venv/bin/python scanner.py --date 4/29/2026 -w $DISCORD_WEBHOOK_URL
./venv/bin/python scanner.py -w $DISCORD_WEBHOOK_URL

