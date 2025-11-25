import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import socket
import sys
import ctypes
import requests
import subprocess
import winreg

SERVICE_NAME = "beszelagent"
AGENT_PORT = 45876

# Widgets, die später in apply_theme() / Badge-Updates benutzt werden
connection_badge = None
status_badge = None
path_label = None

# Unterdrückt Konsolenfenster für alle subprocess-Aufrufe (nur Windows)
CREATE_NO_WINDOW = 0x08000000

# ---------------- THEME SYSTEM ---------------- #

THEME = {
    "light": {
        "bg": "#f3f3f3",
        "card": "#ffffff",
        "border": "#d4d4d4",
        "text": "#111827",
        "muted": "#555555",
        "accent": "#2563eb",
        "badge_green_fg": "#0f5132",
        "badge_green_bg": "#d1e7dd",
        "badge_yellow_fg": "#664d03",
        "badge_yellow_bg": "#fff3cd",
        "badge_red_fg": "#842029",
        "badge_red_bg": "#f8d7da",
    },
    "dark": {
        "bg": "#1f1f1f",
        "card": "#2b2b2b",
        "border": "#3a3a3a",
        "text": "#e5e5e5",
        "muted": "#a3a3a3",
        "accent": "#3b82f6",
        "badge_green_fg": "#bbf7d0",
        "badge_green_bg": "#14532d",
        "badge_yellow_fg": "#fef9c3",
        "badge_yellow_bg": "#854d0e",
        "badge_red_fg": "#fecaca",
        "badge_red_bg": "#7f1d1d",
    }
}

current_theme = "light"

# ---------------- Service helper functions ---------------- #

### Get service status -- running, stopped, etc. ###
def get_service_status():
    result = subprocess.run(
        ["sc", "query", SERVICE_NAME],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )
    out = result.stdout.upper()

    if "RUNNING" in out:
        return "Running"
    if "STOPPED" in out:
        return "Stopped"
    if "PAUSED" in out:
        return "Paused"
    if "START_PENDING" in out:
        return "Starting…"
    if "STOP_PENDING" in out:
        return "Stopping…"
    return "Unknown"

### Get service start type -- automatic, manual, disabled ###
def get_start_type():
    result = subprocess.run(
        ["sc", "qc", SERVICE_NAME],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )
    out = result.stdout.upper()

    if "DELAYED_AUTO_START" in out:
        return "Automatic (Delayed)"
    if "AUTO_START" in out:
        return "Automatic"
    if "DEMAND_START" in out:
        return "Manual"
    if "DISABLED" in out:
        return "Disabled"
    return "Unknown"

