import subprocess, sys
import threading
import os, ctypes, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

try: # do not question my methods of installing.
    from win10toast import ToastNotifier
    from elevate import elevate as UAC_ADMIN
except Exception as e:
    print("Installing missing libraries...")
    subprocess.call([sys.executable, "-m", "pip", "install", "win10toast elevate"])

def is_admin() -> bool:
    return ctypes.windll.shell32.IsUserAnAdmin() != 0

if not is_admin():
    messagebox.showinfo("Permission Required", "The script requires administrator permissions. Please confirm UAC prompt.")
    # ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    # sys.exit(0)
    UAC_ADMIN()

username = os.getlogin()

# Define folders to clean with descriptions
CLEAN_TARGETS = {
    "Temp folders": [
        f"C:\\Users\\{username}\\AppData\\Local\\Temp",
        f"C:\\Windows\\Temp",
        f"C:\\ProgramData\\Temp"
    ],
    "Windows Installer Folder": [
        "C:\\Windows\\Installer"
    ],
    "Windows Logs": [
        "C:\\Windows\\Logs"
    ],
    "Prefetch": [
        "C:\\Windows\\Prefetch"
    ],
    "Recycle Bin": [
        "C:\\$Recycle.Bin"
    ],
    "Windows.old folder": [
        "C:\\Windows.old"
    ],
    "Windows SoftwareDistribution Download": [
        "C:\\Windows\\SoftwareDistribution\\Download"
    ],
    "Internet Cache": [
        f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Windows\\INetCache",
        f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Windows\\Temporary Internet Files",
        f"C:\\Users\\{username}\\AppData\\Local\\Packages\\Microsoft.WindowsStore_8wekyb3d8bbwe\\LocalCache"
    ],
    "Crash Dumps": [
        f"C:\\Users\\{username}\\AppData\\Local\\CrashDumps"
    ],
    #"Driver Store File Repository": [ # I STRONGLY RECOMMEND YOU DO NOT USE THIS FOLDER ASWELL THERE IS A 99.99% CHANCE IT WILL FUCK UP YOUR MOTHERBOARD I/O (still 3gb extra free tho :kek:)
    #    "C:\\Windows\\System32\\DriverStore\\FileRepository"
    #]
}

def get_folder_size(path: Path) -> int:
    total_size = 0
    if not path.exists():
        return 0
    try:
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                try:
                    fp = Path(root) / f
                    total_size += fp.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total_size

def get_recycle_bin_size() -> int:
    path = Path("C:\\$Recycle.Bin")
    total = 0
    if not path.exists():
        return 0
    for sid_folder in path.iterdir():
        if sid_folder.is_dir():
            total += get_folder_size(sid_folder)
    return total

def get_targets_size(paths: list[str]) -> int:
    total = 0
    for target in paths:
        path = Path(target)
        if path.exists():
            if str(path).lower() == "c:\\$recycle.bin":
                total += get_recycle_bin_size()
            elif path.is_dir():
                total += get_folder_size(path)
            else:
                try:
                    total += path.stat().st_size
                except Exception:
                    pass
    return total

def delete_folder_contents(path: Path) -> int:
    total_deleted = 0
    if not path.exists():
        return 0
    for item in path.iterdir():
        try:
            if item.is_dir():
                total_deleted += delete_folder_contents(item)
                item.rmdir()
            else:
                size = item.stat().st_size
                item.unlink()
                total_deleted += size
        except Exception:
            pass
    return total_deleted

def delete_folder(path: Path) -> int:
    total_deleted = 0
    if not path.exists():
        return 0
    try:
        total_deleted = get_folder_size(path)
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        total_deleted = delete_folder_contents(path)
        try:
            path.rmdir()
        except Exception:
            pass
    return total_deleted

def delete_recycle_bin() -> int:
    path = Path("C:\\$Recycle.Bin")
    total = 0
    if not path.exists():
        return 0
    for sid_folder in path.iterdir():
        if sid_folder.is_dir():
            total += delete_folder_contents(sid_folder)
    return total

class CleanerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Windows Cleaner")
        self.geometry("480x580")
        self.resizable(False, False)

        self.check_vars = {}
        self.total_size_var = tk.StringVar(value="Select folders to see estimated storage savings.")
        
        tk.Label(self, text="Select folders to clean:", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10)

        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.check_frame = tk.Frame(canvas)

        self.check_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.check_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for folder_name in CLEAN_TARGETS:
            var = tk.BooleanVar(value=False)
            self.check_vars[folder_name] = var
            
            # Add special handler for Windows Installer Folder
            if folder_name == "Windows Installer Folder":
                cb = ttk.Checkbutton(
                    self.check_frame, 
                    text=folder_name, 
                    variable=var, 
                    command=lambda fn=folder_name, v=var: self.on_installer_check(fn, v)
                )
            else:
                cb = ttk.Checkbutton(self.check_frame, text=folder_name, variable=var, command=self.update_size)
            cb.pack(anchor="w", pady=4)

        self.size_label = ttk.Label(self, textvariable=self.total_size_var, font=("Segoe UI", 11), wraplength=460)
        self.size_label.pack(pady=15)

        # Button frame for both buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        self.run_button = ttk.Button(button_frame, text="Run Cleaner", command=self.run_cleaner)
        self.run_button.pack(side="left", padx=5)

        self.windirstat_button = ttk.Button(button_frame, text="Open WinDirStat", command=self.open_windirstat)
        self.windirstat_button.pack(side="left", padx=5)

        self.toaster = ToastNotifier()

    def on_installer_check(self, folder_name, var):
        """Special handler for Windows Installer Folder checkbox"""
        if var.get():  # If being checked
            result = messagebox.askyesno(
                "Warning - Windows Installer Folder",
                "Warning: Cleaning the Windows Installer folder may prevent you from uninstalling or modifying installed programs.\n\n"
                "This folder contains important installation files that Windows uses for program maintenance.\n\n"
                "Are you sure you want to include this folder in the cleanup?",
                icon="warning"
            )
            if not result:
                var.set(False)  # Uncheck if user says no
        
        self.update_size()  # Update size calculation

    def update_size(self):
        selected_paths = []
        for name, var in self.check_vars.items():
            if var.get():
                selected_paths.extend(CLEAN_TARGETS[name])
        if not selected_paths:
            self.total_size_var.set("Select folders to see estimated storage savings.")
            return
        size_bytes = get_targets_size(selected_paths)
        size_mb = size_bytes / (1024*1024)
        self.total_size_var.set(f"Estimated storage to be freed: {size_mb:.2f} MB")

    def run_cleaner(self):
        selected_paths = []
        selected_names = []
        for name, var in self.check_vars.items():
            if var.get():
                selected_paths.extend(CLEAN_TARGETS[name])
                selected_names.append(name)
        
        if not selected_paths:
            messagebox.showwarning("No Selection", "Please select at least one folder to clean.")
            return
        
        # Final confirmation if Windows Installer Folder is selected
        if "Windows Installer Folder" in selected_names:
            result = messagebox.askyesno(
                "Final Confirmation",
                "You have selected the Windows Installer Folder for cleanup.\n\n"
                "This is your final warning: Cleaning this folder may cause issues with installed programs.\n\n"
                "Do you want to proceed with the cleanup?",
                icon="warning"
            )
            if not result:
                return
        
        self.run_button.config(state="disabled")
        self.total_size_var.set("Cleaning in progress, please wait...")

        total_cleaned = 0
        for target in selected_paths:
            path = Path(target)
            if not path.exists():
                continue
            if str(path).lower() == "c:\\$recycle.bin":
                total_cleaned += delete_recycle_bin()
            elif path.is_dir():
                total_cleaned += delete_folder(path)
            else:
                try:
                    size = path.stat().st_size
                    path.unlink()
                    total_cleaned += size
                except Exception:
                    pass

        size_mb = total_cleaned / (1024*1024)
        self.total_size_var.set(f"Cleanup complete! Freed {size_mb:.2f} MB.")
        self.run_button.config(state="normal")
        self.toaster.show_toast("Windows Cleaner", f"Cleanup complete! Freed {size_mb:.2f} MB storage.", duration=8, threaded=True)

    def open_windirstat(self):
        """Check or install WinDirStat using winget, then run it"""
        self.windirstat_button.config(state="disabled", text="Checking WinDirStat...")

        def run_windirstat_task():
            try:
                # Bekende installatiepaden
                common_paths = [
                    "C:\\Program Files\\WinDirStat\\windirstat.exe",
                    "C:\\Program Files (x86)\\WinDirStat\\windirstat.exe",
                    f"C:\\Users\\{username}\\AppData\\Local\\WinDirStat\\windirstat.exe"
                ]

                windirstat_path = None
                for path in common_paths:
                    if os.path.exists(path):
                        windirstat_path = path
                        break

                if windirstat_path:
                    # Al geïnstalleerd → starten
                    subprocess.Popen([windirstat_path])
                    self.after(0, lambda: self.windirstat_button.config(state="normal", text="Open WinDirStat"))
                else:
                    # Niet geïnstalleerd → vraag gebruiker of installeren met winget
                    result = messagebox.askyesno(
                        "Install WinDirStat",
                        "WinDirStat is not installed.\n\n"
                        "Do you want to install it automatically using winget?",
                        icon="question"
                    )

                    if result:
                        # Controleer of winget aanwezig is
                        try:
                            subprocess.run(["winget", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            # Winget ontbreekt → vraag of gebruiker naar downloadpagina wil gaan
                            go_download = messagebox.askyesno(
                                "Winget Missing",
                                "Winget is not installed or not available in PATH.\n\n"
                                "Would you like to open the official WinDirStat download page instead?"
                            )
                            if go_download:
                                import webbrowser
                                webbrowser.open("https://windirstat.net/download.html")

                                # Mogelijke downloadlocaties checken
                                possible_locations = [
                                    Path.home() / "Downloads" / "windirstat.exe",
                                    Path(__file__).parent / "windirstat.exe",
                                    Path.home() / "Desktop" / "windirstat.exe",
                                    Path.home() / "Documents" / "windirstat.exe"
                                ]

                                found_path = None
                                for p in possible_locations:
                                    if p.exists():
                                        found_path = str(p)
                                        break

                                if found_path:
                                    subprocess.Popen([found_path])
                                    messagebox.showinfo("WinDirStat", "WinDirStat was found and started from your downloads.")
                                    self.after(0, lambda: self.windirstat_button.config(state="normal", text="Open WinDirStat"))
                                    return

                            self.after(0, lambda: self.windirstat_button.config(state="normal", text="Open WinDirStat"))
                            return

                        self.after(0, lambda: self.windirstat_button.config(text="Installing WinDirStat..."))
                        try:
                            # winget installatie uitvoeren
                            subprocess.run([
                                "winget", "install", "WinDirStat.WinDirStat", "-e",
                                "--accept-source-agreements", "--accept-package-agreements"
                            ], check=True)

                            # Na installatie opnieuw zoeken naar uitvoerbaar bestand
                            for path in common_paths:
                                if os.path.exists(path):
                                    windirstat_path = path
                                    break

                            if windirstat_path:
                                subprocess.Popen([windirstat_path])
                                messagebox.showinfo("WinDirStat", "WinDirStat was successfully installed and started.")
                            else:
                                messagebox.showwarning("WinDirStat", "Installation finished, but WinDirStat could not be found. Try running it manually.")

                        except subprocess.CalledProcessError:
                            messagebox.showerror("Installation Failed", "Failed to install WinDirStat using winget.\nPlease try manually.")

                    # Knop resetten
                    self.after(0, lambda: self.windirstat_button.config(state="normal", text="Open WinDirStat"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to open or install WinDirStat: {str(e)}"))
                self.after(0, lambda: self.windirstat_button.config(state="normal", text="Open WinDirStat"))

        # Run in aparte thread zodat de GUI niet blokkeert
        thread = threading.Thread(target=run_windirstat_task)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    app = CleanerApp()
    app.mainloop()