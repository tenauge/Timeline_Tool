import tkinter as tk
from tkinter import ttk, font
from datetime import datetime, timezone
import re, json, os
from dateutil import parser
import pyperclip

CONFIG_FILE = "timeline_config.json"
DATA_FILE = "timeline_data.json"

class TimelineApp:
    def __init__(self, root):
        self.root = root
        self.root.title("时间线记录工具")
        self.events = []

        self.load_config()
        self.load_data()
        self.build_ui()
        self.refresh()

    def load_config(self):
        self.config = {
            "format": "%Y-%m-%d %H:%M:%S",
            "font_family": "Consolas",
            "font_size": 14,
            "geometry": "1200x750"
        }
        if os.path.exists(CONFIG_FILE):
            try:
                self.config.update(json.load(open(CONFIG_FILE)))
            except:
                pass

    def save_config(self):
        self.config.update({
            "format": self.format_var.get(),
            "font_family": self.font_family_var.get(),
            "font_size": self.font_size_var.get(),
            "geometry": self.root.geometry()
        })
        json.dump(self.config, open(CONFIG_FILE, "w"))

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                data = json.load(open(DATA_FILE))
                for item in data:
                    self.events.append((parser.parse(item[0]), item[1]))
            except:
                pass

    def save_data(self):
        data = [(t.strftime("%Y-%m-%d %H:%M:%S"), text) for t, text in self.events]
        json.dump(data, open(DATA_FILE, "w"))

    def build_ui(self):
        self.root.geometry(self.config["geometry"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=12)

        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned, width=450)
        right = ttk.Frame(paned)

        paned.add(left, weight=1)
        paned.add(right, weight=4)

        # ===== 左侧 =====
        top_frame = ttk.LabelFrame(left, text="添加事件")
        top_frame.pack(fill="x", padx=8, pady=8)

        now = datetime.now()
        self.year = tk.IntVar(value=now.year)
        self.month = tk.IntVar(value=now.month)
        self.day = tk.IntVar(value=now.day)
        self.hour = tk.IntVar(value=now.hour)
        self.minute = tk.IntVar(value=now.minute)
        self.second = tk.IntVar(value=now.second)

        time_frame = ttk.Frame(top_frame)
        time_frame.pack(fill="x", pady=8)

        def add_field(label, var, f, t, width):
            ttk.Label(time_frame, text=label, font=(self.config["font_family"], 12)).pack(side="left", padx=5)
            ttk.Spinbox(time_frame, from_=f, to=t, textvariable=var, width=width,
                        font=(self.config["font_family"], 12)).pack(side="left", padx=5)

        add_field("Y", self.year, 1970, 2100, 8)
        add_field("M", self.month, 1, 12, 5)
        add_field("D", self.day, 1, 31, 5)
        ttk.Label(time_frame, text="   ").pack(side="left")
        add_field("H", self.hour, 0, 23, 5)
        add_field("Min", self.minute, 0, 59, 5)
        add_field("S", self.second, 0, 59, 5)

        self.event_entry = ttk.Entry(top_frame, font=(self.config["font_family"], 13))
        self.event_entry.pack(fill="x", padx=6, pady=8)
        self.event_entry.bind("<Return>", self.add_single_event)

        bulk_frame = ttk.LabelFrame(left, text="批量添加事件")
        bulk_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.bulk_text = tk.Text(bulk_frame, font=(self.config["font_family"], 13))
        self.bulk_text.pack(fill="both", expand=True)
        self.bulk_text.bind("<Return>", self.add_bulk_events)

        # ===== 右侧 =====
        control_frame = ttk.Frame(right)
        control_frame.pack(fill="x", pady=5)

        self.format_var = tk.StringVar(value=self.config["format"])
        self.font_family_var = tk.StringVar(value=self.config["font_family"])
        self.font_size_var = tk.IntVar(value=self.config["font_size"])

        ttk.Label(control_frame, text="时间格式:").pack(side="left")
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%m-%d-%Y %H:%M:%S",
            "UTC %Y-%m-%dT%H:%M:%SZ",
            "Timestamp %s"
        ]
        ttk.OptionMenu(control_frame, self.format_var, self.format_var.get(), *formats, command=lambda _: self.refresh()).pack(side="left")

        ttk.Label(control_frame, text="字体:").pack(side="left", padx=5)
        families = sorted([f for f in font.families() if not f.startswith("@")])
        font_box = ttk.Combobox(control_frame, textvariable=self.font_family_var, values=families, width=18)
        font_box.pack(side="left")
        font_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Spinbox(control_frame, from_=10, to=32, textvariable=self.font_size_var, width=5, command=self.refresh).pack(side="left")
        ttk.Button(control_frame, text="清空", command=self.clear_events).pack(side="right", padx=5)
        ttk.Button(control_frame, text="复制", command=self.copy_timeline).pack(side="right", padx=5)

        self.timeline = tk.Text(
            right,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="white",
            spacing1=6,
            spacing3=6
        )
        self.timeline.pack(fill="both", expand=True)

    def get_selected_time(self):
        try:
            return datetime(self.year.get(), self.month.get(), self.day.get(),
                            self.hour.get(), self.minute.get(), self.second.get())
        except:
            return None

    def parse_line(self, line):
        line = line.strip()
        if not line:
            return None
        match = re.match(r"(.+?\d{1,2}:\d{1,2}:\d{1,2})\s+(.*)", line)
        if match:
            try:
                return parser.parse(match.group(1)), match.group(2)
            except:
                return None
        return None

    def add_single_event(self, event=None):
        t = self.get_selected_time()
        text = self.event_entry.get().strip()
        if t and text:
            self.events.append((t, text))
            self.event_entry.delete(0, tk.END)
            self.refresh()

    def add_bulk_events(self, event=None):
        for line in self.bulk_text.get("1.0", tk.END).split("\n"):
            parsed = self.parse_line(line)
            if parsed:
                self.events.append(parsed)
        self.bulk_text.delete("1.0", tk.END)
        self.refresh()
        return "break"

    def refresh(self):
        self.events.sort(key=lambda x: x[0])
        self.timeline.delete("1.0", tk.END)
        f = (self.font_family_var.get(), self.font_size_var.get())
        self.timeline.configure(font=f)

        fmt = self.format_var.get()
        for t, text in self.events:
            self.timeline.insert(tk.END, " ● ", "dot")
            if fmt.startswith("UTC"):
                ts = t.astimezone(timezone.utc)
                self.timeline.insert(tk.END, f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')} {text}\n")
            elif fmt.startswith("Timestamp"):
                self.timeline.insert(tk.END, f"{int(t.timestamp())} {text}\n")
            else:
                self.timeline.insert(tk.END, f"{t.strftime(fmt)} {text}\n")

        self.timeline.tag_config("dot", foreground="#38bdf8")

    def clear_events(self):
        self.events.clear()
        self.refresh()

    def copy_timeline(self):
        content = self.timeline.get("1.0", tk.END).replace("● ", "").strip()
        if content:
            pyperclip.copy(content)

    def on_close(self):
        self.save_config()
        self.save_data()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = TimelineApp(root)
    root.mainloop()