### Get installation path from registry ###
def get_install_path():

    reg_key = r"HKLM\SYSTEM\CurrentControlSet\Services\beszelagent\Parameters"

    try:
        result = subprocess.run(
            ["reg", "query", reg_key, "/v", "Application"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW
        )

        out = result.stdout

        if "Application" in out:
            # Teile am Datentyp: REG_SZ *oder* REG_EXPAND_SZ
            if "REG_EXPAND_SZ" in out:
                parts = out.split("REG_EXPAND_SZ")
            elif "REG_SZ" in out:
                parts = out.split("REG_SZ")
            else:
                return "Unknown"

            path = parts[1].strip().strip('"')

            # Expand %PROGRAMFILES%, %SYSTEMROOT%, etc.
            path = os.path.expandvars(path)

            return path
    except Exception:
        pass

    return "Unknown"

### Get system environment variables ###
def get_env_vars():
    reg_path = r"SYSTEM\CurrentControlSet\Services\beszelagent\Parameters"

    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
    except FileNotFoundError:
        return "Registry path not found."

    lines = []
    index = 0

    while True:
        try:
            name, value, vtype = winreg.EnumValue(key, index)
        except OSError:
            break  # keine weiteren Einträge
        index += 1

        # Typ-Name bestimmen
        if vtype == winreg.REG_SZ:
            type_name = "REG_SZ"
            value_str = str(value)

        elif vtype == winreg.REG_EXPAND_SZ:
            type_name = "REG_EXPAND_SZ"
            value_str = os.path.expandvars(value)

        elif vtype == winreg.REG_MULTI_SZ:
            type_name = "REG_MULTI_SZ"
            value_str = "\n  " + "\n  ".join(value)

        else:
            type_name = f"REG_{vtype}"
            value_str = str(value)

        lines.append(f"{name} ({type_name}):\n  {value_str}\n")

    return "\n".join(lines) if lines else "No values found."

### Agent update functions ###
def download_latest_agent():
    url = agent_update_url_var.get()
    if not url:
        messagebox.showinfo("Agent Update", "Agent is already up to date.")
        return
    try:
        os.startfile(url)
    except Exception as e:
        messagebox.showerror("Download failed", str(e))

### Test connection to agent port ###
def test_agent_connection():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", AGENT_PORT))
        s.close()
        return True
    except Exception:
        return False

### Ensure Beszel Agent Control Center is running as admin ###    
def ensure_admin():
    """
    Relaunch the script as admin if not already elevated.
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        # Re-run with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join([sys.argv[0]] + sys.argv[1:]),
            None, 1
        )
        sys.exit()

# Call immediately at startup
ensure_admin()

### Fetch latest agent version from GitHub ###
def get_github_latest_version():
    try:
        resp = requests.get("https://api.github.com/repos/henrygd/beszel/releases/latest", timeout=5)
        data = resp.json()
        tag = data.get("tag_name", "").strip()  # z.B. "v0.16.1"
        return tag.lstrip("v")  # <-- entfernt führendes v
    except:
        return None

### Compare installed and latest versions ###
def compare_versions(installed, latest):
    if not installed or not latest:
        return "Unknown"

    # normalize (remove v-prefix)
    installed_norm = installed.lstrip("v")
    latest_norm = latest.lstrip("v")

    if installed_norm == latest_norm:
        return "Up to date"
    else:
        return "Update available"

### Trigger agent update check ###
def trigger_agent_update_check():
    agent_path = os.path.join(path_var.get(), "beszel-agent.exe")
    get_github_latest_version(agent_path)

# ---------------- GUI actions ---------------- #
### Service control functions ###
def start_service():
    subprocess.run(
        ["sc", "start", SERVICE_NAME],
        creationflags=CREATE_NO_WINDOW
    )
    refresh_all()
    messagebox.showinfo("Service", "Service started.")
def stop_service():
    subprocess.run(
        ["sc", "stop", SERVICE_NAME],
        creationflags=CREATE_NO_WINDOW
    )
    refresh_all()
    messagebox.showinfo("Service", "Service stopped.")
def restart_service():
    subprocess.run(
        ["sc", "stop", SERVICE_NAME],
        creationflags=CREATE_NO_WINDOW
    )
    subprocess.run(
        ["sc", "start", SERVICE_NAME],
        creationflags=CREATE_NO_WINDOW
    )
    refresh_all()
    messagebox.showinfo("Service", "Service restarted.")

### Open installation directory ###
def open_install_directory():
    path = get_install_path()
    if not path or not os.path.exists(path):
        messagebox.showerror("Error", "Installation directory not found.")
        return

    folder = os.path.dirname(path)
    try:
        os.startfile(folder)
    except Exception as e:
        messagebox.showerror("Error", f"Could not open directory:\n{e}")

### Open environment variables window ###
def open_env_window():
    env_text = get_env_vars()

    win = tk.Toplevel(root)
    win.title("System Environment Variables")
    win.geometry("800x500")

    th = THEME[current_theme]

    txt = scrolledtext.ScrolledText(
        win,
        wrap="word",
        font=("Consolas", 10),
        bg=th["card"],
        fg=th["text"],
        insertbackground=th["text"]
    )
    txt.pack(fill="both", expand=True, padx=10, pady=10)
    txt.insert("1.0", env_text)
    txt.config(state="disabled")

### Refresh status badge for beszel agent service ###
def refresh_status_badge():
    if status_badge is None:
        return

    th = THEME[current_theme]
    status = status_var.get()

    if status == "Running":
        status_badge.config(bg=th["badge_green_bg"], fg=th["badge_green_fg"])
    elif status in ("Starting…", "Stopping…"):
        status_badge.config(bg=th["badge_yellow_bg"], fg=th["badge_yellow_fg"])
    else:
        status_badge.config(bg=th["badge_red_bg"], fg=th["badge_red_fg"])

### Refresh all displayed information ###
def refresh_all():
    status = get_service_status()
    start_type = get_start_type()
    path = get_install_path()
    version = get_installed_agent_version(os.path.join(path, "beszel-agent.exe"))

    status_var.set(status)
    starttype_var.set(start_type)
    path_var.set(path)
    version_var.set(version)

    agent_exe = os.path.join(path, "beszel-agent.exe")
    installed = get_installed_agent_version(agent_exe)
    latest = get_github_latest_version()

    status = compare_versions(installed, latest)

    agent_installed_var.set(installed or "Unknown")
    agent_latest_var.set(latest or "Failed to check")

    # NEW: Only indicate update availability (no URLs)
    if status == "Up to date":
        update_available_var.set("✔ Agent is up to date")
    else:
        update_available_var.set("⚠ Update available")

    refresh_status_badge()
    update_connection_badge()

    # Auto-refresh every 5 seconds
    root.after(5000, refresh_all)

### Update connection badge to beszel agent port ###
def update_connection_badge():
    th = THEME[current_theme]
    status = connection_status_var.get()

    if status == "Connected":
        connection_badge.configure(
            text="Connected",
            bg=th["badge_green_bg"],
            fg=th["badge_green_fg"]
        )
    elif status == "Not reachable":
        connection_badge.configure(
            text="Not reachable",
            bg=th["badge_red_bg"],
            fg=th["badge_red_fg"]
        )
    else:
        connection_badge.configure(
            text="Unknown",
            bg=th["badge_yellow_bg"],
            fg=th["badge_yellow_fg"]
        )

### Run connection test to beszel agent port ###
def run_connection_test():
    ok = test_agent_connection()

    if ok:
        connection_status_var.set("Connected")
    else:
        connection_status_var.set("Not reachable")

    update_connection_badge()

### Update beszel agent ###
def update_beszel_agent():
    raw_path = path_var.get().strip()

    if not raw_path:
        messagebox.showerror("Update failed", "Install path not found.")
        return

    # Detect whether path_var contains directory OR the agent.exe file
    if raw_path.lower().endswith("beszel-agent.exe"):
        install_dir = os.path.dirname(raw_path)
    else:
        install_dir = raw_path

    agent_exe = os.path.join(install_dir, "beszel-agent.exe")

    if not os.path.exists(agent_exe):
        messagebox.showerror(
            "Update failed",
            f"beszel-agent.exe not found in:\n{install_dir}"
        )
        return

    update_command = (
        f'powershell -Command "& {{'
        f'Set-Location -Path \'{install_dir}\'; '
        f'./beszel-agent.exe update }}"'
    )

    try:
        result = subprocess.run(
            update_command,
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            messagebox.showinfo(
                "Update successful",
                "Beszel Agent has been updated."
            )
        else:
            messagebox.showerror(
                "Update failed",
                f"Error:\n{result.stdout}\n{result.stderr}"
            )

    except Exception as e:
        messagebox.showerror("Update failed", str(e))

### Get installed agent version from registry or by running agent.exe ###
def get_installed_agent_version(agent_path):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\beszelagent\Parameters",
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, "InstalledVersion")
        if value:
            return value.strip()
    except Exception:
        pass  # ignore, fallback below

    # ---------------------------
    # 2) Fallback: run agent.exe
    # ---------------------------
    if agent_path and os.path.exists(agent_path):
        try:
            result = subprocess.run(
                [agent_path, "--version"],
                capture_output=True,
                text=True
            )
            output = (result.stdout or "").strip()

            if output and "version" in output.lower():
                return output
        except:
            pass

    # ---------------------------
    # 3) If everything fails
    # ---------------------------
    return "Unknown"

# ---------------- THEME APPLY ---------------- #

def apply_theme(theme_name):
    global current_theme
    current_theme = theme_name
    th = THEME[theme_name]

    # Window background
    root.configure(bg=th["bg"])
    outer.configure(style="Main.TFrame")

    # ttk style updates
    style.configure("Main.TFrame", background=th["bg"])
    style.configure("Header.TLabel", background=th["bg"], foreground=th["text"])
    style.configure("SubHeader.TLabel", background=th["bg"], foreground=th["muted"])

    style.configure("Card.TFrame", background=th["card"], bordercolor=th["border"])
    style.configure("TLabel", background=th["card"], foreground=th["text"])

    style.configure(
        "Accent.TButton",
        background=th["accent"],
        foreground="#ffffff"
    )
    style.map(
        "Accent.TButton",
        background=[("active", th["accent"])],
        foreground=[("active", "#e5e5e5")]
    )

    style.configure("Ghost.TButton", background=th["card"], foreground=th["text"])
    style.map("Ghost.TButton", background=[("active", th["border"])])

    # tk-Labels / Badges nachziehen
    if status_badge is not None:
        status_badge.config(font=("Segoe UI", 9, "bold"))
        refresh_status_badge()

    if connection_badge is not None:
        update_connection_badge()


def toggle_theme():
    if current_theme == "light":
        apply_theme("dark")
    else:
        apply_theme("light")


# ---------------- GUI SETUP ---------------- #

root = tk.Tk()
icon_path = os.path.join(os.path.dirname(__file__), "beszelagent.ico")

try:
    root.iconbitmap(icon_path)
except Exception as e:
    print("Could not set icon:", e)
root.title("Beszel Agent – Control Center")
root.minsize(900, 480)

# Windows-typische Schrift
default_font = ("Segoe UI", 10)
root.option_add("*Font", default_font)

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

# Grund-Styles (werden von apply_theme überschrieben)
style.configure("Main.TFrame", background="#f3f3f3")
style.configure("Card.TFrame", background="#ffffff", borderwidth=1, relief="solid")
style.configure("Header.TLabel", font=("Segoe UI Semibold", 16))
style.configure("SubHeader.TLabel", font=("Segoe UI", 10))
style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(14, 6))
style.configure("Ghost.TButton", padding=(12, 5))

outer = ttk.Frame(root, style="Main.TFrame", padding=20)
outer.pack(fill="both", expand=True)

# Header
header = ttk.Frame(outer, style="Main.TFrame")
header.pack(fill="x", pady=(0, 15))

header_left = ttk.Frame(header, style="Main.TFrame")
header_left.pack(side="left", fill="x", expand=True)

ttk.Label(
    header_left,
    text="Beszel Agent Control Center",
    style="Header.TLabel"
).pack(anchor="w")

ttk.Label(
    header_left,
    text="Monitor and control the Beszel Agent Windows service.",
    style="SubHeader.TLabel"
).pack(anchor="w", pady=(2, 0))

header_right = ttk.Frame(header, style="Main.TFrame")
header_right.pack(side="right")

dark_btn = ttk.Button(
    header_right,
    text="Toggle dark mode",
    style="Ghost.TButton",
    command=toggle_theme
)
dark_btn.pack(anchor="e")

# Info Card
info_card = ttk.Frame(outer, style="Card.TFrame", padding=15)
info_card.pack(fill="x", pady=(0, 15))

status_var = tk.StringVar()
starttype_var = tk.StringVar()
path_var = tk.StringVar()
version_var = tk.StringVar()
connection_status_var = tk.StringVar(value="Unknown")

# Agent update system variables
agent_installed_var = tk.StringVar(value="Unknown")
agent_latest_var = tk.StringVar(value="Checking…")
agent_update_url_var = tk.StringVar(value="")
update_available_var = tk.StringVar(value="")

# ------------------------------
# UPDATE SECTION (separate frame)
# ------------------------------
update_frame = ttk.Frame(outer, style="Card.TFrame", padding=15)
update_frame.pack(fill="x", pady=(0, 15))

ttk.Label(update_frame, text="Installed Agent Version:", style="Body.TLabel")\
    .pack(anchor="w", pady=(0, 0))
ttk.Label(update_frame, textvariable=agent_installed_var, style="Subtle.TLabel")\
    .pack(anchor="w", pady=(0, 8))

ttk.Label(update_frame, text="Latest Agent Version:", style="Body.TLabel")\
    .pack(anchor="w", pady=(0, 0))
ttk.Label(update_frame, textvariable=agent_latest_var, style="Subtle.TLabel")\
    .pack(anchor="w", pady=(0, 8))

ttk.Button(
    update_frame,
    text="Download Latest Agent",
    style="Accent.TButton",
    command=download_latest_agent
).pack(anchor="w", pady=(8, 0))

# Service status row
status_label = ttk.Label(info_card, text="Service status:", font=("Segoe UI", 10, "bold"))
status_label.grid(row=0, column=0, sticky="w")

status_badge = tk.Label(
    info_card,
    textvariable=status_var,
    padx=8,
    pady=2,
    bd=0,
    relief="flat",
    highlightthickness=0
)
status_badge.grid(row=0, column=1, sticky="w", padx=(8,0))

# Start type
ttk.Label(info_card, text="Start type:", font=("Segoe UI", 10, "bold")).grid(
    row=1, column=0, sticky="w", pady=(6, 0)
)
ttk.Label(info_card, textvariable=starttype_var).grid(
    row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
)

# Install path
ttk.Label(info_card, text="Install path:", font=("Segoe UI", 10, "bold")).grid(
    row=2, column=0, sticky="nw", pady=(6, 0)
)
path_label = ttk.Label(info_card, textvariable=path_var, wraplength=540, justify="left")
path_label.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

# Version
ttk.Label(info_card, text="Agent version:", font=("Segoe UI", 10, "bold")).grid(
    row=3, column=0, sticky="w", pady=(6, 0)
)
ttk.Label(info_card, textvariable=version_var).grid(
    row=3, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
)

# Connection test
ttk.Label(info_card, text="Agent port:", font=("Segoe UI", 10, "bold")).grid(
    row=6, column=0, sticky="w", pady=(6, 0)
)
ttk.Label(info_card, text=str(AGENT_PORT)).grid(
    row=6, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
)

ttk.Label(info_card, text="Connection:", font=("Segoe UI", 10, "bold")).grid(
    row=7, column=0, sticky="w", pady=(6, 0)
)
connection_badge = tk.Label(
    info_card,
    textvariable=connection_status_var,
    padx=8,
    pady=2,
    bd=0,
    relief="flat",
    highlightthickness=0
)
connection_badge.grid(row=7, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

for i in range(2):
    info_card.columnconfigure(i, weight=1)

# Actions Card
actions_card = ttk.Frame(outer, style="Card.TFrame", padding=15)
actions_card.pack(fill="x")

btn_row = ttk.Frame(actions_card, style="Card.TFrame")
btn_row.pack(fill="x", pady=5)

button_list = [
    ("Start service", start_service, "Accent.TButton"),
    ("Stop service", stop_service, "Ghost.TButton"),
    ("Restart service", restart_service, "Ghost.TButton"),
    #("View log file", open_logs_window, "Ghost.TButton"),
    ("View environment variables", open_env_window, "Ghost.TButton"),
    ("Open install directory", open_install_directory, "Ghost.TButton"),
    ("Test connection", run_connection_test, "Ghost.TButton"),
    #("Update agent", update_beszel_agent, "Ghost.TButton"),
]

col = 0
row = 0
buttons_per_row = 3

for text, cmd, style_name in button_list:
    ttk.Button(
        btn_row,
        text=text,
        style=style_name,
        command=cmd
    ).pack(side="left", padx=6, pady=6)

# Initial theme + first refresh
root.update_idletasks()
apply_theme("dark")  # oder "light", wenn du standardmäßig Light willst
refresh_all()
update_connection_badge()
# Run agent update check after UI is initialized
root.after(500, trigger_agent_update_check)
root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")
root.mainloop()
###