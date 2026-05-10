"""Modal for creating or editing a task."""
import customtkinter as ctk
from tkinter import messagebox
from datetime import date


class TaskDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, on_save, task=None):
        super().__init__(parent)
        self.db = db
        self.on_save = on_save
        self.task = task  # None = create, dict = edit

        self.title("Edit task" if task else "New task")
        self.geometry("440x560")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_form()
        if task:
            self._populate_from_task()

    def _build_form(self):
        pad = {"padx": 20, "pady": 6}

        ctk.CTkLabel(self, text="Title", anchor="w").pack(fill="x", **pad)
        self.title_entry = ctk.CTkEntry(self, placeholder_text="What needs doing?")
        self.title_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Description (optional)", anchor="w").pack(
            fill="x", **pad
        )
        self.desc_entry = ctk.CTkTextbox(self, height=70)
        self.desc_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Category", anchor="w").pack(fill="x", **pad)
        self.categories = self.db.get_categories()
        cat_names = [c['name'] for c in self.categories] or ['(none)']
        self.cat_var = ctk.StringVar(value=cat_names[0])
        self.cat_menu = ctk.CTkOptionMenu(
            self, values=cat_names, variable=self.cat_var
        )
        self.cat_menu.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Energy required", anchor="w").pack(
            fill="x", **pad
        )
        self.energy_var = ctk.StringVar(value="Medium")
        ctk.CTkSegmentedButton(
            self, values=["High", "Medium", "Low"], variable=self.energy_var,
        ).pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Priority", anchor="w").pack(fill="x", **pad)
        self.priority_var = ctk.StringVar(value="Medium")
        ctk.CTkSegmentedButton(
            self, values=["High", "Medium", "Low"], variable=self.priority_var,
        ).pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Due date (YYYY-MM-DD)", anchor="w").pack(
            fill="x", **pad
        )
        self.date_entry = ctk.CTkEntry(self)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(fill="x", padx=20)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(20, 20))
        ctk.CTkButton(
            btn_row, text="Cancel", command=self.destroy,
            fg_color="gray", hover_color="darkgray",
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text="Save", command=self._save,
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def _populate_from_task(self):
        t = self.task
        self.title_entry.insert(0, t['title'])
        if t.get('description'):
            self.desc_entry.insert("1.0", t['description'])
        if t.get('category_name'):
            self.cat_var.set(t['category_name'])
        self.energy_var.set(t['energy_level'])
        self.priority_var.set(t['priority'])
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, t['due_date'])

    def _save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Please enter a title.",
                                   parent=self)
            return

        try:
            due = self.date_entry.get().strip()
            date.fromisoformat(due)  # validate
        except ValueError:
            messagebox.showwarning(
                "Invalid date", "Use YYYY-MM-DD format.", parent=self,
            )
            return

        cat_id = None
        cat_name = self.cat_var.get()
        for c in self.categories:
            if c['name'] == cat_name:
                cat_id = c['id']
                break

        desc = self.desc_entry.get("1.0", "end").strip()

        if self.task:
            self.db.update_task(
                self.task['id'],
                title=title, description=desc, category_id=cat_id,
                energy_level=self.energy_var.get(),
                priority=self.priority_var.get(),
                due_date=due,
            )
        else:
            self.db.add_task(
                title=title, description=desc, category_id=cat_id,
                energy_level=self.energy_var.get(),
                priority=self.priority_var.get(),
                due_date=due,
            )
        self.on_save()
        self.destroy()
