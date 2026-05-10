"""Stats / streaks dashboard."""
import customtkinter as ctk
from logic import streaks


class StatsWindow(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db

        self.title("Your momentum")
        self.geometry("520x520")
        self.transient(parent)

        self._build()

    def _build(self):
        streak = self.db.get_streak()

        # --- top: streak cards ---
        card_row = ctk.CTkFrame(self, fg_color="transparent")
        card_row.pack(fill="x", padx=20, pady=(20, 10))

        self._streak_card(card_row, "🔥 Current",
                          f"{streak['current_streak']} days").pack(
            side="left", expand=True, fill="x", padx=(0, 8))
        self._streak_card(card_row, "🏆 Longest",
                          f"{streak['longest_streak']} days").pack(
            side="left", expand=True, fill="x", padx=4)
        self._streak_card(card_row, "💪 Comebacks",
                          str(streak['comeback_count'])).pack(
            side="left", expand=True, fill="x", padx=(8, 0))

        # --- middle: status banner ---
        status, message = streaks.check_streak_status(self.db)
        banner_color = {
            'active':  '#10B981',
            'at_risk': '#F59E0B',
            'broken':  '#6B7280',
        }[status]
        banner = ctk.CTkFrame(self, fg_color=banner_color, corner_radius=10)
        banner.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(
            banner, text=message, text_color="white",
            font=("", 14, "bold"), wraplength=440,
        ).pack(padx=14, pady=12)

        # --- weekly chart ---
        ctk.CTkLabel(
            self, text="Last 7 days", font=("", 16, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 6))

        chart_frame = ctk.CTkFrame(self, corner_radius=10)
        chart_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._draw_bar_chart(chart_frame)

    def _streak_card(self, parent, label, value):
        card = ctk.CTkFrame(parent, corner_radius=10, height=90)
        ctk.CTkLabel(card, text=label, font=("", 12)).pack(pady=(14, 0))
        ctk.CTkLabel(card, text=value, font=("", 22, "bold")).pack(pady=(2, 14))
        return card

    def _draw_bar_chart(self, parent):
        data = streaks.get_weekly_completion_data(self.db)
        max_val = max((c for _, c in data), default=0) or 1

        canvas_holder = ctk.CTkFrame(parent, fg_color="transparent")
        canvas_holder.pack(fill="both", expand=True, padx=20, pady=20)

        bar_row = ctk.CTkFrame(canvas_holder, fg_color="transparent")
        bar_row.pack(fill="both", expand=True)
        bar_row.grid_columnconfigure(tuple(range(7)), weight=1, uniform="b")

        from datetime import date
        for i, (d_iso, count) in enumerate(data):
            col = ctk.CTkFrame(bar_row, fg_color="transparent")
            col.grid(row=0, column=i, sticky="nsew", padx=4)

            # value label on top
            ctk.CTkLabel(col, text=str(count), font=("", 11)).pack()

            # bar (use a frame with proportional height)
            bar_max_h = 220
            h = max(int(bar_max_h * count / max_val), 4)
            spacer = ctk.CTkFrame(col, fg_color="transparent",
                                   height=bar_max_h - h)
            spacer.pack(fill="x")
            spacer.pack_propagate(False)
            bar = ctk.CTkFrame(col, fg_color="#3B82F6",
                                height=h, corner_radius=6)
            bar.pack(fill="x")
            bar.pack_propagate(False)

            # day label
            day_name = date.fromisoformat(d_iso).strftime("%a")
            ctk.CTkLabel(col, text=day_name, font=("", 11)).pack(pady=(4, 0))
