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
from typing import Callable
from concurrent.futures import ThreadPoolExecutor

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

from solvers import casinofingerprint, casinokeypad, cayofingerprint, cayovoltage
from exploits import jobwarp


console = Console()

# Constants
VERSION = "v3.3.0"
APP_TITLE = "VKit - Toolbox"
GTA_PROCESS_NAME = "GTA5_Enhanced.exe"

# Thread pool for async operations (bounded to prevent memory leaks)
THREAD_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="vkit_worker")

# Smart pathing
def get_base_dir() -> Path:
    """Get the directory containing the actual .exe or script"""
    if sys.argv[0].endswith('.exe'):
        return Path(sys.argv[0]).parent.resolve()

    exe_path = Path(sys.executable).resolve()
    exe_name = exe_path.name.lower()

    if 'python' not in exe_name and 'temp' not in str(exe_path).lower():
        return exe_path.parent

    return Path(__file__).parent.resolve()


BASE_DIR = get_base_dir()
CONFIG_PATH = BASE_DIR / "config.yaml"
ASSETS_DIR = Path(__file__).parent

# Debug mode
DEBUG = False


@dataclass
class AppConfig:
    """Application configuration"""
    __slots__ = ('rule_name', 'remote_ip', 'test_port', 'hotkeys', 
                 'require_game_focus', 'auto_stop_on_unfocus')

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
    """EVENT-DRIVEN window focus detection - WITH MANUAL REFRESH"""

    EVENT_SYSTEM_FOREGROUND = 0x0003
    WINEVENT_OUTOFCONTEXT = 0x0000

    def __init__(self, process_name: str = "GTA5_Enhanced.exe"):
        self.process_name = process_name.lower()
        self.gta_titles = frozenset(['grand theft auto v', 'gta5', 'rockstar games'])

        self._is_focused = False
        self._callbacks = []
        self._hook_id = None
        self._shutdown = threading.Event()

        # Unified cache
        self._cache = {'hwnd': None, 'pid': None, 'process': None, 'title': None}
        self._cache_lock = threading.Lock()

        # Windows hook setup
        self._hook_func = ctypes.WINFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_uint,
            ctypes.c_uint
        )(self._on_window_focus_change)

    def _get_window_info(self, hwnd) -> tuple:
        """Get all window info"""
        with self._cache_lock:
            if hwnd == self._cache['hwnd']:
                return self._cache['process'], self._cache['title']

            try:
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                try:
                    process = psutil.Process(pid).name().lower()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process = None

                # Update cache
                self._cache.update({
                    'hwnd': hwnd,
                    'pid': pid,
                    'process': process,
                    'title': title
                })

                return process, title
            except Exception:
                return None, ""

    def _check_is_gta(self, process_name, title) -> bool:
        """Check if window is GTA"""
        if process_name == self.process_name:
            return True
        if title:
            title_lower = title.lower()
            return any(gta in title_lower for gta in self.gta_titles)
        return False

    def _on_window_focus_change(self, hook, event, hwnd, id_object, id_child, thread, time):
        """Windows hook callback"""
        try:
            if self._shutdown.is_set():
                return

            process_name, title = self._get_window_info(hwnd)
            is_gta = self._check_is_gta(process_name, title)

            # Only trigger callbacks on STATE CHANGE
            if is_gta != self._is_focused:
                self._is_focused = is_gta

                for callback in self._callbacks[:]:
                    THREAD_POOL.submit(self._safe_callback, callback, is_gta)

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Focus hook error: {e}")

    def _safe_callback(self, callback, is_focused: bool):
        """Execute callback with error handling"""
        try:
            callback(is_focused)
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Focus callback error: {e}")

    def register_focus_callback(self, callback):
        """Register callback"""
        self._callbacks.append(callback)

    def is_gta_focused(self) -> bool:
        """Get current focus state"""
        return self._is_focused

    def force_refresh_focus_state(self):
        """⭐ NEW: Manually check and update focus state"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            process_name, title = self._get_window_info(hwnd)
            is_gta = self._check_is_gta(process_name, title)

            old_state = self._is_focused
            self._is_focused = is_gta

            if DEBUG:
                print(f"[DEBUG] Force refresh: focus={is_gta} (was {old_state})")

            # Trigger callbacks if state changed
            if is_gta != old_state:
                for callback in self._callbacks[:]:
                    THREAD_POOL.submit(self._safe_callback, callback, is_gta)

            return is_gta
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Force refresh error: {e}")
            return self._is_focused

    def start_monitoring(self):
        """Start EVENT-DRIVEN monitoring"""
        def hook_thread():
            try:
                user32 = ctypes.windll.user32

                self._hook_id = user32.SetWinEventHook(
                    self.EVENT_SYSTEM_FOREGROUND,
                    self.EVENT_SYSTEM_FOREGROUND,
                    0,
                    self._hook_func,
                    0,
                    0,
                    self.WINEVENT_OUTOFCONTEXT
                )

                if not self._hook_id:
                    raise RuntimeError("Failed to set Windows event hook")

                if DEBUG:
                    print("[DEBUG] ✓ Windows event hook installed")

                # Check initial state
                try:
                    hwnd = win32gui.GetForegroundWindow()
                    self._on_window_focus_change(None, self.EVENT_SYSTEM_FOREGROUND, hwnd, 0, 0, 0, 0)
                except Exception:
                    pass

                # Message loop
                msg = ctypes.wintypes.MSG()
                while not self._shutdown.is_set():
                    if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                    else:
                        self._shutdown.wait(0.1)

            except Exception as e:
                if DEBUG:
                    print(f"[DEBUG] Hook thread error: {e}")
            finally:
                if self._hook_id:
                    user32.UnhookWinEvent(self._hook_id)

        threading.Thread(target=hook_thread, daemon=True, name="focus_monitor").start()

    def stop_monitoring(self):
        """Stop monitoring"""
        self._shutdown.set()


class SoundManager:
    """Manages sound effects - OPTIMIZED with thread pool"""

    SOUND_FILES = {'on': 'on.wav', 'off': 'off.wav', 'toggle': 'toggle.wav'}

    def __init__(self):
        self.sounds_dir = ASSETS_DIR / "assets" / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        self.sounds = {}
        for key, filename in self.SOUND_FILES.items():
            path = self.sounds_dir / filename
            self.sounds[key] = str(path) if path.exists() else None

    def play(self, sound_type: str):
        """Play sound asynchronously using thread pool"""
        path = self.sounds.get(sound_type)
        if path:
            THREAD_POOL.submit(self._play_sound, path)

    @staticmethod
    def _play_sound(path: str):
        """Internal sound player"""
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    def play_on(self):
        self.play('on')

    def play_off(self):
        self.play('off')

    def play_toggle(self):
        self.play('toggle')


class FirewallManager:
    """Manages firewall rules"""

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
        """Test if IP is blocked"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                return sock.connect_ex((self.remote_ip, self.test_port)) != 0
        except Exception:
            return True

    def add_rule(self, manager: OverlayManager, sound_manager: SoundManager):
        """Add firewall blocking rule"""
        cmd = (f'netsh advfirewall firewall add rule name="{self.rule_name}" '
               f'dir=out action=block remoteip="{self.remote_ip}"')
        subprocess.run(cmd, shell=True, capture_output=True,
                      creationflags=subprocess.CREATE_NO_WINDOW)

        time.sleep(0.5)
        if self.rule_exists():
            console.print("✓ NO SAVING MODE [bold red]ENABLED[/bold red]", style="green")
            manager.update_status("ON")
            manager.show_notification("NOSAVE MODE", "Session protection enabled", "#ef4444")
            sound_manager.play_on()

            if self.test_ip_blocked():
                console.print(f"✓ Connection to [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                            f"is [bold red]BLOCKED[/bold red]", style="green")
        else:
            console.print("✗ Failed to add firewall rule", style="red")
        console.print()

    def delete_rule(self, manager: OverlayManager, sound_manager: SoundManager):
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
                console.print(f"✓ Connection to [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                            f"is [bold green]ACCESSIBLE[/bold green]", style="green")
        else:
            console.print("✗ Failed to delete firewall rule", style="red")
        console.print()

    def toggle_rule(self, manager: OverlayManager, sound_manager: SoundManager):
        """Toggle firewall rule"""
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
    def run_as_admin():
        """Restart script with admin privileges"""
        if ProcessManager.is_admin():
            return

        current_dir = str(BASE_DIR)
        executable = sys.executable

        if hasattr(sys, 'frozen') or "__compiled__" in globals():
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        else:
            params = f'"{sys.argv[0]}" ' + " ".join([f'"{arg}"' for arg in sys.argv[1:]])

        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, current_dir, 1)
        except Exception as e:
            console.print(f"[red]Failed to elevate: {e}[/red]")

        sys.exit()

    @staticmethod
    def kill_process(process_name: str, manager: OverlayManager):
        """Kill a process by name"""
        try:
            result = subprocess.run(f'taskkill /F /IM {process_name}', shell=True,
                                  capture_output=True, text=True,
                                  creationflags=subprocess.CREATE_NO_WINDOW)

            if result.returncode == 0:
                console.print(f"✓ {process_name} process [bold red]KILLED[/bold red]", style="green")
                manager.show_notification("PROCESS TERMINATED",
                                        f"{process_name} has been closed", "#ef4444")
            else:
                console.print(f"✗ {process_name} process not found or already closed", style="yellow")
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

    def _run_solver(self, solver_func, name: str):
        """Generic solver runner"""

        console.print(f"[cyan]➤[/cyan] Running {name}...", style="cyan")
        self.manager.show_notification(name, "Active", "#a855f7")
        bbox = self.manager.get_window_bbox()

        if bbox:
            THREAD_POOL.submit(solver_func, bbox)

    def casino_fingerprint(self):
        self._run_solver(casinofingerprint.main, "CASINO SOLVER 🎰")

    def casino_keypad(self):
        self._run_solver(casinokeypad.main, "CASINO SOLVER 🎰")

    def cayo_fingerprint(self):
        self._run_solver(cayofingerprint.main, "CAYO PERICO 🏝️")

    def cayo_voltage(self):
        self._run_solver(cayovoltage.main, "CAYO PERICO 🏝️")


class ExploitManager:
    """Manages exploit operations"""

    def __init__(self, manager: OverlayManager):
        self.manager = manager

    def job_warp(self):
        """Execute job warp exploit"""
        bbox = self.manager.get_window_bbox()
        if not bbox:
            console.print("[red]✗[/red] GTA V window not found", style="red")
            self.manager.show_notification("ERROR", "GTA V window not detected", "#ef4444")
            return

        console.print("[cyan]➤[/cyan] Triggering Job Warp exploit...", style="cyan")
        self.manager.show_notification("JOB WARP 🚀", "Exploit triggered", "#c084fc")
        THREAD_POOL.submit(jobwarp.main, bbox, self.manager)


class UpdateChecker:
    """Checks for updates from GitHub releases"""

    REPO_OWNER = "ItsCEED"
    REPO_NAME = "vkit-toolbox"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    RELEASES_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"

    def __init__(self, current_version: str):
        self.current_version = current_version.lstrip('v')
        self.latest_version = None
        self.update_available = False
        self.download_url = None

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """Parse version string to tuple"""
        try:
            clean_version = version_str.lstrip('v').split('-')[0]
            return tuple(int(p) for p in clean_version.split('.'))
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def check_for_updates(self, timeout: int = 3) -> bool:
        """Check if newer version is available"""
        try:
            req = urllib.request.Request(
                self.API_URL,
                headers={'User-Agent': f'{self.REPO_NAME}/{self.current_version}'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))

                    self.latest_version = data.get('tag_name', '').lstrip('v')
                    self.download_url = data.get('html_url', self.RELEASES_URL)

                    current = self._parse_version(self.current_version)
                    latest = self._parse_version(self.latest_version)

                    self.update_available = latest > current
                    return self.update_available

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Update check failed: {e}")
            return False

        return False

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
    """Manages UI display"""

    @staticmethod
    def print_header():
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
        """Format hotkey string"""
        parts = [p.strip().upper() for p in hotkey_str.split('+')]
        return ' + '.join(parts)

    @staticmethod
    def print_hotkeys(config: AppConfig):
        """Print hotkeys table"""
        hotkeys_table = Table(
            title="🎮  [bold]Hotkeys[/bold]",
            box=box.ROUNDED, border_style="magenta",
            show_header=True, header_style="bold magenta", width=70
        )
        hotkeys_table.add_column("Shortcut", style="bold magenta", width=25)
        hotkeys_table.add_column("Action", style="white", width=38)

        hk = config.hotkeys

        hotkeys_table.add_row(UIManager._format_hotkey(hk['toggle_overlay']),
                            "Toggle overlay mode (Full ↔ Mini)")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['toggle_nosave']),
                            "Toggle NOSAVE (ON ↔ OFF)")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['debug_toggle']),
                            "🐛 Toggle Debug Mode")
        hotkeys_table.add_row("", "")

        hotkeys_table.add_row(UIManager._format_hotkey(hk['autoclicker']),
                            "⚡ Toggle Fast Autoclicker (50 CPS)")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['snack_spammer']),
                            "🍔 Toggle Snack Spammer (Hold TAB)")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['anti_afk']),
                            "🎮 Toggle Anti-AFK (S+A ↔ S+D)")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['kill_gta']),
                            "💀 Kill GTA5 Process (Instant)")

        hotkeys_table.add_row("", "")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['job_warp']),
                            "🚀 Job Warp Exploit (Toggle)")

        hotkeys_table.add_row("", "")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['casino_fingerprint']),
                            "Casino Fingerprint Solver")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['casino_keypad']),
                            "Casino Keypad Solver")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['cayo_fingerprint']),
                            "Cayo Perico Fingerprint Solver")
        hotkeys_table.add_row(UIManager._format_hotkey(hk['cayo_voltage']),
                            "Cayo Perico Voltage Solver")

        console.print(hotkeys_table)
        console.print()

    @staticmethod
    def print_status(config: AppConfig):
        """Print running status"""
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
    """Handles hotkey detection - FORCES focus refresh after restart"""

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

        self.current_keys = set()
        self.triggered = set()
        self._lock = threading.Lock()

        self._listener = None
        self._listener_lock = threading.Lock()
        self._should_run = True

        # Focus manager
        self.focus_manager = WindowFocusManager(GTA_PROCESS_NAME)
        self.require_game_focus = config.require_game_focus
        self.auto_stop_on_unfocus = config.auto_stop_on_unfocus

        if self.auto_stop_on_unfocus:
            self.focus_manager.register_focus_callback(self._on_focus_change)
            self.focus_manager.start_monitoring()

        # Pre-compute hotkeys
        self.hotkeys = {}
        for action, hotkey_str in config.hotkeys.items():
            self.hotkeys[action] = self._parse_hotkey(hotkey_str)
            if DEBUG:
                print(f"[DEBUG] Parsed {action}: {hotkey_str} -> {self.hotkeys[action]}")

    def _parse_hotkey(self, hotkey_str: str) -> frozenset:
        """Parse hotkey"""
        parts = [p.strip().lower() for p in hotkey_str.split('+')]
        keys = set()

        key_map = {
            'ctrl': keyboard.Key.ctrl, 'alt': keyboard.Key.alt, 'shift': keyboard.Key.shift,
            'f1': keyboard.Key.f1, 'f2': keyboard.Key.f2, 'f3': keyboard.Key.f3,
            'f4': keyboard.Key.f4, 'f5': keyboard.Key.f5, 'f6': keyboard.Key.f6,
            'f7': keyboard.Key.f7, 'f8': keyboard.Key.f8, 'f9': keyboard.Key.f9,
            'f10': keyboard.Key.f10, 'f11': keyboard.Key.f11, 'f12': keyboard.Key.f12,
            'space': keyboard.Key.space, 'enter': keyboard.Key.enter,
            'tab': keyboard.Key.tab, 'esc': keyboard.Key.esc,
        }

        for part in parts:
            keys.add(key_map.get(part, keyboard.KeyCode.from_char(part)))

        return frozenset(keys)

    def _normalize_key(self, key):
        """Normalize key"""
        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return keyboard.Key.ctrl
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                return keyboard.Key.alt
            if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                return keyboard.Key.shift

            if hasattr(key, 'vk') and key.vk:
                if 65 <= key.vk <= 90:
                    return keyboard.KeyCode.from_char(chr(key.vk + 32))
                elif 48 <= key.vk <= 57:
                    return keyboard.KeyCode.from_char(chr(key.vk))

            if hasattr(key, 'char') and key.char:
                return keyboard.KeyCode.from_char(key.char.lower())

            return key
        except Exception:
            return key

    def _on_focus_change(self, is_focused: bool):
        """Handle focus change"""
        if not is_focused:
            stopped = []

            for tool, name in [(self.autoclicker, "Auto Clicker"),
                             (self.snack_spammer, "Snack Spammer"),
                             (self.anti_afk, "Anti-AFK")]:
                if tool.active:
                    tool.stop()
                    stopped.append(name)

            with self._lock:
                self.current_keys.clear()
                self.triggered.clear()

            if stopped:
                tools_str = ", ".join(stopped)
                console.print(f"[yellow]⏸[/yellow] Alt+Tab detected - Stopped: {tools_str}",
                            style="yellow")
                self.manager.show_notification("AUTO-STOPPED",
                                             f"Tools paused: {tools_str}", "#f59e0b")
                if DEBUG:
                    print(f"[DEBUG] Focus lost - Stopped: {tools_str}")
        else:
            if DEBUG:
                print("[DEBUG] GTA regained focus - restarting listener...")

            with self._lock:
                self.current_keys.clear()
                self.triggered.clear()

            THREAD_POOL.submit(self._restart_listener)

    def _restart_listener(self):
        """Restart listener + force focus refresh"""
        try:
            with self._listener_lock:
                # Stop old listener
                if self._listener is not None:
                    try:
                        self._listener.stop()
                        if DEBUG:
                            print("[DEBUG] Stopped old listener")
                    except Exception as e:
                        if DEBUG:
                            print(f"[DEBUG] Error stopping listener: {e}")

                time.sleep(0.2)

                # Start new listener
                self._listener = keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release,
                    suppress=False
                )
                self._listener.start()

                if DEBUG:
                    print("[DEBUG] ✓ Listener restarted")

            # ⭐ CRITICAL: Force refresh focus state after restart
            time.sleep(0.1)  # Let listener initialize
            is_focused = self.focus_manager.force_refresh_focus_state()

            if DEBUG:
                print(f"[DEBUG] Focus state after restart: {is_focused}")

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Failed to restart listener: {e}")

    def on_press(self, key):
        """Handle key press"""
        try:
            normalized = self._normalize_key(key)

            if DEBUG:
                print(f"[DEBUG] Key pressed: {key} -> {normalized}")

            with self._lock:
                self.current_keys.add(normalized)

                if DEBUG:
                    print(f"[DEBUG]   Current keys: {self.current_keys}")
                    print(f"[DEBUG]   GTA focused: {self.focus_manager.is_gta_focused()}")

                # Skip if focus required but not focused
                if self.require_game_focus and not self.focus_manager.is_gta_focused():
                    if DEBUG:
                        print("[DEBUG]   GTA not focused - ignoring")
                    return

                # Check hotkey matches
                current_frozen = frozenset(self.current_keys)
                for action, combo in self.hotkeys.items():
                    if action not in self.triggered and combo.issubset(current_frozen):
                        self.triggered.add(action)

                        if DEBUG:
                            print(f"[DEBUG] ✓✓✓ HOTKEY MATCHED: {action}")

                        THREAD_POOL.submit(self._handle_action, action)
                        break

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Key press error: {e}")

    def on_release(self, key):
        """Handle key release"""
        try:
            normalized = self._normalize_key(key)

            if DEBUG:
                print(f"[DEBUG] Key released: {key} -> {normalized}")

            with self._lock:
                self.current_keys.discard(normalized)

                current_frozen = frozenset(self.current_keys)
                to_clear = [
                    action for action in self.triggered
                    if normalized in self.hotkeys[action] or not self.hotkeys[action].issubset(current_frozen)
                ]

                for action in to_clear:
                    self.triggered.discard(action)

                if DEBUG and to_clear:
                    print(f"[DEBUG]   Cleared combos: {to_clear}")

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Key release error: {e}")

    def _handle_action(self, action: str):
        """Route action to handler"""
        try:
            handlers = {
                'toggle_overlay': self._toggle_overlay,
                'toggle_nosave': lambda: self.firewall_manager.toggle_rule(
                    self.manager, self.sound_manager),
                'debug_toggle': self._toggle_debug,
                'autoclicker': lambda: self._toggle_tool(
                    self.autoclicker, "AUTO CLICKER ⚡"),
                'snack_spammer': lambda: self._toggle_tool(
                    self.snack_spammer, "SNACK SPAMMER 🍔", " (Hold TAB)"),
                'anti_afk': lambda: self._toggle_tool(
                    self.anti_afk, "ANTI-AFK 🎮", " (S+A ↔ S+D)"),
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
                print(f"[DEBUG] Action handler error: {e}")

    def _toggle_overlay(self):
        """Toggle overlay"""
        self.manager.toggle_mode()
        self.sound_manager.play_toggle()

        if self.manager.show_full:
            console.print("◉ Switched to [bold cyan]FULL[/bold cyan] overlay mode", style="blue")
            self.manager.show_notification("OVERLAY MODE", "Full display enabled", "#3b82f6")
        else:
            console.print("◉ Switched to [bold cyan]MINI[/bold cyan] overlay mode", style="blue")
            self.manager.show_notification("OVERLAY MODE", "Compact indicator active", "#3b82f6")
        console.print()

    def _toggle_debug(self):
        """Toggle debug"""
        global DEBUG
        DEBUG = not DEBUG
        status = "ENABLED" if DEBUG else "DISABLED"
        console.print(f"🐛 DEBUG MODE [bold]{status}[/bold]", style="yellow")
        self.manager.show_notification("DEBUG MODE 🐛", status, "#f59e0b")
        console.print()

    def _toggle_tool(self, tool, name: str, extra: str = ""):
        """Toggle tool"""
        tool.toggle()
        if tool.active:
            console.print(f"[bold green]✓ {name} ENABLED{extra}[/bold green]")
            self.manager.show_notification(name, f"ENABLED{extra}", "#10b981")
        else:
            console.print(f"[bold red]✗ {name} DISABLED[/bold red]")
            self.manager.show_notification(name, "DISABLED", "#ef4444")

    def start_listening(self):
        """Start listener"""
        if DEBUG:
            print("[DEBUG] Starting initial keyboard listener...")

        try:
            with self._listener_lock:
                self._listener = keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release,
                    suppress=False
                )
                self._listener.start()

            if DEBUG:
                print("[DEBUG] ✓ Listener started")

            while self._should_run:
                time.sleep(1)

        except KeyboardInterrupt:
            self._should_run = False
        finally:
            with self._listener_lock:
                if self._listener:
                    self._listener.stop()

