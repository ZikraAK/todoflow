"""
Desktop notifications via plyer (cross-platform: Win/Mac/Linux).
Falls back gracefully if plyer isn't installed.
"""
try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False


def notify(title, message, timeout=8):
    """Show a desktop notification. Silent no-op if plyer is unavailable."""
    if not HAS_PLYER:
        print(f"[notify] {title}: {message}")
        return
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="ToDoFlow",
            timeout=timeout,
        )
    except Exception as e:
        print(f"[notify] failed: {e}")


def notify_rollover(count):
    if count == 0:
        return
    notify(
        "Tasks rolled to today",
        f"{count} task{'s' if count > 1 else ''} carried over from yesterday.",
    )


def notify_procrastination(tasks):
    if not tasks:
        return
    sample = tasks[0]['title']
    extra = f" (+{len(tasks)-1} more)" if len(tasks) > 1 else ""
    notify(
        "Procrastination alert",
        f"'{sample}'{extra} has been postponed 3+ times. Time to commit?",
    )


def notify_streak_at_risk(days):
    notify(
        "Your streak is at risk!",
        f"Complete one task today to keep your {days}-day streak alive.",
    )


def notify_suggestion(task, energy_label):
    notify(
        f"{energy_label} energy suggestion",
        f"How about: {task['title']}",
    )
