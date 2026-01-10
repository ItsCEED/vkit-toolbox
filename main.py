# Standard library imports
import atexit
import ctypes
import json
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import winsound
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Optional

# Third-party imports
import yaml
import win32gui
import win32process
import psutil
from pynput import keyboard
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# Local application imports
from assets.ui import OverlayManager
from tools.autoclicker import AutoClicker, SnackSpammer, AntiAFK


# Optional dependencies
try:
    from solvers import casinofingerprint, casinokeypad, cayofingerprint, cayovoltage
    SOLVERS_AVAILABLE = True
except ImportError:
    SOLVERS_AVAILABLE = False


try:
    from exploits import jobwarp
    JOBWARP_AVAILABLE = True
except ImportError:
    JOBWARP_AVAILABLE = False


console = Console()


# Constants
VERSION = "v3.2.0"
APP_TITLE = "VKit - Toolbox"
GTA_PROCESS_NAME = "GTA5_Enhanced.exe"

# --- SMART PATHING ---
# If compiled, sys.executable is the .exe in your folder. 
# If script, __file__ is your main.py.
def get_base_dir() -> Path:
    """Get the directory containing the actual .exe or script"""
    # Method 1: Check sys.argv[0] (most reliable for onefile)
    # When you double-click VKit.exe, argv[0] contains the full path
    if sys.argv[0].endswith('.exe'):
        return Path(sys.argv[0]).parent.resolve()
    
    # Method 2: Check sys.executable
    exe_path = Path(sys.executable).resolve()
    exe_name = exe_path.name.lower()
    print(exe_path)
    print(exe_name)
    # If it's NOT python.exe AND not in a temp folder, use it
    if 'python' not in exe_name and 'temp' not in str(exe_path).lower():
        return exe_path.parent
    
    # Method 3: Fall back to __file__ (script mode)
    return Path(__file__).parent.resolve()


# Apply the fix
BASE_DIR = get_base_dir()
CONFIG_PATH = BASE_DIR / "config.yaml"
ASSETS_DIR = Path(__file__).parent  # Assets always from temp extraction

# Debug mode toggle
DEBUG = False

