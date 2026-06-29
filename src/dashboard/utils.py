"""
src/dashboard/utils.py
=========================
Small, dependency-free presentation helpers shared across views.
"""

from datetime import datetime


def relative_time(dt: datetime) -> str:
    """'3 minutes ago' / '2 hours ago' / '5 days ago' style formatting,
    without pulling in an extra dependency like `humanize`."""
    if dt is None:
        return "never"

    now = datetime.utcnow()
    try:
        delta = now - dt.replace(tzinfo=None)
    except Exception:
        return str(dt)

    seconds = delta.total_seconds()
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = int(seconds // 60)
        return f"{m} min{'s' if m != 1 else ''} ago"
    if seconds < 86400:
        h = int(seconds // 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = int(seconds // 86400)
    return f"{d} day{'s' if d != 1 else ''} ago"
