"""
ToDoFlow — a to-do app with auto-rollover, energy-based scheduling,
and a streak system.

Run: python main.py
"""
import customtkinter as ctk
from database import Database
from ui.main_window import MainWindow


def main():
    # Theme defaults — user can toggle from the top bar
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    db = Database()
    app = MainWindow(db)
    try:
        app.mainloop()
    finally:
        db.close()


if __name__ == "__main__":
    main()