@dataclass
class AppConfig:
    """Application configuration"""
    rule_name: str
    remote_ip: str
    test_port: int
    hotkeys: dict
    require_game_focus: bool
    auto_stop_on_unfocus: bool

    @classmethod
    def load(cls, path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        if not path.exists():
            cls._create_default_config(path)

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        return cls(
            rule_name=config['firewall']['rule_name'],
            remote_ip=config['firewall']['remote_ip'],
            test_port=config['firewall']['test_port'],
            hotkeys=config['hotkeys'],
            require_game_focus=config.get('require_game_focus', True),
            auto_stop_on_unfocus=config.get('auto_stop_on_unfocus', True)
        )

    @staticmethod
    def _create_default_config(path: Path) -> None:
        """Create default configuration file"""
        default_config = {
            'firewall': {
                'rule_name': 'gtanosavemode_rule',
                'remote_ip': '192.81.241.171',
                'test_port': 80
            },
            'require_game_focus': True,
            'auto_stop_on_unfocus': True,
            'hotkeys': {
                'toggle_overlay': 'ctrl+f8',
                'toggle_nosave': 'ctrl+f9',
                'autoclicker': 'ctrl+k',
                'snack_spammer': 'ctrl+c',
                'anti_afk': 'ctrl+a',
                'job_warp': 'ctrl+alt+j',
                'debug_toggle': 'ctrl+shift+d',
                'kill_gta': 'ctrl+shift+q',
                'casino_fingerprint': 'f5',
                'casino_keypad': 'f6',
                'cayo_fingerprint': 'ctrl+f5',
                'cayo_voltage': 'ctrl+f6'
            }
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓[/green] Created default config at: {path}")



class WindowFocusManager:
    """Manages window focus detection - OPTIMIZED"""

    def __init__(self, process_name: str = "GTA5_Enhanced.exe"):
        self.process_name = process_name
        self.process_name_lower = process_name.lower()  # Cache lowercase
        self.gta_window_titles = tuple([  # Tuple faster than list
            "Grand Theft Auto V",
            "GTA5",
            "Rockstar Games"
        ])
        self._last_focus_state = False
        self._focus_callbacks = []
        self._shutdown_event = threading.Event()
        self._monitor_thread = None

        # OPTIMIZATION: Cache to reduce Win32 API calls
        self._last_hwnd = None
        self._last_pid = None
        self._last_process_name = None

    def get_active_window_process(self) -> Optional[str]:
        """Get process name - OPTIMIZED with caching"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            # OPTIMIZATION: Return cached if same window
            if hwnd == self._last_hwnd and self._last_process_name:
                return self._last_process_name

            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # OPTIMIZATION: Return cached if same PID
            if pid == self._last_pid and self._last_process_name:
                return self._last_process_name

            try:
                # Only create Process object if PID changed
                process = psutil.Process(pid)
                process_name = process.name()

                # Update cache
                self._last_hwnd = hwnd
                self._last_pid = pid
                self._last_process_name = process_name

                return process_name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None
        except Exception:
            return None

    def get_active_window_title(self) -> str:
        """Get window title - OPTIMIZED with caching"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == self._last_hwnd and hasattr(self, '_last_title'):
                return self._last_title

            title = win32gui.GetWindowText(hwnd)
            self._last_title = title
            return title
        except Exception:
            return ""

    def is_gta_focused(self) -> bool:
        """Check if GTA focused - OPTIMIZED"""
        # Method 1: Check by process name (cached)
        active_process = self.get_active_window_process()
        if active_process:
            # OPTIMIZATION: Use cached lowercase comparison
            if active_process.lower() == self.process_name_lower:
                return True

        # Method 2: Check by window title (cached)
        active_title = self.get_active_window_title()
        if active_title:
            active_title_lower = active_title.lower()
            return any(gta_title.lower() in active_title_lower 
                      for gta_title in self.gta_window_titles)

        return False

    def register_focus_callback(self, callback):
        """Register callback"""
        self._focus_callbacks.append(callback)

    def check_focus_change(self):
        """Check focus change - OPTIMIZED with thread safety"""
        current_focus = self.is_gta_focused()

        if current_focus != self._last_focus_state:
            # OPTIMIZATION: Copy list to avoid race condition
            callbacks = self._focus_callbacks.copy()

            for callback in callbacks:
                try:
                    callback(current_focus)
                except Exception as e:
                    if DEBUG:
                        print(f"[DEBUG] Focus callback error: {e}")

            self._last_focus_state = current_focus

    def start_monitoring(self, interval: float = 2.0):  # CHANGED: 2s instead of 1s
        """Start monitoring - OPTIMIZED interval"""
        def monitor():
            # OPTIMIZATION: Exponential backoff on errors
            error_count = 0
            max_errors = 10

            while not self._shutdown_event.is_set() and error_count < max_errors:
                try:
                    self.check_focus_change()
                    error_count = 0  # Reset on success
                except Exception as e:
                    error_count += 1
                    if DEBUG:
                        print(f"[DEBUG] Focus monitor error: {e}")

                    # Exponential backoff on repeated errors
                    if error_count > 3:
                        self._shutdown_event.wait(min(interval * error_count, 30))
                        continue

                self._shutdown_event.wait(interval)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring"""
        self._shutdown_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=3.0)



class SoundManager:
    """Manages sound effects for the application"""

    SOUND_FILES = {'on': 'on.wav', 'off': 'off.wav', 'toggle': 'toggle.wav'}

    def __init__(self) -> None:
        self.sounds_dir = ASSETS_DIR / "assets" / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        # Load sound paths and check existence
        self.sounds = {}
        for key, filename in self.SOUND_FILES.items():
            path = self.sounds_dir / filename
            self.sounds[key] = {'path': str(path), 'exists': path.exists()}

            if not self.sounds[key]['exists']:
                console.print(f"[yellow]⚠[/yellow] Sound file not found: {path}", style="dim")

    @staticmethod
    def _play(path: str) -> None:
        """Play sound asynchronously"""
        def _target() -> None:
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

        threading.Thread(target=_target, daemon=True).start()

    def play(self, sound_type: str) -> None:
        """Play a sound by type (on/off/toggle)"""
        if sound_type in self.sounds and self.sounds[sound_type]['exists']:
            self._play(self.sounds[sound_type]['path'])

    def play_on(self) -> None:
        self.play('on')

    def play_off(self) -> None:
        self.play('off')

    def play_toggle(self) -> None:
        self.play('toggle')

    def get_loaded_count(self) -> int:
        """Return count of successfully loaded sounds"""
        return sum(1 for sound in self.sounds.values() if sound['exists'])



class FirewallManager:
    """Manages firewall rules for blocking/unblocking IPs"""

    def __init__(self, config: AppConfig):
        self.rule_name = config.rule_name
        self.remote_ip = config.remote_ip
        self.test_port = config.test_port

    def rule_exists(self) -> bool:
        """Check if firewall rule exists"""
        cmd = f'netsh advfirewall firewall show rule name="{self.rule_name}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, 
                              creationflags=subprocess.CREATE_NO_WINDOW)
        return "No rules match the specified criteria" not in result.stdout

    def test_ip_blocked(self, timeout: float = 2) -> bool:
        """Test if IP is blocked by attempting connection"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((self.remote_ip, self.test_port))
                return result != 0
        except Exception:
            return True

    def add_rule(self, manager: OverlayManager, sound_manager: SoundManager) -> None:
        """Add firewall blocking rule"""
        cmd = (
            f'netsh advfirewall firewall add rule name="{self.rule_name}" '
            f'dir=out action=block remoteip="{self.remote_ip}"'
        )
        subprocess.run(cmd, shell=True, capture_output=True, 
                      creationflags=subprocess.CREATE_NO_WINDOW)

        time.sleep(0.5)
        if self.rule_exists():
            console.print("✓ NO SAVING MODE [bold red]ENABLED[/bold red]", style="green")
            manager.update_status("ON")
            manager.show_notification("NOSAVE MODE", "Session protection enabled", "#ef4444")
            sound_manager.play_on()

            if self.test_ip_blocked():
                console.print(
                    f"✓ Connection to [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                    f"is [bold red]BLOCKED[/bold red]", style="green"
                )
        else:
            console.print("✗ Failed to add firewall rule", style="red")
        console.print()

    def delete_rule(self, manager: OverlayManager, sound_manager: SoundManager) -> None:
        """Remove firewall blocking rule"""
        cmd = f'netsh advfirewall firewall delete rule name="{self.rule_name}"'
        subprocess.run(cmd, shell=True, capture_output=True, 
                      creationflags=subprocess.CREATE_NO_WINDOW)

        time.sleep(0.5)
        if not self.rule_exists():
            console.print("✓ NO SAVING MODE [bold green]DISABLED[/bold green]", style="green")
            manager.update_status("OFF")
            manager.show_notification("NOSAVE MODE", "Session protection disabled", "#85BB65")
            sound_manager.play_off()

            if not self.test_ip_blocked():
                console.print(
                    f"✓ Connection to [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                    f"is [bold green]ACCESSIBLE[/bold green]", style="green"
                )
        else:
            console.print("✗ Failed to delete firewall rule", style="red")
        console.print()

    def toggle_rule(self, manager: OverlayManager, sound_manager: SoundManager) -> None:
        """Toggle firewall rule on/off"""
        if self.rule_exists():
            self.delete_rule(manager, sound_manager)
        else:
            self.add_rule(manager, sound_manager)

    def cleanup(self) -> bool:
        """Cleanup firewall rule on exit"""
        if self.rule_exists():
            cmd = f'netsh advfirewall firewall delete rule name="{self.rule_name}"'
            subprocess.run(cmd, shell=True, capture_output=True, 
                          creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        return False



class ProcessManager:
    """Manages external process operations"""

    @staticmethod
    def is_admin() -> bool:
        """Check if running with admin privileges"""
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @staticmethod
    def run_as_admin() -> None:
        """Restart script with admin privileges, preserving original directory"""
        if ProcessManager.is_admin():
            return

        # Use the BASE_DIR we calculated above
        current_dir = str(BASE_DIR)
        executable = sys.executable
        
        # Build arguments correctly for both Script and EXE modes
        if hasattr(sys, 'frozen') or "__compiled__" in globals():
            # For EXE: Just pass the original arguments
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        else:
            # For Script: Must pass the script path (sys.argv[0]) first
            params = f'"{sys.argv[0]}" ' + " ".join([f'"{arg}"' for arg in sys.argv[1:]])

        try:
            # The 'current_dir' here is what keeps your config.yaml out of Temp/System32
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", executable, params, current_dir, 1
            )
        except Exception as e:
            console.print(f"[red]Failed to elevate: {e}[/red]")
            
        sys.exit()

    @staticmethod
    def kill_process(process_name: str, manager: OverlayManager) -> None:
        """Kill a process by name"""
        try:
            result = subprocess.run(
                f'taskkill /F /IM {process_name}',
                shell=True, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                console.print(f"✓ {process_name} process [bold red]KILLED[/bold red]", style="green")
                manager.show_notification("PROCESS TERMINATED", 
                                        f"{process_name} has been closed", "#ef4444")
            else:
                console.print(f"✗ {process_name} process not found or already closed", 
                            style="yellow")
                manager.show_notification("PROCESS NOT FOUND", 
                                        f"{process_name} is not running", "#f59e0b")
        except Exception as e:
            console.print(f"✗ Failed to kill {process_name}: {e}", style="red")
            manager.show_notification("ERROR", f"Failed to terminate {process_name}", "#ef4444")
        console.print()



class SolverManager:
    """Manages heist solver operations"""

    def __init__(self, manager: OverlayManager):
        self.manager = manager

    def _run_solver(self, solver_func, name: str, emoji: str) -> None:
        """Generic solver runner"""
        if not SOLVERS_AVAILABLE:
            console.print("[red]✗[/red] Hack modules not available", style="red")
            return

        console.print(f"[cyan]➤[/cyan] Running {name}...", style="cyan")
        self.manager.show_notification(name, "Active", "#a855f7")
        bbox = self.manager.get_window_bbox()

        if bbox:
            Thread(target=solver_func, args=(bbox,), daemon=True).start()

    def casino_fingerprint(self) -> None:
        self._run_solver(casinofingerprint.main, "CASINO SOLVER 🎰", "Fingerprint hack")

    def casino_keypad(self) -> None:
        self._run_solver(casinokeypad.main, "CASINO SOLVER 🎰", "Keypad hack")

    def cayo_fingerprint(self) -> None:
        self._run_solver(cayofingerprint.main, "CAYO PERICO 🏝️", "Fingerprint hack")

    def cayo_voltage(self) -> None:
        self._run_solver(cayovoltage.main, "CAYO PERICO 🏝️", "Voltage hack")



class ExploitManager:
    """Manages exploit operations"""

    def __init__(self, manager: OverlayManager):
        self.manager = manager

    def job_warp(self) -> None:
        """Execute job warp exploit"""
        if not JOBWARP_AVAILABLE:
            console.print("[red]✗[/red] Job warp module not available", style="red")
            self.manager.show_notification("ERROR", "Job warp not available", "#ef4444")
            return

        bbox = self.manager.get_window_bbox()
        if not bbox:
            console.print("[red]✗[/red] GTA V window not found", style="red")
            self.manager.show_notification("ERROR", "GTA V window not detected", "#ef4444")
            return

        console.print("[cyan]➤[/cyan] Triggering Job Warp exploit...", style="cyan")
        self.manager.show_notification("JOB WARP 🚀", "Exploit triggered", "#c084fc")
        Thread(target=jobwarp.main, args=(bbox, self.manager), daemon=True).start()



class UpdateChecker:
    """Checks for updates from GitHub releases"""

    REPO_OWNER = "ItsCEED"
    REPO_NAME = "vkit-toolbox"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    RELEASES_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"

    def __init__(self, current_version: str):
        self.current_version = current_version.lstrip('v')  # Remove 'v' prefix if present
        self.latest_version = None
        self.update_available = False
        self.download_url = None

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """Parse version string to tuple for comparison"""
        try:
            # Remove 'v' prefix and split by '.'
            clean_version = version_str.lstrip('v').split('-')[0]  # Handle v2.9-beta etc
            parts = clean_version.split('.')
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def check_for_updates(self, timeout: int = 3) -> bool:
        """Check if a newer version is available on GitHub"""
        try:
            # Create request with timeout
            req = urllib.request.Request(
                self.API_URL,
                headers={'User-Agent': f'{self.REPO_NAME}/{self.current_version}'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))

                    # Get latest version from tag_name
                    self.latest_version = data.get('tag_name', '').lstrip('v')
                    self.download_url = data.get('html_url', self.RELEASES_URL)

                    # Compare versions
                    current = self._parse_version(self.current_version)
                    latest = self._parse_version(self.latest_version)

                    self.update_available = latest > current
                    return self.update_available

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Update check failed: {e}")
            return False

        return False

    def get_update_message(self) -> str:
        """Get formatted update message"""
        if self.update_available and self.latest_version:
            return (
                f"🔔 Update Available: v{self.latest_version} "
                f"(Current: v{self.current_version})\n"
                f"Download: {self.download_url}"
            )
        return ""

    def print_update_notification(self):
        """Print update notification if available"""
        if self.update_available:
            update_panel = Panel(
                f"[bold yellow]🔔 NEW VERSION AVAILABLE![/bold yellow]\n\n"
                f"Current version: [cyan]v{self.current_version}[/cyan]\n"
                f"Latest version:  [green]v{self.latest_version}[/green]\n\n"
                f"[dim]Download from:[/dim] [link={self.download_url}]{self.download_url}[/link]",
                title="✨ [bold]Update Checker[/bold]",
                border_style="yellow",
                box=box.DOUBLE,
                width=70,
                padding=(1, 2)
            )
            console.print(update_panel)
            console.print()



class UIManager:
    """Manages UI display and instructions"""

    @staticmethod
    def print_header() -> None:
        """Print application header"""
        console.clear()
        console.print()

        title = Text()
        title.append(APP_TITLE, style="bold cyan")
        title.append(" | ", style="white")
        title.append(VERSION, style="dim yellow")

        console.print(Panel(Align.center(title), box=box.DOUBLE, 
                          border_style="bright_cyan", padding=(0, 2)))
        console.print()

    @staticmethod
    def _format_hotkey(hotkey_str: str) -> str:
        """Format hotkey string for display"""
        parts = [p.strip().upper() for p in hotkey_str.split('+')]
        return ' + '.join(parts)

    @staticmethod
    def print_hotkeys(config: AppConfig) -> None:
        """Print hotkeys table from config"""
        hotkeys_table = Table(
            title="🎮  [bold]Hotkeys[/bold]",
            box=box.ROUNDED, border_style="magenta",
            show_header=True, header_style="bold magenta", width=70
        )
        hotkeys_table.add_column("Shortcut", style="bold magenta", width=25)
        hotkeys_table.add_column("Action", style="white", width=38)

        hk = config.hotkeys

        # Core hotkeys
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['toggle_overlay']), 
            "Toggle overlay mode (Full ↔ Mini)"
        )
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['toggle_nosave']), 
            "Toggle NOSAVE (ON ↔ OFF)"
        )
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['debug_toggle']), 
            "🐛 Toggle Debug Mode"
        )
        hotkeys_table.add_row("", "")

        # Tool hotkeys
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['autoclicker']), 
            "⚡ Toggle Fast Autoclicker (50 CPS)"
        )
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['snack_spammer']), 
            "🍔 Toggle Snack Spammer (Hold TAB)"
        )
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['anti_afk']), 
            "🎮 Toggle Anti-AFK (S+A ↔ S+D)"
        )
        hotkeys_table.add_row(
            UIManager._format_hotkey(hk['kill_gta']), 
            "💀 Kill GTA5 Process (Instant)"
        )

        # Optional features
        if JOBWARP_AVAILABLE:
            hotkeys_table.add_row("", "")
            hotkeys_table.add_row(
                UIManager._format_hotkey(hk['job_warp']), 
                "🚀 Job Warp Exploit (Toggle)"
            )

        if SOLVERS_AVAILABLE:
            hotkeys_table.add_row("", "")
            hotkeys_table.add_row(
                UIManager._format_hotkey(hk['casino_fingerprint']), 
                "Casino Fingerprint Solver"
            )
            hotkeys_table.add_row(
                UIManager._format_hotkey(hk['casino_keypad']), 
                "Casino Keypad Solver"
            )
            hotkeys_table.add_row(
                UIManager._format_hotkey(hk['cayo_fingerprint']), 
                "Cayo Perico Fingerprint Solver"
            )
            hotkeys_table.add_row(
                UIManager._format_hotkey(hk['cayo_voltage']), 
                "Cayo Perico Voltage Solver"
            )

        console.print(hotkeys_table)
        console.print()

    @staticmethod
    def print_status(config: AppConfig) -> None:

        # Running status
        console.print(
            Panel(
                "[bold green]●[/bold green] Script is running... "
                "Press [bold red]CTRL+C[/bold red] to exit\n"
                f"[dim]Press {UIManager._format_hotkey(config.hotkeys['debug_toggle'])} to toggle debug mode[/dim]",
                box=box.HEAVY, border_style="bright_green", width=70, padding=(0, 2)
            )
        )
        console.print()



