"""
PEPS CoreXY — Control Interface
Sends XY coordinates to an ESP8266 via HTTP JSON.

Dependencies:
    pip install requests

Usage:
    python peps_control.py
"""

import json
import time
import tkinter as tk
from tkinter import messagebox
import requests

# Work area
MAX_X = 400.0
MAX_Y = 300.0

# Color palette
BG = "#0f1117"
SURFACE = "#1a1d27"
BORDER = "#2a2d3e"
ACCENT = "#3b82f6"
CYAN = "#22d3ee"
DANGER = "#ef4444"
SUCCESS = "#22c55e"
WARN = "#f59e0b"
TEXT = "#e2e8f0"
MUTED = "#64748b"


class App(tk.Tk):
    """Main application window for PEPS CoreXY control."""

    def __init__(self):
        """Initialize the app, set up state variables and build the UI."""
        super().__init__()
        self.title("PEPS Control — CoreXY")
        self.configure(bg=BG)
        self.minsize(940, 580)

        self.base_url: str = ""
        self.log_lines: list[str] = []

        self.cur_x = tk.DoubleVar(value=0.0)
        self.cur_y = tk.DoubleVar(value=0.0)

        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=SURFACE, pady=10, padx=16)
        hdr.pack(fill="x", side="top")

        tk.Label(
            hdr, text="⊕  PEPS Control", bg=SURFACE, fg=TEXT, font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        tk.Label(
            hdr, text="  Automated Key Fob Positioning — CoreXY 400×300 mm", bg=SURFACE, fg=MUTED, font=("Segoe UI", 10),
        ).pack(side="left")

        conn = tk.Frame(hdr, bg=SURFACE)
        conn.pack(side="right")

        self.dot = tk.Label(conn, text="●", bg=SURFACE, fg=MUTED, font=("Segoe UI", 14))
        self.dot.pack(side="left", padx=(0, 4))

        self.lbl_status = tk.Label(
            conn, text="Not connected", bg=SURFACE, fg=MUTED, font=("Segoe UI", 10), width=18, anchor="w",
        )
        self.lbl_status.pack(side="left")

        tk.Label(conn, text="IP:", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(8, 2))
        
        self.ent_ip = tk.Entry(
            conn, bg=BORDER, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Cascadia Code", 11), width=16,
        )
        # AQUÍ ESTÁ EL CAMBIO: Ya tiene la IP del ESP8266 por defecto
        self.ent_ip.insert(0, "192.168.4.1")
        self.ent_ip.pack(side="left", ipady=4, padx=(0, 6))

        self.btn_conn = self._btn(conn, "Connect", self._connect, accent=True)
        self.btn_conn.pack(side="left", padx=2)
        self.btn_disc = self._btn(conn, "Disconnect", self._disconnect)
        self.btn_disc.pack(side="left")
        self.btn_disc.config(state="disabled")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(
            left, text="Workspace  (click to move)", bg=BG, fg=MUTED, font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        self.canvas = tk.Canvas(
            left, bg="#0b0d14", highlightthickness=1, highlightbackground=BORDER, cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Button-1>", self._canvas_click)
        self.canvas.bind("<Motion>", self._canvas_hover)

        self.lbl_coord = tk.Label(left, text="X: 0.0  |  Y: 0.0", bg=BG, fg=MUTED, font=("Cascadia Code", 9))
        self.lbl_coord.pack(pady=(4, 0))

        right = tk.Frame(body, bg=BG, width=310)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)
        self._build_sidebar(right)

    def _build_sidebar(self, parent):
        f = self._card(parent, "Current Position")
        row = tk.Frame(f, bg=SURFACE)
        row.pack(fill="x")
        for axis, var in [("X", self.cur_x), ("Y", self.cur_y)]:
            box = tk.Frame(row, bg=BORDER, padx=2, pady=2)
            box.pack(side="left", expand=True, fill="x", padx=4)
            inner = tk.Frame(box, bg=SURFACE, padx=12, pady=8)
            inner.pack(fill="both")
            tk.Label(inner, text=axis, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9, "bold")).pack()
            lbl = tk.Label(inner, textvariable=var, bg=SURFACE, fg=CYAN, font=("Cascadia Code", 20, "bold"))
            lbl.pack()
            tk.Label(inner, text="mm", bg=SURFACE, fg=MUTED, font=("Segoe UI", 8)).pack()

        mf = tk.Frame(parent, bg=SURFACE, padx=10, pady=6)
        mf.pack(fill="x", pady=(0, 8))
        self._build_tab_manual(mf)

        lf = self._card(parent, "HTTP Log")
        log_frame = tk.Frame(lf, bg=SURFACE)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame, height=6, bg="#08090f", fg=MUTED, font=("Cascadia Code", 8), state="disabled", relief="flat", wrap="word", insertbackground=TEXT,
        )
        sb = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.log_text.tag_config("ok", foreground=SUCCESS)
        self.log_text.tag_config("err", foreground=DANGER)
        self.log_text.tag_config("inf", foreground=CYAN)
        self.log_text.tag_config("mut", foreground=MUTED)

        self._btn(lf, "Clear log", lambda: self._clear_log(), w=12).pack(anchor="e", pady=(4, 0))

        estop = tk.Button(
            parent, text="🛑  EMERGENCY STOP", bg=DANGER, fg="white", activebackground="#c53030", font=("Segoe UI", 13, "bold"), relief="flat", cursor="hand2", pady=10, command=self._estop,
        )
        estop.pack(fill="x", pady=(4, 0))

    def _build_tab_manual(self, p):
        row = tk.Frame(p, bg=SURFACE)
        row.pack(fill="x", pady=(0, 8))
        for lbl, attr, mx in [("X (mm)", "ent_x", MAX_X), ("Y (mm)", "ent_y", MAX_Y)]:
            col = tk.Frame(row, bg=SURFACE)
            col.pack(side="left", expand=True, fill="x", padx=(0, 6))
            tk.Label(col, text=lbl, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            e = tk.Entry(col, bg=BORDER, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Cascadia Code", 13), width=8)
            e.insert(0, "0")
            e.pack(fill="x", ipady=5)
            setattr(self, attr, e)

        self.btn_send = self._btn(p, "▶  Send Coordinates", self._send_manual, accent=True, full=True)
        self.btn_send.pack(fill="x", pady=(0, 4))
        self.btn_send.config(state="disabled")

        self.btn_home = self._btn(p, "⌂  Home (0, 0)", self._go_home, full=True)
        self.btn_home.pack(fill="x")
        self.btn_home.config(state="disabled")

        tk.Label(p, text="QUICK POSITIONS", bg=SURFACE, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(12, 4))

        PRESETS = [
            ("Home", 0, 0), ("Center", 200, 150), ("Front", 200, 50),
            ("Back", 200, 250), ("Left", 50, 150), ("Right", 350, 150),
            ("Fwd-L", 50, 50), ("Fwd-R", 350, 50), ("Bwd-L", 50, 250),
        ]
        grid = tk.Frame(p, bg=SURFACE)
        grid.pack(fill="x")
        for i, (name, x, y) in enumerate(PRESETS):
            b = tk.Button(
                grid, text=f"{name}\n{x},{y}", bg=BORDER, fg=TEXT, activebackground=ACCENT, font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", pady=4, command=lambda x=x, y=y: self._send_xy(x, y),
            )
            b.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)

    def _connect(self):
        ip = self.ent_ip.get().strip()
        if not ip:
            messagebox.showerror("Error", "Enter the ESP8266 IP address.")
            return
        try:
            r = requests.get(f"http://{ip}/ping", timeout=3)
            if r.status_code != 200:
                raise ConnectionError(f"HTTP {r.status_code}")
            self.base_url = f"http://{ip}"
            self._set_connected(True, ip)
            self._log(f"Connected to {ip}", "ok")
        except requests.RequestException as e:
            self._log(f"Connection error: {e}", "err")
            messagebox.showerror("Connection Error", str(e))

    def _disconnect(self):
        self.base_url = ""
        self._set_connected(False)
        self._log("Disconnected.", "mut")

    def _set_connected(self, yes: bool, ip: str = ""):
        color = SUCCESS if yes else MUTED
        self.dot.config(fg=color)
        self.lbl_status.config(text=f"Connected — {ip}" if yes else "Not connected", fg=color)
        state = "normal" if yes else "disabled"
        for w in [self.btn_send, self.btn_home]:
            w.config(state=state)
        self.btn_conn.config(state="disabled" if yes else "normal")
        self.btn_disc.config(state="normal" if yes else "disabled")

    def _send_json(self, data: dict):
        if not self.base_url:
            self._log("Not connected.", "err")
            return False
        try:
            endpoint = "/cmd" if "cmd" in data else "/move"
            r = requests.post(f"{self.base_url}{endpoint}", json=data, timeout=120)
            self._log(f"→ {json.dumps(data)}", "ok")
            if r.text.strip():
                self._log(f"← {r.text.strip()}", "mut")
            return r.ok
        except requests.RequestException as e:
            self._log(f"HTTP error: {e}", "err")
            return False

    def _send_xy(self, x: float, y: float):
        x = max(0.0, min(MAX_X, float(x)))
        y = max(0.0, min(MAX_Y, float(y)))
        ok = self._send_json({"x": round(x, 2), "y": round(y, 2)})
        if ok:
            self.cur_x.set(round(x, 1))
            self.cur_y.set(round(y, 1))
            self._draw()

    def _send_manual(self):
        try:
            x = float(self.ent_x.get())
            y = float(self.ent_y.get())
        except ValueError:
            messagebox.showerror("Error", "Enter numeric values for X and Y.")
            return
        self._send_xy(x, y)

    def _go_home(self):
        self._send_xy(0, 0)

    def _estop(self):
        self._send_json({"cmd": "ESTOP"})
        self._log("⚠ EMERGENCY STOP sent", "err")

    def _mm_to_canvas(self, x, y):
        W = self.canvas.winfo_width()
        H = self.canvas.winfo_height()
        cx = (x / MAX_X) * W
        cy = H - (y / MAX_Y) * H
        return cx, cy

    def _canvas_to_mm(self, cx, cy):
        W = self.canvas.winfo_width()
        H = self.canvas.winfo_height()
        x = (cx / W) * MAX_X
        y = ((H - cy) / H) * MAX_Y
        return x, y

    def _draw(self):
        c = self.canvas
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 2 or H < 2: return
        c.delete("all")

        for xi in range(0, int(MAX_X) + 1, 50):
            cx, _ = self._mm_to_canvas(xi, 0)
            c.create_line(cx, 0, cx, H, fill="#1c1f2e", width=1)
            c.create_text(cx, H - 8, text=str(xi), fill="#2a2d3e", font=("Segoe UI", 7))
        for yi in range(0, int(MAX_Y) + 1, 50):
            _, cy = self._mm_to_canvas(0, yi)
            c.create_line(0, cy, W, cy, fill="#1c1f2e", width=1)
            c.create_text(20, cy, text=str(yi), fill="#2a2d3e", font=("Segoe UI", 7))

        px, py = self.cur_x.get(), self.cur_y.get()
        cx, cy = self._mm_to_canvas(px, py)

        c.create_line(cx, 0, cx, H, fill="#0f3344", width=1, dash=(3, 3))
        c.create_line(0, cy, W, cy, fill="#0f3344", width=1, dash=(3, 3))

        c.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, fill="#0a2a33", outline=CYAN, width=1)
        c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=CYAN, outline="")
        c.create_text(cx + 14, cy - 10, text=f"({px:.1f}, {py:.1f})", fill=CYAN, font=("Cascadia Code", 8, "bold"), anchor="w")

        ox, oy = self._mm_to_canvas(0, 0)
        c.create_oval(ox - 4, oy - 4, ox + 4, oy + 4, fill=BORDER, outline="")
        c.create_text(ox + 8, oy - 8, text="origin", fill=BORDER, font=("Segoe UI", 7), anchor="w")

    def _canvas_click(self, event):
        x, y = self._canvas_to_mm(event.x, event.y)
        x = max(0.0, min(MAX_X, x))
        y = max(0.0, min(MAX_Y, y))
        self.ent_x.delete(0, "end")
        self.ent_x.insert(0, f"{x:.1f}")
        self.ent_y.delete(0, "end")
        self.ent_y.insert(0, f"{y:.1f}")
        self._send_xy(x, y)

    def _canvas_hover(self, event):
        x, y = self._canvas_to_mm(event.x, event.y)
        x = max(0.0, min(MAX_X, x))
        y = max(0.0, min(MAX_Y, y))
        self.lbl_coord.config(text=f"X: {x:.1f}  |  Y: {y:.1f}")

    def _log(self, msg: str, tag: str = "inf"):
        ts = time.strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _card(self, parent, title: str):
        outer = tk.Frame(parent, bg=BORDER, pady=1, padx=1)
        outer.pack(fill="x", pady=(0, 8))
        inner = tk.Frame(outer, bg=SURFACE, padx=10, pady=8)
        inner.pack(fill="both")
        tk.Label(inner, text=title.upper(), bg=SURFACE, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))
        return inner

    def _btn(self, parent, text, cmd, accent=False, full=False, w=None):
        bg = ACCENT if accent else BORDER
        fg = "white" if accent else TEXT
        kw = {"width": w} if w else {}
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=ACCENT, font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=8, pady=5, **kw)

if __name__ == "__main__":
    app = App()
    app.mainloop()
