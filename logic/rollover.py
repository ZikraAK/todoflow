"""
Auto-rollover with guilt tracking.

When app starts, any pending task with due_date < today gets rolled forward
to today. Each rollover increments rollover_count. Once a task hits 3+
rollovers, it's flagged as procrastinated and the UI prompts the user to
commit, break it down, or delete.
"""
from datetime import date


def perform_daily_rollover(db):
    """
    Roll all overdue pending tasks forward to today.
    Returns: list of task dicts that were rolled over.
    """
    today = date.today().isoformat()
    overdue = db.get_pending_tasks_before(today)
    rolled = []
    for task in overdue:
        db.log_rollover(task['id'], task['due_date'], today)
        # re-fetch to get updated counters
        updated = db.get_task(task['id'])
        rolled.append(updated)
    return rolled


def get_procrastinated_alerts(db):
    """Return tasks that have crossed the 3-rollover threshold."""
    return db.get_procrastinated_tasks()


def commit_to_task(db, task_id):
    """User commits — reset procrastination flag but keep rollover history."""
    db.update_task(task_id, is_procrastinated=0)


def break_down_task(db, parent_task_id, subtask_titles, today_iso):
    """
    Split a procrastinated task into smaller subtasks. The original is
    marked deleted; new tasks inherit category/energy/priority.
    """
    parent = db.get_task(parent_task_id)
    if not parent:
        return []
    new_ids = []
    for title in subtask_titles:
        new_id = db.add_task(
            title=title,
            description=f"(Broken down from: {parent['title']})",
            category_id=parent['category_id'],
            energy_level=parent['energy_level'],
            priority=parent['priority'],
            due_date=today_iso,
        )
        new_ids.append(new_id)
    db.delete_task(parent_task_id)
    return new_ids
