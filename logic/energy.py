"""
Energy-based scheduling.

Maps the time of day to the energy level the user likely has, then
recommends tasks that match. The user's natural rhythm:

  - Morning   (5:00 - 11:59)  → High energy   (deep work, hard problems)
  - Afternoon (12:00 - 16:59) → Medium energy (meetings, admin)
  - Evening   (17:00 - 21:59) → Low energy    (planning, light tasks)
  - Night     (22:00 - 4:59)  → Low energy    (wind down, reading)
"""
from datetime import datetime


def current_energy_window():
    """Return ('label', recommended_level) for right now."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Morning", "High"
    if 12 <= hour < 17:
        return "Afternoon", "Medium"
    if 17 <= hour < 22:
        return "Evening", "Low"
    return "Night", "Low"


def suggest_next_task(db, today_iso):
    """
    Pick the best task to do RIGHT NOW based on current energy + priority.
    Returns one task dict or None.
    """
    label, recommended = current_energy_window()
    tasks = db.get_tasks_for_date(today_iso, include_completed=False)
    if not tasks:
        return None

    # First pass: exact energy match, sorted by priority
    matches = [t for t in tasks if t['energy_level'] == recommended]
    if matches:
        return matches[0]  # already priority-sorted by query

    # Fallback: highest-priority pending task regardless
    return tasks[0]


def group_by_energy(tasks):
    """Bucket tasks by energy level for the suggestion panel."""
    buckets = {'High': [], 'Medium': [], 'Low': []}
    for t in tasks:
        if t['status'] == 'pending':
            buckets[t['energy_level']].append(t)
    return buckets
