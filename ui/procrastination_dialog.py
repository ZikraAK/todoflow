"""
Triggered when a task hits 3+ rollovers.
User can: commit (just clear flag), break it down into subtasks, or delete.
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import date
from logic import rollover


class ProcrastinationDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, task, on_resolved):
        super().__init__(parent)
        self.db = db
        self.task = task
        self.on_resolved = on_resolved

        self.title("Procrastination check-in")
        self.geometry("480x440")
        self.transient(parent)
        self.grab_set()

        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="🐢", font=("", 40),
        ).pack(pady=(20, 0))
        ctk.CTkLabel(
            self, text="This one keeps getting away from you",
            font=("", 18, "bold"),
        ).pack(pady=(4, 0))

        info = ctk.CTkFrame(self, corner_radius=10)
        info.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(
            info, text=self.task['title'], font=("", 15, "bold"),
            wraplength=420,
        ).pack(padx=16, pady=(14, 4))
        ctk.CTkLabel(
            info,
            text=f"Postponed {self.task['rollover_count']} times since "
                 f"{self.task['original_date']}",
            font=("", 12), text_color="#9CA3AF",
        ).pack(padx=16, pady=(0, 14))

        ctk.CTkLabel(
            self, text="What do you want to do?", font=("", 13),
        ).pack(pady=(0, 10))

        ctk.CTkButton(
            self, text="✓  Commit — I'll do it today",
            command=self._commit, height=42,
        ).pack(fill="x", padx=20, pady=4)

        ctk.CTkButton(
            self, text="✂  Break it down into smaller tasks",
            command=self._break_down, height=42,
            fg_color="#8B5CF6", hover_color="#7C3AED",
        ).pack(fill="x", padx=20, pady=4)

        ctk.CTkButton(
            self, text="🗑  Delete — I'm not doing this",
            command=self._delete, height=42,
            fg_color="#EF4444", hover_color="#DC2626",
        ).pack(fill="x", padx=20, pady=4)

    def _commit(self):
        rollover.commit_to_task(self.db, self.task['id'])
        self.on_resolved()
        self.destroy()

    def _break_down(self):
        BreakDownDialog(self, self.db, self.task, self._after_break)

    def _after_break(self):
        self.on_resolved()
        self.destroy()

    def _delete(self):
        if messagebox.askyesno(
            "Delete task?",
            f"Permanently delete '{self.task['title']}'?",
            parent=self,
        ):
            self.db.delete_task(self.task['id'])
            self.on_resolved()
            self.destroy()


class BreakDownDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, task, on_done):
        super().__init__(parent)
        self.db = db
        self.task = task
        self.on_done = on_done

        self.title("Break it down")
        self.geometry("440x420")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self, text=f"Splitting: {task['title']}", font=("", 14, "bold"),
            wraplength=400,
        ).pack(padx=20, pady=(20, 8))
        ctk.CTkLabel(
            self,
            text="Enter 2–5 smaller subtasks (one per line):",
            font=("", 12),
        ).pack(padx=20, pady=(0, 8))

        self.text = ctk.CTkTextbox(self, height=200)
        self.text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.text.insert("1.0", "")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(
            btn_row, text="Cancel", command=self.destroy,
            fg_color="gray", hover_color="darkgray",
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text="Create subtasks", command=self._create,
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def _create(self):
        raw = self.text.get("1.0", "end").strip()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not (2 <= len(lines) <= 5):
            messagebox.showwarning(
                "Need 2–5 subtasks", "Please enter between 2 and 5 lines.",
                parent=self,
            )
            return
        rollover.break_down_task(
            self.db, self.task['id'], lines, date.today().isoformat(),
        )
        self.on_done()
        self.destroy()