def cleanup(autoclicker, snack_spammer, anti_afk, firewall_manager):
    """Cleanup resources"""
    for tool in (autoclicker, snack_spammer, anti_afk):
        if tool.active:
            tool.stop()

    if firewall_manager.cleanup():
        console.print("\n✓ Cleanup: Firewall rule removed", style="green")


def disable_console_quickedit():
    """Aggressively disable Windows console QuickEdit mode to prevent input freeze"""
    if sys.platform != "win32":
        return

    try:
        kernel32 = ctypes.windll.kernel32
        h_console = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(h_console, ctypes.byref(mode))
        
        # Disable ALL interactive modes
        ENABLE_QUICK_EDIT_MODE = 0x0040
        ENABLE_INSERT_MODE = 0x0020
        ENABLE_MOUSE_INPUT = 0x0010
        ENABLE_EXTENDED_FLAGS = 0x0080
        
        new_mode = mode.value
        new_mode &= ~ENABLE_QUICK_EDIT_MODE
        new_mode &= ~ENABLE_INSERT_MODE
        new_mode &= ~ENABLE_MOUSE_INPUT
        new_mode |= ENABLE_EXTENDED_FLAGS
        
        kernel32.SetConsoleMode(h_console, new_mode)
        
        if DEBUG:
            print(f"[DEBUG] Console mode changed: {mode.value:04x} -> {new_mode:04x}")
            
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Failed to disable QuickEdit: {e}")


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler to prevent crashes"""
    if DEBUG:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        console.print(f"[red]✗ Critical error: {exc_value}[/red]")


def main():
    """Main application entry point - OPTIMIZED"""
    global DEBUG

    # Set global exception handler
    sys.excepthook = global_exception_handler

    if "--debug" in sys.argv:
        DEBUG = True
        console.print("[bold yellow]🐛 DEBUG MODE ENABLED[/bold yellow]")
        console.print()

    ProcessManager.run_as_admin()
    ctypes.windll.user32.SetProcessDPIAware()
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

    # Check for updates
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

    # Register cleanup
    atexit.register(cleanup, autoclicker, snack_spammer, anti_afk, firewall_manager)

    # Start listener thread
    threading.Thread(target=hotkey_handler.start_listening, daemon=True,
                    name="hotkey_listener").start()

    # Run overlay manager (blocks until exit)
    try:
        overlay_manager.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow] Shutting down...", style="bold")
    finally:
        THREAD_POOL.shutdown(wait=False)
        console.print("✓ Script terminated successfully\n", style="green bold")


if __name__ == "__main__":
    main()
