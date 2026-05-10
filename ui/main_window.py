"""Main application window."""
import customtkinter as ctk
from datetime import date
from logic import energy, streaks, rollover, notifications
from ui.task_dialog import TaskDialog
from ui.stats_window import StatsWindow
from ui.procrastination_dialog import ProcrastinationDialog


class MainWindow(ctk.CTk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("ToDoFlow — your daily momentum")
        self.geometry("760x680")
        self.minsize(640, 560)

        self._build_layout()
        self._run_startup_tasks()
        self._refresh()

    # ---------- layout ----------
    def _build_layout(self):
        # ---- top bar ----
        top = ctk.CTkFrame(self, fg_color="transparent", height=60)
        top.pack(fill="x", padx=20, pady=(20, 8))

        ctk.CTkLabel(
            top, text="Today", font=("", 26, "bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            top, text=date.today().strftime("%A, %b %d"),
            font=("", 13), text_color="#9CA3AF",
        ).pack(side="left", padx=(10, 0), pady=(8, 0))

        ctk.CTkButton(
            top, text="🌓", width=40, command=self._toggle_theme,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            top, text="📊 Stats", width=90, command=self._open_stats,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            top, text="+ New task", width=110, command=self._new_task,
        ).pack(side="right")

        # ---- energy suggestion banner ----
        self.energy_banner = ctk.CTkFrame(self, corner_radius=12, height=80)
        self.energy_banner.pack(fill="x", padx=20, pady=8)
        self.energy_banner.pack_propagate(False)
        self.energy_label = ctk.CTkLabel(
            self.energy_banner, text="", font=("", 14),
        )
        self.energy_label.pack(side="left", padx=20, pady=10)
        self.suggest_btn = ctk.CTkButton(
            self.energy_banner, text="Do this →", width=120,
            command=self._do_suggested,
        )
        self.suggest_btn.pack(side="right", padx=20)

        # ---- streak strip ----
        self.streak_label = ctk.CTkLabel(self, text="", font=("", 13))
        self.streak_label.pack(anchor="w", padx=22, pady=(4, 8))

        # ---- task list (scrollable) ----
        self.task_list = ctk.CTkScrollableFrame(self, corner_radius=12)
        self.task_list.pack(fill="both", expand=True, padx=20, pady=(4, 16))

    # ---------- startup ----------
    def _run_startup_tasks(self):
        # 1. roll overdue tasks
        rolled = rollover.perform_daily_rollover(self.db)
        if rolled:
            notifications.notify_rollover(len(rolled))

        # 2. check procrastinated tasks (after rollover, so counters are fresh)
        procrastinated = rollover.get_procrastinated_alerts(self.db)
        if procrastinated:
            notifications.notify_procrastination(procrastinated)
            # show first one immediately
            self.after(800, lambda: self._handle_procrastinated(procrastinated))

        # 3. streak status notification
        status, msg = streaks.check_streak_status(self.db)
        if status == 'at_risk':
            current = self.db.get_streak()['current_streak']
            notifications.notify_streak_at_risk(current)

    def _handle_procrastinated(self, queue):
        if not queue:
            return
        task = queue[0]
        rest = queue[1:]
        ProcrastinationDialog(
            self, self.db, task,
            on_resolved=lambda: (self._refresh(),
                                  self._handle_procrastinated(rest)),
        )

    # ---------- refresh / render ----------
    def _refresh(self):
        # clear task list
        for w in self.task_list.winfo_children():
            w.destroy()

        today = date.today().isoformat()
        tasks = self.db.get_tasks_for_date(today, include_completed=True)

        # update energy banner
        label, level = energy.current_energy_window()
        suggested = energy.suggest_next_task(self.db, today)
        if suggested:
            self.energy_label.configure(
                text=f"⚡ {label} → {level} energy. "
                     f"Try: \"{suggested['title']}\""
            )
            self.suggest_btn.configure(state="normal")
            self._suggested_id = suggested['id']
        else:
            self.energy_label.configure(
                text=f"⚡ {label} → no pending tasks. Take a breath."
            )
            self.suggest_btn.configure(state="disabled")
            self._suggested_id = None

        # update streak strip
        streak = self.db.get_streak()
        status, msg = streaks.check_streak_status(self.db)
        self.streak_label.configure(
            text=f"🔥 {streak['current_streak']}-day streak  •  "
                 f"🏆 longest {streak['longest_streak']}  •  {msg}"
        )

        # render tasks
        if not tasks:
            ctk.CTkLabel(
                self.task_list,
                text="No tasks for today. Add one to get rolling.",
                font=("", 13), text_color="#9CA3AF",
            ).pack(pady=40)
            return

        for t in tasks:
            self._render_task_row(t)

    def _render_task_row(self, task):
        row = ctk.CTkFrame(self.task_list, corner_radius=10, height=64)
        row.pack(fill="x", padx=8, pady=4)
        row.pack_propagate(False)

        # checkbox
        is_done = task['status'] == 'completed'
        var = ctk.BooleanVar(value=is_done)

        def on_toggle(t=task, v=var):
            if v.get():
                self.db.complete_task(t['id'])
                streaks.update_streak_on_completion(self.db)
            else:
                self.db.uncomplete_task(t['id'])
            self._refresh()

        ctk.CTkCheckBox(
            row, text="", variable=var, command=on_toggle, width=24,
        ).pack(side="left", padx=(14, 8))

        # left: title + meta
        body = ctk.CTkFrame(row, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, pady=8)

        title_text = task['title']
        if is_done:
            title_text = "✓ " + title_text
        title_lbl = ctk.CTkLabel(
            body, text=title_text, font=("", 14, "bold"), anchor="w",
            text_color="#9CA3AF" if is_done else None,
        )
        title_lbl.pack(anchor="w", fill="x")

        meta_parts = []
        if task.get('category_name'):
            meta_parts.append(task['category_name'])
        meta_parts.append(f"⚡ {task['energy_level']}")
        meta_parts.append(f"❗ {task['priority']}")
        if task['rollover_count'] > 0:
            meta_parts.append(f"↻ {task['rollover_count']}× rolled")
        if task['is_procrastinated']:
            meta_parts.append("🐢 procrastinated")
        ctk.CTkLabel(
            body, text="  •  ".join(meta_parts), font=("", 11),
            text_color="#9CA3AF", anchor="w",
        ).pack(anchor="w", fill="x")

        # right: category color dot + edit/delete
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=14)

        if task.get('color_hex'):
            dot = ctk.CTkFrame(
                right, width=12, height=12, corner_radius=6,
                fg_color=task['color_hex'],
            )
            dot.pack(side="left", padx=(0, 12))
            dot.pack_propagate(False)

        ctk.CTkButton(
            right, text="✎", width=30, height=30,
            command=lambda t=task: self._edit_task(t),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            right, text="🗑", width=30, height=30,
            fg_color="#EF4444", hover_color="#DC2626",
            command=lambda t=task: self._delete_task(t),
        ).pack(side="left", padx=2)

    # ---------- actions ----------
    def _new_task(self):
        TaskDialog(self, self.db, on_save=self._refresh)

    def _edit_task(self, task):
        TaskDialog(self, self.db, on_save=self._refresh, task=task)

    def _delete_task(self, task):
        from tkinter import messagebox
        if messagebox.askyesno(
            "Delete task?", f"Delete '{task['title']}'?", parent=self,
        ):
            self.db.delete_task(task['id'])
            self._refresh()

    def _do_suggested(self):
        if self._suggested_id is None:
            return
        self.db.complete_task(self._suggested_id)
        streaks.update_streak_on_completion(self.db)
        self._refresh()

    def _open_stats(self):
        StatsWindow(self, self.db)

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("Light" if current == "Dark" else "Dark")
