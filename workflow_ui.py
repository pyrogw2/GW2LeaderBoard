import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import sys
from pathlib import Path
from threading import Thread
import queue
import multiprocessing

# It's better to refactor workflow.py to import functions, but for now,
# we can add the src path and import the main functions directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gw2_leaderboard.utils.sync_logs import main as sync_logs_main
from gw2_leaderboard.parsers.parse_logs_enhanced import main as parse_logs_enhanced_main
from gw2_leaderboard.core.glicko_rating_system import main as glicko_rating_system_main
from gw2_leaderboard.web.generate_web_ui import main as generate_web_ui_main
from gw2_leaderboard.core.guild_manager import main as guild_manager_main

CONFIG_FILE = "sync_config.json"

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
DEFAULT_CONFIG = {
    "log_aggregate_url": "https://pyrogw2.github.io",
    "database_path": "gw2_comprehensive.db",
    "extracted_logs_dir": "extracted_logs",
    "web_ui_output": "web_ui_output",
    "auto_confirm": False,
    "max_logs_per_run": 5,
    "guild": {
        "api_key": "",
        "guild_id": "",
        "guild_name": "",
        "guild_tag": "",
        "filter_enabled": False,
        "member_cache_hours": 6
    }
}

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.encoding = 'utf-8'
        self.text_widget.after(100, self.process_queue)

    def write(self, string):
        self.queue.put(string)

    def process_queue(self):
        while not self.queue.empty():
            string = self.queue.get_nowait()
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
        self.text_widget.after(100, self.process_queue)

    def flush(self):
        pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GW2 WvW Leaderboard Workflow")
        self.geometry("800x600")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        self.create_workflow_tab()
        self.create_config_tab()

        self.load_config()

    def create_workflow_tab(self):
        self.workflow_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.workflow_tab, text="Workflow")

        # --- Controls Frame ---
        controls_frame = ttk.LabelFrame(self.workflow_tab, text="Controls")
        controls_frame.pack(padx=10, pady=10, fill="x")

        self.run_full_button = ttk.Button(controls_frame, text="Run Full Workflow", command=self.run_full_workflow)
        self.run_full_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # --- Individual Steps ---
        steps_frame = ttk.LabelFrame(self.workflow_tab, text="Individual Steps")
        steps_frame.pack(padx=10, pady=5, fill="x")

        self.download_button = ttk.Button(steps_frame, text="Download Logs", command=lambda: self.run_task('download'))
        self.download_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.parse_button = ttk.Button(steps_frame, text="Parse Logs", command=lambda: self.run_task('parse'))
        self.parse_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.glicko_button = ttk.Button(steps_frame, text="Update Ratings", command=lambda: self.run_task('glicko'))
        self.glicko_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.ui_button = ttk.Button(steps_frame, text="Generate Web UI", command=lambda: self.run_task('ui'))
        self.ui_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        self.guild_button = ttk.Button(steps_frame, text="Refresh Guild Members", command=lambda: self.run_task('guild'))
        self.guild_button.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        # --- Options ---
        options_frame = ttk.LabelFrame(self.workflow_tab, text="Options")
        options_frame.pack(padx=10, pady=5, fill="x")

        self.latest_only_var = tk.BooleanVar()
        self.latest_only_check = ttk.Checkbutton(options_frame, text="Download latest log only", variable=self.latest_only_var)
        self.latest_only_check.pack(side="left", padx=5)

        self.force_rebuild_var = tk.BooleanVar()
        self.force_rebuild_check = ttk.Checkbutton(options_frame, text="Force complete rating history rebuild", variable=self.force_rebuild_var)
        self.force_rebuild_check.pack(side="left", padx=5)

        # --- Output Frame ---
        output_frame = ttk.LabelFrame(self.workflow_tab, text="Output")
        output_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=20)
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Redirect stdout
        self.stdout_redirector = StdoutRedirector(self.output_text)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stdout_redirector


    def create_config_tab(self):
        self.config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="Configuration")

        self.config_vars = {}
        
        # --- Basic Settings ---
        basic_frame = ttk.LabelFrame(self.config_tab, text="Basic Settings")
        basic_frame.pack(padx=10, pady=10, fill="x")
        
        self.create_config_entry(basic_frame, "log_aggregate_url", "Log Aggregate URL:", 0)
        self.create_config_entry(basic_frame, "database_path", "Database Filename:", 1)
        self.create_config_entry(basic_frame, "web_ui_output", "Web UI Output Dir:", 2)
        self.create_config_entry(basic_frame, "max_logs_per_run", "Max Logs Per Run:", 3)

        # --- Guild Settings ---
        guild_frame = ttk.LabelFrame(self.config_tab, text="Guild Settings")
        guild_frame.pack(padx=10, pady=10, fill="x")

        self.config_vars['guild_filter_enabled'] = tk.BooleanVar()
        self.guild_filter_check = ttk.Checkbutton(guild_frame, text="Enable Guild Filtering", variable=self.config_vars['guild_filter_enabled'])
        self.guild_filter_check.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        self.create_config_entry(guild_frame, "guild_api_key", "GW2 API Key:", 1, is_guild=True)
        self.create_config_entry(guild_frame, "guild_guild_id", "Guild ID:", 2, is_guild=True)
        self.create_config_entry(guild_frame, "guild_guild_name", "Guild Name:", 3, is_guild=True)
        self.create_config_entry(guild_frame, "guild_guild_tag", "Guild Tag:", 4, is_guild=True)
        self.create_config_entry(guild_frame, "guild_member_cache_hours", "Member Cache Hours:", 5, is_guild=True)

        # --- Save Button ---
        save_button = ttk.Button(self.config_tab, text="Save Configuration", command=self.save_config)
        save_button.pack(pady=10)

    def create_config_entry(self, parent, key, text, row, is_guild=False):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=60)
        entry.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        
        if is_guild:
            key = f"guild_{key.split('_', 1)[1]}"

        self.config_vars[key] = var

    def load_config(self):
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Deep merge
                for key, value in loaded_config.items():
                    if key in config and isinstance(config[key], dict):
                        config[key].update(value)
                    else:
                        config[key] = value
            except json.JSONDecodeError:
                messagebox.showerror("Config Error", f"Could not read {CONFIG_FILE}. It might be corrupted.")
        
        self.config_vars["log_aggregate_url"].set(config.get("log_aggregate_url", ""))
        self.config_vars["database_path"].set(config.get("database_path", ""))
        self.config_vars["web_ui_output"].set(config.get("web_ui_output", ""))
        self.config_vars["max_logs_per_run"].set(config.get("max_logs_per_run", ""))
        
        guild_config = config.get("guild", {})
        self.config_vars["guild_filter_enabled"].set(guild_config.get("filter_enabled", False))
        self.config_vars["guild_api_key"].set(guild_config.get("api_key", ""))
        self.config_vars["guild_guild_id"].set(guild_config.get("guild_id", ""))
        self.config_vars["guild_guild_name"].set(guild_config.get("guild_name", ""))
        self.config_vars["guild_guild_tag"].set(guild_config.get("guild_tag", ""))
        self.config_vars["guild_member_cache_hours"].set(guild_config.get("member_cache_hours", ""))

    def save_config(self):
        config = {
            "log_aggregate_url": self.config_vars["log_aggregate_url"].get(),
            "database_path": self.config_vars["database_path"].get(),
            "web_ui_output": self.config_vars["web_ui_output"].get(),
            "max_logs_per_run": int(self.config_vars["max_logs_per_run"].get() or 0),
            "guild": {
                "filter_enabled": self.config_vars["guild_filter_enabled"].get(),
                "api_key": self.config_vars["guild_api_key"].get(),
                "guild_id": self.config_vars["guild_guild_id"].get(),
                "guild_name": self.config_vars["guild_guild_name"].get(),
                "guild_tag": self.config_vars["guild_guild_tag"].get(),
                "member_cache_hours": int(self.config_vars["guild_member_cache_hours"].get() or 0)
            }
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", "Configuration saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def run_full_workflow(self):
        self.run_task('all')

    def run_task(self, task_name):
        # Disable buttons during run
        self.toggle_buttons(False)
        
        # Start the task in a new thread to keep the UI responsive
        thread = Thread(target=self._execute_task, args=(task_name,))
        thread.daemon = True
        thread.start()

    def _execute_task(self, task_name):
        self.output_text.delete('1.0', tk.END)
        print(f"--- Starting task: {task_name} ---\n")
        
        config = self._get_config_from_ui()
        
        try:
            if task_name == 'all' or task_name == 'download':
                self._run_sync_logs(config)
            if task_name == 'all' or task_name == 'parse':
                self._run_parse_logs(config)
            if task_name == 'all' or task_name == 'glicko':
                self._run_glicko(config)
            if task_name == 'all' or task_name == 'ui':
                self._run_generate_ui(config)
            if task_name == 'guild':
                self._run_guild_manager()

            print(f"\n--- Task '{task_name}' finished successfully! ---")
        except SystemExit as e:
            if e.code != 0:
                print(f"\n--- Task '{task_name}' failed with exit code {e.code}. ---")
        except Exception as e:
            print(f"\n--- An unexpected error occurred in task '{task_name}': {e} ---")
        finally:
            # Re-enable buttons on the main thread
            self.after(0, self.toggle_buttons, True)

    def _get_config_from_ui(self):
        # This can be expanded to read from the UI fields directly if needed
        # For now, it just re-reads the saved config file
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _run_sync_logs(self, config):
        print("\n--- Step 1: Downloading and extracting logs ---\n")
        sys_argv_backup = sys.argv[:]
        sys.argv = ['sync_logs.py', '--download-only', '--auto-confirm']
        if self.latest_only_var.get():
            sys.argv.extend(['--max-logs', '1'])
        sync_logs_main()
        sys.argv = sys_argv_backup

    def _run_parse_logs(self, config):
        print("\n--- Step 2: Parsing extracted logs ---\n")
        sys_argv_backup = sys.argv[:]
        sys.argv = ['parse_logs_enhanced.py', config['extracted_logs_dir'], '-d', config['database_path']]
        parse_logs_enhanced_main()
        sys.argv = sys_argv_backup

    def _run_glicko(self, config):
        print("\n--- Step 3: Updating Glicko ratings ---\n")
        sys_argv_backup = sys.argv[:]
        method = 'rebuild-history' if self.force_rebuild_var.get() else 'incremental'
        sys.argv = ['glicko_rating_system.py', config['database_path'], f'--{method}']
        glicko_rating_system_main()
        sys.argv = sys_argv_backup

    def _run_generate_ui(self, config):
        print("\n--- Step 4: Generating web UI ---\n")
        sys_argv_backup = sys.argv[:]
        sys.argv = ['generate_web_ui.py', config['database_path'], '-o', config['web_ui_output'], '--skip-recalc']
        generate_web_ui_main()
        sys.argv = sys_argv_backup

    def _run_guild_manager(self):
        print("\n--- Refreshing guild members ---\n")
        sys_argv_backup = sys.argv[:]
        sys.argv = ['guild_manager.py', '--refresh']
        guild_manager_main()
        sys.argv = sys_argv_backup

    def toggle_buttons(self, state):
        status = tk.NORMAL if state else tk.DISABLED
        self.run_full_button.config(state=status)
        self.download_button.config(state=status)
        self.parse_button.config(state=status)
        self.glicko_button.config(state=status)
        self.ui_button.config(state=status)
        self.guild_button.config(state=status)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
