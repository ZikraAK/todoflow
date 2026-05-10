"""
Streak & momentum system.

Rules:
  - A "streak day" = at least 1 task completed that day.
  - Streak continues if user completes ≥1 task today and last_active_date
    was yesterday.
  - Streak breaks if last_active_date is older than yesterday.
  - "Comeback" = user starts a new streak after a break of 2+ days; we
    increment comeback_count for the achievement system.
"""
from datetime import date, timedelta


def update_streak_on_completion(db):
    """Call this whenever the user completes a task."""
    streak = db.get_streak()
    today = date.today()
    today_iso = today.isoformat()

    last_iso = streak['last_active_date']
    current = streak['current_streak']
    longest = streak['longest_streak']
    comebacks = streak['comeback_count']

    if last_iso == today_iso:
        return streak  # already counted today

    if last_iso is None:
        # first ever completion
        current = 1
    else:
        last = date.fromisoformat(last_iso)
        gap = (today - last).days
        if gap == 1:
            current += 1
        elif gap >= 2:
            # streak broken; this is a comeback
            current = 1
            if gap >= 3:
                comebacks += 1

    longest = max(longest, current)
    db.update_streak(current, longest, today_iso, comebacks)
    return db.get_streak()


def check_streak_status(db):
    """Called on app open — returns ('active'|'at_risk'|'broken', message)."""
    streak = db.get_streak()
    if streak['current_streak'] == 0 or streak['last_active_date'] is None:
        return 'broken', "No active streak. Complete a task to start one!"

    today = date.today()
    last = date.fromisoformat(streak['last_active_date'])
    gap = (today - last).days

    if gap == 0:
        return 'active', f"🔥 {streak['current_streak']}-day streak active!"
    if gap == 1:
        return 'at_risk', (
            f"⚠️ Your {streak['current_streak']}-day streak is at risk! "
            f"Complete a task today to keep it alive."
        )
    # streak technically broken; UI confirms reset on next completion
    return 'broken', (
        f"💔 Your {streak['current_streak']}-day streak ended. "
        f"Start a comeback today!"
    )


def get_weekly_completion_data(db):
    """Returns last 7 days as [(date_iso, completions), ...] oldest first."""
    today = date.today()
    data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_iso = d.isoformat()
        count = db.get_completions_for_date(d_iso)
        data.append((d_iso, count))
    return data
