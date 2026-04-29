import requests
import logging
from typing import List

DISCORD_MAX_LEN = 2000


def _chunk(content: str) -> List[str]:
    if len(content) <= DISCORD_MAX_LEN:
        return [content]
    chunks, current = [], []
    current_len = 0
    for line in content.splitlines(keepends=True):
        # If a single line exceeds the limit, hard-split it
        while len(line) > DISCORD_MAX_LEN:
            remaining = DISCORD_MAX_LEN - current_len
            current.append(line[:remaining])
            chunks.append("".join(current))
            current, current_len = [], 0
            line = line[remaining:]
        if current_len + len(line) > DISCORD_MAX_LEN:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


def send_webhook(webhooks_url: str, messages: List[str], logger: logging.Logger) -> None:
    """Post each message in `messages` as a separate Discord webhook request."""
    headers = {"Content-Type": "application/json"}
    for hook in (h.strip() for h in webhooks_url.split(",")):
        for content in messages:
            for chunk in _chunk(content):
                try:
                    response = requests.post(hook, json={"content": chunk}, headers=headers, timeout=10)
                    if response.status_code >= 400:
                        logger.error(f"Webhook request failed ({response.status_code}): {response.text}")
                except Exception as e:
                    logger.error(f"Error sending webhook: {e}")