class HotkeyHandler:
    """Handles all hotkey detection and routing - ROBUST version"""

    def __init__(
        self,
        config: AppConfig,
        manager: OverlayManager,
        sound_manager: SoundManager,
        firewall_manager: FirewallManager,
        autoclicker: AutoClicker,
        snack_spammer: SnackSpammer,
        anti_afk: AntiAFK,
        solver_manager: SolverManager,
        exploit_manager: ExploitManager,
    ):
        self.config = config
        self.manager = manager
        self.sound_manager = sound_manager
        self.firewall_manager = firewall_manager
        self.autoclicker = autoclicker
        self.snack_spammer = snack_spammer
        self.anti_afk = anti_afk
        self.solver_manager = solver_manager
        self.exploit_manager = exploit_manager
        self.current_keys: set = set()
        self._triggered_combos: set = set()  # CHANGED: Just track which actions were triggered
        self._lock = threading.Lock()

        # Initialize window focus manager
        self.focus_manager = WindowFocusManager(GTA_PROCESS_NAME)
        self.require_game_focus = config.require_game_focus
        self.auto_stop_on_unfocus = config.auto_stop_on_unfocus

        # Register focus change callback
        if self.auto_stop_on_unfocus:
            self.focus_manager.register_focus_callback(self._on_focus_change)
            self.focus_manager.start_monitoring()

        # Parse hotkeys into key combination sets
        self.hotkeys = {}
        for action, hotkey_str in config.hotkeys.items():
            self.hotkeys[action] = self._parse_hotkey_to_set(hotkey_str)
            if DEBUG:
                print(f"[DEBUG] Parsed {action}: {hotkey_str} -> {self.hotkeys[action]}")

    def _parse_hotkey_to_set(self, hotkey_str: str) -> set:
        """Parse hotkey string - USE from_char() for character keys"""
        parts = [p.strip().lower() for p in hotkey_str.split('+')]
        key_set = set()

        # Map of string to keyboard keys
        key_map = {
            'ctrl': keyboard.Key.ctrl,
            'alt': keyboard.Key.alt,
            'shift': keyboard.Key.shift,
            'f1': keyboard.Key.f1, 'f2': keyboard.Key.f2, 'f3': keyboard.Key.f3,
            'f4': keyboard.Key.f4, 'f5': keyboard.Key.f5, 'f6': keyboard.Key.f6,
            'f7': keyboard.Key.f7, 'f8': keyboard.Key.f8, 'f9': keyboard.Key.f9,
            'f10': keyboard.Key.f10, 'f11': keyboard.Key.f11, 'f12': keyboard.Key.f12,
            'space': keyboard.Key.space, 'enter': keyboard.Key.enter,
            'tab': keyboard.Key.tab, 'esc': keyboard.Key.esc,
        }

        for part in parts:
            if part in key_map:
                key_set.add(key_map[part])
            else:
                # Use from_char() to create KeyCode
                key_set.add(keyboard.KeyCode.from_char(part))

        return key_set

    def _normalize_key(self, key):
        """Normalize keys - MUST match parsing method"""
        try:
            # Normalize modifier keys (treat left and right as same)
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return keyboard.Key.ctrl
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                return keyboard.Key.alt
            if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                return keyboard.Key.shift

            # For character keys with vk code
            if hasattr(key, 'vk') and key.vk:
                # Convert VK codes to characters, then use from_char()
                if 65 <= key.vk <= 90:  # A-Z
                    char = chr(key.vk + 32)  # lowercase
                    return keyboard.KeyCode.from_char(char)
                elif 48 <= key.vk <= 57:  # 0-9
                    char = chr(key.vk)
                    return keyboard.KeyCode.from_char(char)

            # If key has char attribute, use from_char()
            if hasattr(key, 'char') and key.char:
                return keyboard.KeyCode.from_char(key.char.lower())

            # For function keys and special keys, return as-is
            return key

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Key normalization error: {e}")
            return key

    def _on_focus_change(self, is_focused: bool):
        """Called when GTA focus state changes"""
        try:
            if not is_focused:
                stopped_tools = []

                if self.autoclicker.active:
                    self.autoclicker.stop()
                    stopped_tools.append("Auto Clicker")

                if self.snack_spammer.active:
                    self.snack_spammer.stop()
                    stopped_tools.append("Snack Spammer")

                if self.anti_afk.active:
                    self.anti_afk.stop()
                    stopped_tools.append("Anti-AFK")

                # Clear keyboard state on focus loss
                with self._lock:
                    self.current_keys.clear()
                    self._triggered_combos.clear()

                if stopped_tools:
                    tools_str = ", ".join(stopped_tools)
                    console.print(f"[yellow]⏸[/yellow] Alt+Tab detected - Stopped: {tools_str}",
                                style="yellow")
                    self.manager.show_notification(
                        "AUTO-STOPPED",
                        f"Tools paused: {tools_str}",
                        "#f59e0b"
                    )

                    if DEBUG:
                        print(f"[DEBUG] Focus lost - Stopped tools: {tools_str}")
            else:
                if DEBUG:
                    print("[DEBUG] GTA regained focus")
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Focus callback error: {e}")

    def _toggle_overlay_mode(self) -> None:
        self.manager.toggle_mode()
        self.sound_manager.play_toggle()

        if self.manager.show_full:
            console.print("◉ Switched to [bold cyan]FULL[/bold cyan] overlay mode", style="blue")
            self.manager.show_notification("OVERLAY MODE", "Full display enabled", "#3b82f6")
        else:
            console.print("◉ Switched to [bold cyan]MINI[/bold cyan] overlay mode (glowing indicator)",
                        style="blue")
            self.manager.show_notification("OVERLAY MODE", "Compact indicator active", "#3b82f6")
        console.print()

    def _toggle_debug(self) -> None:
        global DEBUG
        DEBUG = not DEBUG
        status = "ENABLED" if DEBUG else "DISABLED"
        console.print(f"🐛 DEBUG MODE [bold]{status}[/bold]", style="yellow")
        self.manager.show_notification("DEBUG MODE 🐛", status, "#f59e0b")
        console.print()

    def on_press(self, key) -> None:
        """Handle key press events - IMPROVED logic"""
        try:
            normalized_key = self._normalize_key(key)

            if DEBUG:
                print(f"[DEBUG] Key pressed: {key} -> {normalized_key}")

            with self._lock:
                # Add key to current set
                self.current_keys.add(normalized_key)

                if DEBUG:
                    print(f"[DEBUG]   Current keys: {self.current_keys}")
                    print(f"[DEBUG]   Triggered combos: {self._triggered_combos}")

                # Check if GTA is focused (if required)
                if self.require_game_focus and not self.focus_manager.is_gta_focused():
                    if DEBUG:
                        print("[DEBUG]   GTA not focused - ignoring")
                    return

                # Check if any hotkey combination is now complete
                for action, key_combo in self.hotkeys.items():
                    # Skip if already triggered
                    if action in self._triggered_combos:
                        continue

                    # Check if combo is pressed
                    if key_combo.issubset(self.current_keys):
                        # Mark as triggered
                        self._triggered_combos.add(action)

                        if DEBUG:
                            print(f"[DEBUG] ✓✓✓ HOTKEY MATCHED: {action}")
                            print(f"[DEBUG]   Expected: {key_combo}")
                            print(f"[DEBUG]   Current: {self.current_keys}")

                        # Execute action in separate thread to avoid blocking
                        threading.Thread(
                            target=self._handle_action,
                            args=(action,),
                            daemon=True
                        ).start()

                        break  # Only trigger one action per keypress

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] on_press error: {e}")
                import traceback
                traceback.print_exc()

    def _handle_action(self, action: str) -> None:
        """Route action to appropriate handler"""
        try:
            handlers = {
                'toggle_overlay': self._toggle_overlay_mode,
                'toggle_nosave': lambda: self.firewall_manager.toggle_rule(
                    self.manager, self.sound_manager),
                'debug_toggle': self._toggle_debug,
                'autoclicker': lambda: self._toggle_tool(
                    self.autoclicker, "AUTO CLICKER ⚡"),
                'snack_spammer': lambda: self._toggle_tool(
                    self.snack_spammer, "SNACK SPAMMER 🍔", extra=" (Hold TAB)"),
                'anti_afk': lambda: self._toggle_tool(
                    self.anti_afk, "ANTI-AFK 🎮", extra=" (S+A ↔ S+D)"),
                'kill_gta': lambda: ProcessManager.kill_process(GTA_PROCESS_NAME, self.manager),
                'job_warp': self.exploit_manager.job_warp,
                'casino_fingerprint': self.solver_manager.casino_fingerprint,
                'casino_keypad': self.solver_manager.casino_keypad,
                'cayo_fingerprint': self.solver_manager.cayo_fingerprint,
                'cayo_voltage': self.solver_manager.cayo_voltage,
            }

            handler = handlers.get(action)
            if handler:
                handler()
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Action handler error for {action}: {e}")
                import traceback
                traceback.print_exc()

    def _toggle_tool(self, tool, name: str, extra: str = "") -> None:
        """Toggle a tool on/off"""
        try:
            console.print(f"[bold green]✓ HOTKEY DETECTED - TOGGLING {name}[/bold green]")
            tool.toggle()
            if tool.active:
                self.manager.show_notification(name, f"ENABLED{extra}", "#10b981")
            else:
                self.manager.show_notification(name, "DISABLED", "#ef4444")
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Tool toggle error: {e}")

    def on_release(self, key) -> None:
        """Handle key release events - IMPROVED: Clear combos when ANY key released"""
        try:
            normalized_key = self._normalize_key(key)

            if DEBUG:
                print(f"[DEBUG] Key released: {key} -> {normalized_key}")

            with self._lock:
                # Remove key from current set
                self.current_keys.discard(normalized_key)

                if DEBUG:
                    print(f"[DEBUG]   Remaining keys: {self.current_keys}")

                # IMPROVED: Clear ALL triggered combos that included this key
                combos_to_clear = []
                for action in list(self._triggered_combos):
                    key_combo = self.hotkeys[action]

                    # If this combo contained the released key
                    if normalized_key in key_combo:
                        combos_to_clear.append(action)
                        if DEBUG:
                            print(f"[DEBUG]   Clearing combo {action} (contained released key)")
                    # OR if the combo is no longer fully pressed
                    elif not key_combo.issubset(self.current_keys):
                        combos_to_clear.append(action)
                        if DEBUG:
                            print(f"[DEBUG]   Clearing combo {action} (no longer fully pressed)")

                # Clear the combos
                for action in combos_to_clear:
                    self._triggered_combos.discard(action)

                if DEBUG and combos_to_clear:
                    print(f"[DEBUG]   Cleared {len(combos_to_clear)} combo(s)")
                    print(f"[DEBUG]   Remaining triggered: {self._triggered_combos}")

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] on_release error: {e}")
                import traceback
                traceback.print_exc()

    def start_listening(self) -> None:
        """Start the keyboard listener with error recovery"""
        while True:
            try:
                if DEBUG:
                    print("[DEBUG] Starting keyboard listener...")

                with keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release,
                    suppress=False
                ) as listener:
                    listener.join()

            except Exception as e:
                if DEBUG:
                    print(f"[DEBUG] Keyboard listener died: {e}")
                    import traceback
                    traceback.print_exc()

                time.sleep(1)
                if DEBUG:
                    print("[DEBUG] Restarting keyboard listener...")


