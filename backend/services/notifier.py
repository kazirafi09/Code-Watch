from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def notify(severity: str, filename: str, review_text: str) -> None:
    from backend.core.config import get_config
    cfg = get_config()
    notif = cfg.notifications

    summary = review_text[:100].replace("\n", " ")

    # Desktop notification
    if notif.desktop and severity in notif.desktop_severities:
        _desktop_notify(severity, filename, summary)

    # Telegram notification
    if notif.telegram and severity in notif.telegram_severities:
        token = notif.telegram_token
        chat_id = notif.telegram_chat_id
        if token and chat_id:
            await _telegram_notify(token, chat_id, severity, filename, review_text[:500])


def _desktop_notify(severity: str, filename: str, summary: str) -> None:
    try:
        from plyer import notification
        notification.notify(
            title=f"CodeWatch — {severity.upper()}",
            message=f"{filename}\n{summary}",
            app_name="CodeWatch",
            timeout=8,
        )
    except Exception as exc:
        logger.debug("Desktop notification failed: %s", exc)


async def _telegram_notify(
    token: str, chat_id: str, severity: str, filename: str, text: str
) -> None:
    try:
        import httpx
        message = f"*CodeWatch — {severity.upper()}*\n`{filename}`\n\n{text}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            })
    except Exception as exc:
        logger.debug("Telegram notification failed: %s", exc)
