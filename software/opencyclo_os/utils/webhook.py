"""
OpenCyclo OS — Webhook Dispatcher
==================================

Sends HTTP POST alerts for biosecurity events, pH shock triggers,
and state machine transitions.

Works with any webhook-compatible endpoint (Slack, Discord, IFTTT, custom).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


logger = logging.getLogger("opencyclo")


async def send_webhook(
    url: Optional[str],
    event: str,
    message: str,
    severity: str = "info",
    data: Optional[dict] = None,
) -> bool:
    """
    Send a webhook notification.

    Uses stdlib urllib to avoid aiohttp dependency in garage mode.
    Runs the blocking HTTP call in a thread executor to stay async-friendly.

    Args:
        url: Webhook endpoint URL. If None, logs but does not send.
        event: Event type identifier (e.g., "biosecurity_alert", "ph_shock").
        message: Human-readable message body.
        severity: One of "info", "warning", "critical".
        data: Additional structured payload.

    Returns:
        True if sent successfully, False otherwise.
    """
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "opencyclo_os",
        "event": event,
        "severity": severity,
        "message": message,
    }
    if data:
        payload["data"] = data

    if url is None:
        logger.info(f"Webhook (no URL configured): [{event}] {message}")
        return False

    def _post():
        try:
            req = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except (URLError, OSError) as exc:
            logger.warning(f"Webhook delivery failed: {exc}")
            return False

    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _post)

    if success:
        logger.info(f"Webhook sent: [{event}] {message}")
    return success