def cleanup(
    autoclicker: AutoClicker,
    snack_spammer: SnackSpammer,
    anti_afk: AntiAFK,
    firewall_manager: FirewallManager
) -> None:
    """Cleanup all resources before exit"""
    for tool in (autoclicker, snack_spammer, anti_afk):
        if tool.active:
            tool.stop()

    if firewall_manager.cleanup():
        console.print("\n✓ Cleanup: Firewall rule removed", style="green")



def disable_console_quickedit() -> None:
    """Silently disable Windows console QuickEdit mode to prevent click-freeze"""
    if sys.platform != "win32":
        return

    try:
        kernel32 = ctypes.windll.kernel32
        h_console = kernel32.GetStdHandle(-10)
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(h_console, ctypes.byref(mode))
        kernel32.SetConsoleMode(h_console, mode.value & ~0x0040 & ~0x0020 | 0x0080)
    except Exception:
        pass



def main() -> None:
    """Main application entry point"""
    global DEBUG

    # Check for debug flag
    if "--debug" in sys.argv:
        DEBUG = True
        console.print("[bold yellow]🐛 DEBUG MODE ENABLED[/bold yellow]")
        console.print()

    # Ensure admin privileges
    ProcessManager.run_as_admin()
    ctypes.windll.user32.SetProcessDPIAware()

    # Prevent console click-freeze
    disable_console_quickedit()

    # Load configuration
    config = AppConfig.load(CONFIG_PATH)

    # Initialize managers
    sound_manager = SoundManager()
    firewall_manager = FirewallManager(config)
    overlay_manager = OverlayManager()

    # Initialize tools
    autoclicker = AutoClicker(sound_manager)
    snack_spammer = SnackSpammer(sound_manager)
    anti_afk = AntiAFK(sound_manager)

    # Initialize feature managers
    solver_manager = SolverManager(overlay_manager)
    exploit_manager = ExploitManager(overlay_manager)

    # Display UI
    UIManager.print_header()

    # Check for updates (non-blocking with timeout)
    console.print("[dim]⏳ Checking for updates...[/dim]", end="")
    update_checker = UpdateChecker(VERSION)
    if update_checker.check_for_updates():
        console.print(" [yellow]✓[/yellow]")
        update_checker.print_update_notification()
    else:
        console.print(" [green]✓[/green] [dim](up to date)[/dim]")
    console.print()

    UIManager.print_hotkeys(config)

    initial_status = "ON" if firewall_manager.rule_exists() else "OFF"
    UIManager.print_status(config)

    overlay_manager.update_status(initial_status)

    # Setup hotkey handler
    hotkey_handler = HotkeyHandler(
        config, overlay_manager, sound_manager, firewall_manager,
        autoclicker, snack_spammer, anti_afk, solver_manager, exploit_manager
    )

    # Register cleanup on exit
    atexit.register(cleanup, autoclicker, snack_spammer, anti_afk, firewall_manager)

    # Start listener thread
    listener_thread = threading.Thread(target=hotkey_handler.start_listening, daemon=True)
    listener_thread.start()

    # Run overlay manager (blocks until exit)
    try:
        overlay_manager.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow] Shutting down...", style="bold")
    finally:
        console.print("✓ Script terminated successfully\n", style="green bold")



if __name__ == "__main__":
    main()