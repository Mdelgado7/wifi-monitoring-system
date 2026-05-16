import tkinter as tk
from tkinter import ttk, messagebox, filedialog  # Added filedialog
from PIL import Image, ImageTk
from picamera2 import Picamera2
import subprocess, os, math, json
from datetime import datetime

class DashboardMapper:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='#121212')
        self.root.config(cursor="none")

        # Directory Setup
        self.save_dir = os.path.expanduser("~/wifi_survey/captures")
        self.export_dir = os.path.expanduser("~/wifi_survey/exports")
        for d in [self.save_dir, self.export_dir]: os.makedirs(d, exist_ok=True)

        # --- STATE LOGIC & DEFAULTS ---
        self.data_points = []
        self.room_outline = []
        self.layout_locked = False
        self.tk_img = None
        self.wall_color = "#00ffff"

        # User Adjustable Options (Defaults)
        self.scan_interval = 5000
        self.grid_size = 20
        self.a_threshold = -55

        try:
            self.picam2 = Picamera2()
            self.picam2.start()
            self.cam_ok = True
        except: self.cam_ok = False

        # --- MAIN LAYOUT ---
        self.canvas = tk.Canvas(root, width=360, height=320, bg="#0a0a0a", highlightthickness=0)
        self.canvas.place(x=0, y=0)

        self.panel = tk.Frame(root, width=120, height=320, bg="#1e1e1e")
        self.panel.place(x=360, y=0)
        self.panel.pack_propagate(False)

        # 1. HEADER
        self.mode_indicator = tk.Label(self.panel, text="MODE: DRAW", fg="#00ff00", bg="#252525", font=("Arial", 9, "bold"), pady=4)
        self.mode_indicator.pack(fill="x")

        # 2. TABS
        self.tab_control = ttk.Notebook(self.panel)
        self.tab_live = tk.Frame(self.tab_control, bg="#1e1e1e")
        self.tab_log = tk.Frame(self.tab_control, bg="#1e1e1e")
        self.tab_save = tk.Frame(self.tab_control, bg="#1e1e1e")

        self.tab_control.add(self.tab_live, text='LIVE')
        self.tab_control.add(self.tab_log, text='LOG')
        self.tab_control.add(self.tab_save, text='SAVE')
        self.tab_control.pack(expand=True, fill="both")

        # --- TAB: LIVE ---
        self.btn_lock = tk.Button(self.tab_live, text="LOCK ROOM", command=self.lock_layout,
                                   bg="#ff0000", fg="white", relief="flat", font=("Arial", 8, "bold"), bd=0)
        self.btn_lock.pack(fill="x", padx=2, pady=2)

        self.preview_label = tk.Label(self.tab_live, bg="#000", width=116, height=60)
        self.preview_label.pack(fill="x", pady=(0, 2))

        # Signal Metrics
        self.sig_val = tk.Label(self.tab_live, text="SIG: -- dBm", fg="#00ff00", bg="#1e1e1e", font=("Courier", 9, "bold"))
        self.sig_val.pack(anchor="w", padx=4)
        self.qlty_val = tk.Label(self.tab_live, text="QLTY: --/70", fg="#00ffff", bg="#1e1e1e", font=("Courier", 9, "bold"))
        self.qlty_val.pack(anchor="w", padx=4)

        # Point Counters
        self.stat_pts = tk.Label(self.tab_live, text="PTS: 0", fg="#fff", bg="#1e1e1e", font=("Courier", 8, "bold"))
        self.stat_pts.pack(anchor="w", padx=4)
        self.stat_range = tk.Label(self.tab_live, text="RANGE: --", fg="#888", bg="#1e1e1e", font=("Courier", 8))
        self.stat_range.pack(anchor="w", padx=4)

        # Analysis Box
        self.analysis_box = tk.Frame(self.tab_live, bg="#2a2a2a", pady=4)
        self.analysis_box.pack(fill="x", pady=5)
        self.stat_grade = tk.Label(self.analysis_box, text="GRADE: -", fg="#00ff00", bg="#2a2a2a", font=("Arial", 11, "bold"))
        self.stat_grade.pack()
        self.stat_avg = tk.Label(self.analysis_box, text="AVG: -- dBm", fg="#aaa", bg="#2a2a2a", font=("Arial", 8))
        self.stat_avg.pack()

        # Status Key
        self.status_key = tk.Frame(self.analysis_box, bg="#2a2a2a")
        self.status_key.pack(pady=(2, 0))
        k_cfg = {"bg": "#2a2a2a", "font": ("Arial", 7, "bold")}
        tk.Label(self.status_key, text="■", fg="#00ff00", **k_cfg).pack(side="left")
        tk.Label(self.status_key, text="G", fg="#eee", **k_cfg).pack(side="left", padx=(0, 4))
        tk.Label(self.status_key, text="■", fg="#ffff00", **k_cfg).pack(side="left")
        tk.Label(self.status_key, text="M", fg="#eee", **k_cfg).pack(side="left", padx=(0, 4))
        tk.Label(self.status_key, text="■", fg="#ff0000", **k_cfg).pack(side="left")
        tk.Label(self.status_key, text="P", fg="#eee", **k_cfg).pack(side="left")

        self.ssid_val = tk.Label(self.tab_live, text="ID: SCANNING...", fg="#666", bg="#1e1e1e",
                                  font=("Courier", 7, "italic"), wraplength=110, justify="center")
        self.ssid_val.pack(side="bottom", fill="x", pady=5)

        # --- TAB: LOG ---
        self.history_list = tk.Text(self.tab_log, bg="#0a0a0a", fg="#00ff00", font=("Courier", 7), state="disabled", borderwidth=0)
        self.history_list.pack(expand=True, fill="both")

        # --- TAB: SAVE ---
        self.save_menu = tk.Frame(self.tab_save, bg="#1e1e1e")
        self.save_menu.pack(expand=True, fill="both", padx=5, pady=5)

        tk.Button(self.save_menu, text="SAVE MAP", command=self.export_map, bg="#00ff00", fg="#000", relief="flat", font=("Arial", 8, "bold")).pack(fill="x", pady=2)
        tk.Button(self.save_menu, text="LOAD PREV", command=self.load_session, bg="#333", fg="#fff", relief="flat", font=("Arial", 8)).pack(fill="x", pady=2)
        tk.Button(self.save_menu, text="OPTIONS", command=self.show_options, bg="#333", fg="#fff", relief="flat", font=("Arial", 8)).pack(fill="x", pady=2)
        tk.Button(self.save_menu, text="WIPE DATA", command=self.confirm_reset, bg="#442222", fg="#ff4444", relief="flat", font=("Arial", 8, "bold")).pack(side="bottom", fill="x", pady=5)

        self.canvas_msg = self.canvas.create_text(180, 160, text="TAP TO DRAW", fill="#444", font=("Arial", 10, "bold"), tags="instruction")
        self.canvas.bind("<Button-1>", self.on_tap)
        self.update_loop()

    # --- SAVE / LOAD SYSTEM ---
    def export_map(self):
        if not self.data_points: return
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. Save PostScript image for external viewing
        ps_fn = f"{self.export_dir}/map_{timestamp}.ps"
        self.canvas.postscript(file=ps_fn, colormode='color')

        # 2. Save Raw Data (JSON) for loading back into this app
        data_fn = f"{self.export_dir}/survey_{timestamp}.json"
        save_data = {
            "room_outline": self.room_outline,
            "data_points": self.data_points,
            "timestamp": timestamp
        }
        with open(data_fn, "w") as f:
            json.dump(save_data, f)

        messagebox.showinfo("Export", "Visual and Data Saved Successfully")

    def load_session(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.export_dir,
            title="Select Survey Session",
            filetypes=(("JSON files", "*.json"), ("all files", "*.*"))
        )
        if not file_path: return

        try:
            with open(file_path, "r") as f:
                loaded = json.load(f)

            self.reset_map() # Clear current

            # Reconstruct Room Outline
            self.room_outline = [tuple(p) for p in loaded["room_outline"]]
            if self.room_outline:
                self.layout_locked = True
                self.mode_indicator.config(text="MODE: SCAN", bg="#004400")
                self.btn_lock.config(text="UNLOCK", bg="#333")
                self.canvas.delete("instruction")
                self.canvas.create_polygon(self.room_outline, outline=self.wall_color, fill="#111", width=2, tags="bg_room")

            # Reconstruct Data Points
            self.data_points = loaded["data_points"]
            for i, pt in enumerate(self.data_points):
                x, y, dbm = pt
                label = chr(i % 26 + 65)
                self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="white", tags="pt")
                self.canvas.create_text(x, y-12, text=label, fill="white", font=("Arial", 10, "bold"), tags="pt")

            # Update UI Stats and Heatmap
            self.stat_pts.config(text=f"PTS: {len(self.data_points)}")
            if len(self.data_points) > 0:
                last_label = chr((len(self.data_points)-1) % 26 + 65)
                self.stat_range.config(text=f"RANGE: A → {last_label}")

            self.redraw_heatmap()
            self.run_analysis()
            messagebox.showinfo("Load", "Session Loaded Successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session: {e}")

    # --- OPTIONS & SLIDERS ---
    def show_options(self):
        opt_win = tk.Toplevel(self.root)
        opt_win.geometry("220x300+40+40")
        opt_win.configure(bg="#222", highlightbackground="#00ff00", highlightthickness=1)
        opt_win.title("OPTS")
        opt_win.attributes('-topmost', True)

        l_cfg = {"fg": "#00ff00", "bg": "#222", "font": ("Arial", 8, "bold")}
        s_cfg = {"fg": "#888", "bg": "#222", "font": ("Arial", 7)}

        tk.Label(opt_win, text="SCAN SPEED", **l_cfg).pack(pady=(10, 0))
        self.rate_map = {0: 500, 1: 2000, 2: 5000}
        s1 = tk.Scale(opt_win, from_=0, to=2, orient="horizontal", bg="#222", fg="white",
                      highlightthickness=0, troughcolor="#444", showvalue=0,
                      command=lambda v: self.set_opt("rate", v))
        s1.set(next((k for k, v in self.rate_map.items() if v == self.scan_interval), 1))
        s1.pack(fill="x", padx=20)

        f1 = tk.Frame(opt_win, bg="#222")
        f1.pack(fill="x", padx=20)
        tk.Label(f1, text="FAST", **s_cfg).pack(side="left")
        tk.Label(f1, text="SLOW", **s_cfg).pack(side="right")
        tk.Label(f1, text="MED", **s_cfg).pack()

        tk.Label(opt_win, text="HEATMAP DETAIL", **l_cfg).pack(pady=(15, 0))
        self.res_map = {0: 10, 1: 20, 2: 40}
        s2 = tk.Scale(opt_win, from_=0, to=2, orient="horizontal", bg="#222", fg="white",
                      highlightthickness=0, troughcolor="#444", showvalue=0,
                      command=lambda v: self.set_opt("res", v))
        s2.set(next((k for k, v in self.res_map.items() if v == self.grid_size), 1))
        s2.pack(fill="x", padx=20)

        f2 = tk.Frame(opt_win, bg="#222")
        f2.pack(fill="x", padx=20)
        tk.Label(f2, text="HIGH", **s_cfg).pack(side="left")
        tk.Label(f2, text="LOW", **s_cfg).pack(side="right")
        tk.Label(f2, text="STD", **s_cfg).pack()

        tk.Label(opt_win, text="GRADE STRICTNESS", **l_cfg).pack(pady=(15, 0))
        self.sens_map = {0: -45, 1: -55, 2: -65}
        s3 = tk.Scale(opt_win, from_=0, to=2, orient="horizontal", bg="#222", fg="white",
                      highlightthickness=0, troughcolor="#444", showvalue=0,
                      command=lambda v: self.set_opt("sens", v))
        s3.set(next((k for k, v in self.sens_map.items() if v == self.a_threshold), 1))
        s3.pack(fill="x", padx=20)

        f3 = tk.Frame(opt_win, bg="#222")
        f3.pack(fill="x", padx=20)
        tk.Label(f3, text="ELITE", **s_cfg).pack(side="left")
        tk.Label(f3, text="EASY", **s_cfg).pack(side="right")
        tk.Label(f3, text="OFFICE", **s_cfg).pack()

        tk.Button(opt_win, text="APPLY & DONE", command=opt_win.destroy, bg="#00ff00",
                  fg="black", relief="flat", font=("Arial", 8, "bold")).pack(pady=20)

    def set_opt(self, target, val):
        v = int(val)
        if target == "rate": self.scan_interval = self.rate_map[v]
        elif target == "res":
            self.grid_size = self.res_map[v]
            self.redraw_heatmap()
        elif target == "sens":
            self.a_threshold = self.sens_map[v]
            self.run_analysis()

    # --- CORE LOGIC ---
    def update_loop(self):
        try:
            res = subprocess.check_output("iwconfig wlan0", shell=True).decode()
            if 'ESSID:"' in res:
                ssid = res.split('ESSID:"')[1].split('"')[0]
                self.ssid_val.config(text=f"ID: {ssid}")
            if 'Signal level=' in res:
                dbm = int(res.split("level=")[1].split(" ")[0])
                self.sig_val.config(text=f"SIG: {dbm} dBm", fg="#00ff00" if dbm > -60 else "#ff4444")
            if 'Link Quality=' in res:
                qlty = res.split("Quality=")[1].split(" ")[0]
                self.qlty_val.config(text=f"QLTY: {qlty}")
        except: pass
        self.root.after(self.scan_interval, self.update_loop)

    def run_analysis(self):
        if not self.data_points: return
        dbms = [p[2] for p in self.data_points]
        avg = sum(dbms) / len(dbms)
        self.stat_avg.config(text=f"AVG: {avg:.1f} dBm")

        if avg > self.a_threshold: grade, color = "A+", "#00ff00"
        elif avg > self.a_threshold - 10: grade, color = "B", "#aaff00"
        elif avg > self.a_threshold - 20: grade, color = "C", "#ffff00"
        else: grade, color = "F", "#ff0000"

        self.stat_grade.config(text=f"GRADE: {grade}", fg=color)

    def redraw_heatmap(self):
        if len(self.data_points) < 2: return
        self.canvas.delete("heat")
        gs = self.grid_size
        for x in range(0, 360, gs):
            for y in range(0, 320, gs):
                ws, tw = 0, 0
                for px, py, pdbm in self.data_points:
                    dist = math.sqrt((x-px)**2 + (y-py)**2)
                    weight = 1 / (max(dist, 1)**1.5)
                    ws += pdbm * weight
                    tw += weight
                avg = ws / tw
                color = "#00ff00" if avg > -50 else "#ffff00" if avg > -70 else "#ff0000"
                self.canvas.create_rectangle(x, y, x+gs, y+gs, fill=color, outline="", tags="heat")
        self.canvas.tag_lower("heat"); self.canvas.tag_lower("bg_room"); self.canvas.tag_raise("pt")

    def confirm_reset(self):
        if messagebox.askyesno("Confirm", "Wipe all current survey data?"):
            self.reset_map()

    def lock_layout(self):
        if not self.layout_locked:
            if len(self.room_outline) < 3: return
            self.layout_locked = True
            self.mode_indicator.config(text="MODE: SCAN", bg="#004400")
            self.btn_lock.config(text="UNLOCK", bg="#333")
            self.canvas.delete("instruction")
            self.canvas.create_polygon(self.room_outline, outline=self.wall_color, fill="#111", width=2, tags="bg_room")
        else:
            self.layout_locked = False
            self.mode_indicator.config(text="MODE: DRAW", bg="#252525")
            self.btn_lock.config(text="LOCK ROOM", bg="#ff0000")
            self.reset_map()

    def on_tap(self, event):
        if event.x < 25 and event.y < 25: self.root.destroy()
        if event.x > 360: return
        if not self.layout_locked:
            self.room_outline.append((event.x, event.y))
            self.canvas.create_oval(event.x-3, event.y-3, event.x+3, event.y+3, fill=self.wall_color, tags="wall")
            if len(self.room_outline) > 1:
                p1 = self.room_outline[-2]
                self.canvas.create_line(p1[0], p1[1], event.x, event.y, fill=self.wall_color, tags="wall")
        else:
            self.perform_scan(event.x, event.y)

    def perform_scan(self, x, y):
        try:
            res = subprocess.check_output("iwconfig wlan0 | grep 'Signal level'", shell=True).decode()
            dbm = int(res.split("level=")[1].split(" ")[0])
        except: dbm = -100

        count = len(self.data_points)
        label = chr(count % 26 + 65)
        self.data_points.append((x, y, dbm))

        self.stat_pts.config(text=f"PTS: {len(self.data_points)}")
        if len(self.data_points) >= 2:
            self.stat_range.config(text=f"RANGE: A → {label}")
        else:
            self.stat_range.config(text=f"RANGE: {label}")

        self.history_list.config(state="normal")
        self.history_list.insert("1.0", f"{label}:{dbm}dBm @ {datetime.now().strftime('%H:%M')}\n")
        self.history_list.config(state="disabled")

        if self.cam_ok:
            self.picam2.capture_file(f"{self.save_dir}/pt_{label}.jpg")
            img = Image.open(f"{self.save_dir}/pt_{label}.jpg").resize((116, 60))
            self.tk_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.tk_img)

        self.redraw_heatmap(); self.run_analysis()
        self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="white", tags="pt")
        self.canvas.create_text(x, y-12, text=label, fill="white", font=("Arial", 10, "bold"), tags="pt")

    def reset_map(self):
        self.data_points = []; self.room_outline = []
        self.canvas.delete("all")
        self.preview_label.config(image='')
        self.stat_pts.config(text="PTS: 0")
        self.stat_range.config(text="RANGE: --")
        self.stat_grade.config(text="GRADE: -", fg="#00ff00")
        self.stat_avg.config(text="AVG: -- dBm")
        self.history_list.config(state="normal"); self.history_list.delete("1.0", tk.END); self.history_list.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('default')
    style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
    style.configure("TNotebook.Tab", background="#333", foreground="#888", padding=[6, 2], font=("Arial", 8, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#1e1e1e")], foreground=[("selected", "#00ff00")])
    app = DashboardMapper(root); root.mainloop()
