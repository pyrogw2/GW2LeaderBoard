import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import sys
from pathlib import Path
from threading import Thread
import queue
import multiprocessing
import tempfile
import subprocess
import zipfile
import shutil
import webbrowser
import traceback
try:
    from packaging import version
except ImportError:
    # Fallback for basic version comparison
    def version_compare(v1, v2):
        """Simple version comparison fallback"""
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        # Pad with zeros to same length
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        return v1_parts < v2_parts
    
    class version:
        @staticmethod
        def parse(v):
            return v
        
        @staticmethod
        def __gt__(v1, v2):
            return version_compare(v2, v1)

# It's better to refactor workflow.py to import functions, but for now,
# we can add the src path and import the main functions directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gw2_leaderboard.utils.sync_logs import main as sync_logs_main
from gw2_leaderboard.parsers.parse_logs_enhanced import main as parse_logs_enhanced_main
from gw2_leaderboard.core.glicko_rating_system import main as glicko_rating_system_main
from gw2_leaderboard.web.generate_web_ui import main as generate_web_ui_main
from gw2_leaderboard.core.guild_manager import main as guild_manager_main

CONFIG_FILE = "sync_config.json"
VERSION = "0.0.10"  # Current version - should match release tags
GITHUB_REPO = "pyrogw2/GW2LeaderBoard"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

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
        
        # Optional: Check for updates on startup (after a delay)
        self.after(2000, self.check_for_updates_silent)

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

        # --- Update Section ---
        update_frame = ttk.LabelFrame(self.config_tab, text="Updates")
        update_frame.pack(padx=10, pady=10, fill="x")
        
        # Version info with build date
        import datetime
        build_date = datetime.datetime.now().strftime("%Y-%m-%d")
        version_label = ttk.Label(update_frame, text=f"Current Version: v{VERSION} (Built: {build_date})")
        version_label.pack(pady=5)
        
        # Update buttons
        button_frame = ttk.Frame(update_frame)
        button_frame.pack(pady=5)
        
        check_update_button = ttk.Button(button_frame, text="Check for Updates", command=self.check_for_updates)
        check_update_button.pack(side="left", padx=5)
        
        manual_update_button = ttk.Button(button_frame, text="Open Releases Page", command=self.open_releases_page)
        manual_update_button.pack(side="left", padx=5)
        
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
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"⚠️ Configuration file {CONFIG_FILE} not found or invalid. Using defaults.")
            config = DEFAULT_CONFIG.copy()
            # Save the default config
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                print(f"✅ Created default configuration file: {CONFIG_FILE}")
            except Exception as e:
                print(f"❌ Could not create config file: {e}")
        
        # Ensure all required configuration keys exist with defaults
        config_defaults = {
            'extracted_logs_dir': 'extracted_logs',
            'web_ui_output': 'web_ui_output',
            'database_path': 'gw2_comprehensive.db',
            'log_aggregate_url': 'https://pyrogw2.github.io',
            'max_logs_per_run': 5,
            'auto_confirm': False
        }
        
        updated = False
        for key, default_value in config_defaults.items():
            if key not in config:
                config[key] = default_value
                updated = True
                print(f"✅ Added missing config key '{key}' with default: {default_value}")
        
        # Ensure guild configuration exists
        if 'guild' not in config:
            config['guild'] = DEFAULT_CONFIG['guild'].copy()
            updated = True
            print("✅ Added missing guild configuration")
        
        # Save updated config if we made changes
        if updated:
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                print(f"✅ Updated configuration file: {CONFIG_FILE}")
            except Exception as e:
                print(f"⚠️ Could not save updated config: {e}")
        
        # Ensure required directories exist
        required_dirs = [
            config.get('extracted_logs_dir', 'extracted_logs'),
            config.get('web_ui_output', 'web_ui_output')
        ]
        
        for dir_path in required_dirs:
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ Ensured directory exists: {dir_path}")
            except Exception as e:
                print(f"⚠️ Could not create directory {dir_path}: {e}")
        
        return config

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
        sys.argv = ['guild_manager.py', '--sync', '--force', '--stats']
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
    
    def open_releases_page(self):
        """Open the GitHub releases page in browser"""
        webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases")
    
    def check_for_updates(self):
        """Check for updates and optionally download/install them"""
        # Start update check in background thread
        thread = Thread(target=self._check_for_updates_thread)
        thread.daemon = True
        thread.start()
    
    def check_for_updates_silent(self):
        """Check for updates silently on startup - only notify if update available"""
        thread = Thread(target=self._check_for_updates_thread_silent)
        thread.daemon = True
        thread.start()
    
    def _check_for_updates_thread_silent(self):
        """Silent background check - only shows notification if update available"""
        try:
            response = requests.get(GITHUB_API_URL, timeout=5)
            response.raise_for_status()
            
            releases = response.json()
            if not releases:
                return
            
            latest_release = releases[0]
            latest_version = latest_release['tag_name'].lstrip('v')
            current_version = VERSION.lstrip('v')
            
            if version.parse(latest_version) > version.parse(current_version):
                # Update available - show subtle notification
                self.after(0, lambda: self._show_update_notification(latest_release))
                
        except Exception:
            # Silent failure for startup check
            pass
    
    def _show_update_notification(self, latest_release):
        """Show subtle update notification"""
        latest_version = latest_release['tag_name'].lstrip('v')
        
        result = messagebox.askyesno(
            "Update Available",
            f"Version v{latest_version} is available!\n\nWould you like to check it out?",
            icon='info'
        )
        
        if result:
            self._show_update_dialog(latest_release, latest_version)
    
    def _check_for_updates_thread(self):
        """Background thread for checking updates"""
        try:
            print("🔍 Checking for updates...")
            print(f"GitHub API URL: {GITHUB_API_URL}")
            
            # Get latest release info
            response = requests.get(GITHUB_API_URL, timeout=10)
            print(f"API Response status: {response.status_code}")
            response.raise_for_status()
            
            releases = response.json()
            if not releases:
                raise Exception("No releases found")
            
            # Get the latest release (first in the list)
            latest_release = releases[0]
            print(f"Found {len(releases)} releases, latest: {latest_release['tag_name']}")
            print(f"Latest release info: {json.dumps(latest_release, indent=2)[:500]}...")
            
            latest_version = latest_release['tag_name'].lstrip('v')
            current_version = VERSION.lstrip('v')
            
            print(f"Current version: v{current_version}")
            print(f"Latest version: v{latest_version}")
            
            # Debug version comparison
            try:
                is_newer = version.parse(latest_version) > version.parse(current_version)
                print(f"Version comparison: v{latest_version} > v{current_version} = {is_newer}")
            except Exception as ver_err:
                print(f"Version comparison error: {ver_err}")
                # Fallback to simple string comparison
                is_newer = latest_version != current_version
                print(f"Fallback comparison: {latest_version} != {current_version} = {is_newer}")
            
            if is_newer:
                # Update available
                print("✅ Update available! Showing dialog...")
                self._handle_update_available(latest_release)
            else:
                # No update needed
                print("ℹ️ No update needed")
                self.after(0, lambda: messagebox.showinfo(
                    "No Updates", 
                    f"You're already running the latest version (v{current_version})"
                ))
                
        except Exception as e:
            print(f"❌ Error checking for updates: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            self.after(0, lambda: messagebox.showerror(
                "Update Check Failed", 
                f"Could not check for updates:\n{str(e)}"
            ))
    
    def _handle_update_available(self, latest_release):
        """Handle when an update is available"""
        latest_version = latest_release['tag_name'].lstrip('v')
        current_version = VERSION.lstrip('v')
        
        # Show update dialog on main thread
        self.after(0, lambda: self._show_update_dialog(latest_release, latest_version))
    
    def _show_update_dialog(self, latest_release, latest_version):
        """Show update confirmation dialog"""
        message = f"""Update Available!

Current Version: v{VERSION.lstrip('v')}
Latest Version: v{latest_version}

Release Notes:
{latest_release.get('body', 'No release notes available.')[:200]}...

Would you like to download and install the update?
(This will restart the application)"""
        
        result = messagebox.askyesnocancel(
            "Update Available",
            message,
            icon='question'
        )
        
        if result is True:  # Yes - download and install
            self._start_update_download(latest_release)
        elif result is False:  # No - open releases page
            self.open_releases_page()
        # Cancel - do nothing
    
    def _start_update_download(self, latest_release):
        """Start the update download process"""
        print(f"🔄 Starting update download...")
        
        # Show progress dialog
        self.update_progress_window = tk.Toplevel(self)
        self.update_progress_window.title("Downloading Update")
        self.update_progress_window.geometry("400x150")
        self.update_progress_window.resizable(False, False)
        
        # Center the window
        self.update_progress_window.transient(self)
        self.update_progress_window.grab_set()
        
        # Progress widgets
        ttk.Label(self.update_progress_window, text="Downloading update...").pack(pady=10)
        
        self.update_progress_bar = ttk.Progressbar(
            self.update_progress_window, 
            mode='indeterminate'
        )
        self.update_progress_bar.pack(pady=10, padx=20, fill='x')
        self.update_progress_bar.start()
        
        self.update_status_label = ttk.Label(self.update_progress_window, text="Preparing download...")
        self.update_status_label.pack(pady=5)
        
        # Cancel button
        cancel_button = ttk.Button(
            self.update_progress_window, 
            text="Cancel", 
            command=self._cancel_update
        )
        cancel_button.pack(pady=10)
        
        # Start download in background thread
        self.update_cancelled = False
        thread = Thread(target=self._download_update_thread, args=(latest_release,))
        thread.daemon = True
        thread.start()
    
    def _cancel_update(self):
        """Cancel the update download"""
        self.update_cancelled = True
        if hasattr(self, 'update_progress_window'):
            self.update_progress_window.destroy()
    
    def _download_update_thread(self, latest_release):
        """Background thread for downloading update"""
        try:
            # Find the appropriate asset for current platform
            platform_asset = self._find_platform_asset(latest_release['assets'])
            
            if not platform_asset:
                raise Exception("No suitable download found for your platform")
            
            if self.update_cancelled:
                return
            
            # Update status
            self.after(0, lambda: self.update_status_label.config(
                text=f"Downloading {platform_asset['name']}..."
            ))
            
            # Download the asset
            download_path = self._download_asset(platform_asset)
            
            if self.update_cancelled:
                return
            
            # Extract and prepare update
            self.after(0, lambda: self.update_status_label.config(
                text="Preparing update..."
            ))
            
            extracted_path = self._extract_update(download_path)
            
            if self.update_cancelled:
                return
            
            # Create update script and restart
            self.after(0, lambda: self.update_status_label.config(
                text="Installing update..."
            ))
            
            self._create_update_script(extracted_path)
            
        except Exception as e:
            print(f"❌ Update download failed: {e}")
            if not self.update_cancelled:
                self.after(0, lambda: self._show_update_error(str(e)))
    
    def _find_platform_asset(self, assets):
        """Find the appropriate download asset for current platform"""
        platform_keywords = {
            'win32': ['Windows', 'windows'],
            'darwin': ['macOS', 'macos'],
            'linux': ['Linux', 'linux']
        }
        
        current_platform = sys.platform
        keywords = platform_keywords.get(current_platform, [])
        
        for asset in assets:
            if any(keyword in asset['name'] for keyword in keywords):
                return asset
        
        return None
    
    def _download_asset(self, asset):
        """Download the update asset"""
        import urllib.request
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        download_path = os.path.join(temp_dir, asset['name'])
        
        # Download with progress (simplified)
        urllib.request.urlretrieve(asset['browser_download_url'], download_path)
        
        return download_path
    
    def _extract_update(self, download_path):
        """Extract the downloaded update"""
        extract_dir = os.path.join(os.path.dirname(download_path), 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        # Extract ZIP
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        return extract_dir
    
    def _create_update_script(self, extracted_path):
        """Create platform-specific update script and restart"""
        current_exe = sys.executable
        
        # Find the new executable in extracted files
        new_exe = self._find_executable_in_extracted(extracted_path)
        
        if not new_exe:
            raise Exception("Could not find executable in downloaded update")
        
        if sys.platform == 'win32':
            self._create_windows_update_script(current_exe, new_exe)
        elif sys.platform == 'darwin':
            self._create_macos_update_script(current_exe, new_exe)
        else:  # Linux
            self._create_linux_update_script(current_exe, new_exe)
    
    def _find_executable_in_extracted(self, extracted_path):
        """Find the executable file in extracted update"""
        for root, dirs, files in os.walk(extracted_path):
            # Look for .app directories on macOS
            if sys.platform == 'darwin':
                for dir_name in dirs:
                    if dir_name.endswith('.app'):
                        return os.path.join(root, dir_name)
            
            # Look for files
            for file in files:
                if sys.platform == 'win32' and file.endswith('.exe'):
                    return os.path.join(root, file)
                elif sys.platform == 'linux' and os.access(os.path.join(root, file), os.X_OK):
                    # Check if it's likely our executable (not a script)
                    if not file.endswith(('.sh', '.py', '.txt', '.md')):
                        return os.path.join(root, file)
        return None
    
    def _create_windows_update_script(self, current_exe, new_exe):
        """Create Windows batch script for update"""
        script_content = f'''@echo off
echo Updating GW2 Leaderboard...
timeout /t 3 /nobreak >nul
taskkill /F /IM "{os.path.basename(current_exe)}" 2>nul
timeout /t 1 /nobreak >nul
copy /Y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
'''
        
        script_path = os.path.join(tempfile.gettempdir(), 'gw2_update.bat')
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Close progress window and start update
        self.after(0, lambda: self.update_progress_window.destroy())
        self.after(0, lambda: messagebox.showinfo(
            "Update Starting", 
            "The application will restart to complete the update."
        ))
        
        # Start update script and exit
        subprocess.Popen([script_path], shell=True)
        self.after(1000, lambda: sys.exit(0))
    
    def _create_macos_update_script(self, current_exe, new_exe):
        """Create macOS shell script for update"""
        script_content = f'''#!/bin/bash
echo "Updating GW2 Leaderboard..."
sleep 3
pkill -f "{os.path.basename(current_exe)}" 2>/dev/null
sleep 1
cp -r "{new_exe}" "{current_exe}"
open "{current_exe}"
rm "$0"
'''
        
        script_path = os.path.join(tempfile.gettempdir(), 'gw2_update.sh')
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        # Close progress window and start update
        self.after(0, lambda: self.update_progress_window.destroy())
        self.after(0, lambda: messagebox.showinfo(
            "Update Starting", 
            "The application will restart to complete the update."
        ))
        
        # Start update script and exit
        subprocess.Popen([script_path])
        self.after(1000, lambda: sys.exit(0))
    
    def _create_linux_update_script(self, current_exe, new_exe):
        """Create Linux shell script for update"""
        script_content = f'''#!/bin/bash
echo "Updating GW2 Leaderboard..."
sleep 3
pkill -f "{os.path.basename(current_exe)}" 2>/dev/null
sleep 1
cp "{new_exe}" "{current_exe}"
chmod +x "{current_exe}"
"{current_exe}" &
rm "$0"
'''
        
        script_path = os.path.join(tempfile.gettempdir(), 'gw2_update.sh')
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        # Close progress window and start update
        self.after(0, lambda: self.update_progress_window.destroy())
        self.after(0, lambda: messagebox.showinfo(
            "Update Starting", 
            "The application will restart to complete the update."
        ))
        
        # Start update script and exit
        subprocess.Popen([script_path])
        self.after(1000, lambda: sys.exit(0))
    
    def _show_update_error(self, error_message):
        """Show update error dialog"""
        if hasattr(self, 'update_progress_window'):
            self.update_progress_window.destroy()
        
        messagebox.showerror(
            "Update Failed", 
            f"Failed to download/install update:\n{error_message}\n\nYou can manually download from the releases page."
        )
        
        if messagebox.askyesno("Open Releases Page", "Would you like to open the releases page to download manually?"):
            self.open_releases_page()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
