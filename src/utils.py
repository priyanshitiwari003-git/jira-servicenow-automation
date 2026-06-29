"""Utility functions for the agent."""

import re
from typing import List, Optional
from datetime import datetime, timedelta


def sanitize_name(name: str) -> str:
    """Sanitize a string to be a valid ServiceNow update set name.

    Args:
        name: Original name

    Returns:
        Sanitized name
    """
    # Remove special characters, keep alphanumeric and underscores
    sanitized = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Convert to lowercase
    sanitized = sanitized.lower()
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


def generate_parent_deployment_name(sprint_name: Optional[str] = None) -> str:
    """Generate a parent deployment update set name.

    Naming format: DEV-Q{quarter}{year}-{MONTH}-WEEK{week_of_month}
    Example: DEV-Q22026-JUNE-WEEK2

    Args:
        sprint_name: Jira sprint name (unused, kept for compatibility)

    Returns:
        Parent update set name
    """
    now = datetime.now()
    quarter = ((now.month - 1) // 3) + 1
    year = now.year
    month_name = now.strftime('%B').upper()
    week_of_month = ((now.day - 1) // 7) + 1

    return f"DEV-Q{quarter}{year}-{month_name}-WEEK{week_of_month}"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def is_thursday() -> bool:
    """Check if today is Thursday.

    Returns:
        True if today is Thursday (weekday 3)
    """
    return datetime.now().weekday() == 3


def is_time_within_window(target_hour: int, target_minute: int, window_minutes: int = 5) -> bool:
    """Check if current time is within a window of target time.

    Args:
        target_hour: Target hour (0-23)
        target_minute: Target minute (0-59)
        window_minutes: Window tolerance in minutes

    Returns:
        True if within window
    """
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    delta = abs((now - target_time).total_seconds()) / 60
    return delta <= window_minutes
