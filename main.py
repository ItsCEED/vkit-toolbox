# Standard library imports
import atexit
import ctypes
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
import yaml
from pynput import keyboard
from rich.console import Console

# Local application imports
from assets.ui import  OverlayManager
from tools.autoclicker import AutoClicker, SnackSpammer, AntiAFK
from solvers import casinofingerprint, casinokeypad, cayofingerprint, cayovoltage
from exploits import jobwarp

from core.managers import (
    WindowFocusManager,
    SoundManager,
    FirewallManager,
    ProcessManager,
    GameDetector
)
from core.ui import UIManager, UpdateChecker

console = Console()

# Constants
VERSION = "v3.3.4"
APP_TITLE = "VKit - Toolbox"

THREAD_POOL = ThreadPoolExecutor(max_workers=15, thread_name_prefix="vkit_worker")
DEBUG = False


# ============================================================================
# CONFIGURATION & PATHS
# ============================================================================


def get_base_dir() -> Path:
    """Get the directory containing the actual .exe or script"""
    if sys.argv[0].endswith(".exe"):
        return Path(sys.argv[0]).parent.resolve()

    exe_path = Path(sys.executable).resolve()
    if "python" not in exe_path.name.lower() and "temp" not in str(exe_path).lower():
        return exe_path.parent

    return Path(__file__).parent.resolve()


BASE_DIR = get_base_dir()
CONFIG_PATH = BASE_DIR / "config.yaml"
ASSETS_DIR = Path(__file__).parent


@dataclass
class AppConfig:
    """Application configuration with simplified loading"""

    __slots__ = (
        "rule_name",
        "remote_ip",
        "test_port",
        "hotkeys",
        "require_game_focus",
        "auto_stop_on_unfocus",
    )

    rule_name: str
    remote_ip: str
    test_port: int
    hotkeys: dict
    require_game_focus: bool
    auto_stop_on_unfocus: bool

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        """Load or create configuration"""
        if not path.exists():
            cls._create_default_config(path)

        with open(path) as f:
            config = yaml.safe_load(f)

        fw = config["firewall"]
        return cls(
            rule_name=fw["rule_name"],
            remote_ip=fw["remote_ip"],
            test_port=fw["test_port"],
            hotkeys=config["hotkeys"],
            require_game_focus=config.get("require_game_focus", True),
            auto_stop_on_unfocus=config.get("auto_stop_on_unfocus", True),
        )

    @staticmethod
    def _create_default_config(path: Path) -> None:
        """Create default configuration file"""
        default_config = {
            "firewall": {
                "rule_name": "gtanosavemode_rule",
                "remote_ip": "192.81.241.171",
                "test_port": 80,
            },
            "require_game_focus": True,
            "auto_stop_on_unfocus": True,
            "hotkeys": {
                "toggle_overlay": "ctrl+f8",
                "toggle_nosave": "ctrl+f9",
                "autoclicker": "ctrl+k",
                "snack_spammer": "ctrl+c",
                "anti_afk": "ctrl+shift+a",
                "job_warp": "ctrl+shift+j",
                "debug_toggle": "ctrl+alt+shift+d",
                "kill_gta": "ctrl+shift+q",
                "casino_fingerprint": "f5",
                "casino_keypad": "f6",
                "cayo_fingerprint": "ctrl+f5",
                "cayo_voltage": "ctrl+f6",
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓[/green] Created default config at: {path}")


# ============================================================================
# FEATURE MANAGERS
# ============================================================================


class SolverManager:
    """Manages heist solver operations"""

    def __init__(self, manager: OverlayManager):
        self.manager = manager

    def _run_solver(self, solver_func: Callable, name: str):
        """Generic solver runner"""
        console.print(f"[cyan]➤[/cyan] Running {name}...", style="cyan")
        self.manager.show_notification(name, "Active", "#c084fc")

        if bbox := self.manager.get_window_bbox():
            THREAD_POOL.submit(solver_func, bbox)

    def casino_fingerprint(self):
        self._run_solver(casinofingerprint.main, "CASINO FINGERPRINT SOLVER 🎰")

    def casino_keypad(self):
        self._run_solver(casinokeypad.main, "CASINO KEYPAD SOLVER 🎰")

    def cayo_fingerprint(self):
        self._run_solver(cayofingerprint.main, "CAYO PERICO FINGERPRINT 🏝️")

    def cayo_voltage(self):
        self._run_solver(cayovoltage.main, "CAYO PERICO VOLTAGE 🏝️")

class ExploitManager:
    """Manages exploit operations"""

    def __init__(self, manager: OverlayManager):
        self.manager = manager

    def job_warp(self):
        """Execute job warp exploit"""
        if not (bbox := self.manager.get_window_bbox()):
            console.print("[red]✗[/red] GTA V window not found", style="red")
            self.manager.show_notification(
                "ERROR", "GTA V window not detected", "#FF3B5C"
            )
            return

        console.print("[cyan]➤[/cyan] Triggering Job Warp exploit...", style="cyan")
        self.manager.show_notification("JOB WARP 🚀", "Exploit triggered", "#c084fc")
        THREAD_POOL.submit(jobwarp.main, bbox, self.manager)


# ============================================================================
# HOTKEY HANDLER
# ============================================================================


class HotkeyHandler:
    """Handles hotkey detection with focus management"""

    # Pre-computed key mappings for hotkey parsing
    # Maps string names like 'ctrl', 'f5' to pynput Key objects
    KEY_MAP = {
        "ctrl": keyboard.Key.ctrl,
        "alt": keyboard.Key.alt,
        "shift": keyboard.Key.shift,
        **{f"f{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)},
        "space": keyboard.Key.space,
        "enter": keyboard.Key.enter,
        "tab": keyboard.Key.tab,
        "esc": keyboard.Key.esc,
    }

    # Normalizes left/right modifier variants to single key
    # Example: Key.ctrl_l and Key.ctrl_r both map to Key.ctrl
    MODIFIER_NORMALIZE = {
        keyboard.Key.ctrl_l: keyboard.Key.ctrl,
        keyboard.Key.ctrl_r: keyboard.Key.ctrl,
        keyboard.Key.alt_l: keyboard.Key.alt,
        keyboard.Key.alt_r: keyboard.Key.alt,
        keyboard.Key.alt_gr: keyboard.Key.alt,
        keyboard.Key.shift_l: keyboard.Key.shift,
        keyboard.Key.shift_r: keyboard.Key.shift,
    }

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
        self.focus_manager = WindowFocusManager()
        self.require_game_focus = config.require_game_focus
        self.auto_stop_on_unfocus = config.auto_stop_on_unfocus

        if self.auto_stop_on_unfocus:
            self.focus_manager.register_focus_callback(self._on_focus_change)
            self.focus_manager.start_monitoring()

        # Pre-compute hotkeys
        self.hotkeys = {
            action: self._parse_hotkey(hotkey_str)
            for action, hotkey_str in config.hotkeys.items()
        }

        if DEBUG:
            for action, combo in self.hotkeys.items():
                print(f"[DEBUG] Parsed {action}: {combo}")

    def _parse_hotkey(self, hotkey_str: str) -> frozenset:
        """Parse hotkey string into key set"""
        parts = [p.strip().lower() for p in hotkey_str.split("+")]
        keys = {
            self.KEY_MAP.get(part, keyboard.KeyCode.from_char(part)) for part in parts
        }
        return frozenset(keys)

    def _normalize_key(self, key):
        """Normalize key variants (left/right modifiers, case)"""
        # Check modifier normalization
        if normalized := self.MODIFIER_NORMALIZE.get(key):
            return normalized

        # Handle VK codes
        if hasattr(key, "vk") and key.vk:
            if 65 <= key.vk <= 90:  # A-Z
                return keyboard.KeyCode.from_char(chr(key.vk + 32))
            if 48 <= key.vk <= 57:  # 0-9
                return keyboard.KeyCode.from_char(chr(key.vk))

        # Handle character keys
        if hasattr(key, "char") and key.char:
            return keyboard.KeyCode.from_char(key.char.lower())

        return key

    def _on_focus_change(self, is_focused: bool):
        """Handle focus change - stop tools on unfocus"""
        if is_focused:
            if DEBUG:
                print("[DEBUG] GTA regained focus - restarting listener...")

            with self._lock:
                self.current_keys.clear()
                self.triggered.clear()

            THREAD_POOL.submit(self._restart_listener)
            return

        # Stop active tools on unfocus
        active_tools = [
            (self.autoclicker, "Auto Clicker"),
            (self.snack_spammer, "Snack Spammer"),
            (self.anti_afk, "Anti-AFK"),
        ]

        stopped = [
            name for tool, name in active_tools if tool.active and not tool.stop()
        ]

        if stopped:
            with self._lock:
                self.current_keys.clear()
                self.triggered.clear()

            tools_str = ", ".join(stopped)
            console.print(
                f"[yellow]⏸[/yellow] Alt+Tab detected - Stopped: {tools_str}",
                style="yellow",
            )
            self.manager.show_notification(
                "AUTO-STOPPED", f"Tools paused: {tools_str}", "#f59e0b"
            )

            if DEBUG:
                print(f"[DEBUG] Focus lost - Stopped: {tools_str}")

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
                    on_press=self.on_press, on_release=self.on_release, suppress=False
                )
                self._listener.start()

                if DEBUG:
                    print("[DEBUG] ✓ Listener restarted")

            # Force refresh focus state after restart
            time.sleep(0.1)
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
                    print(
                        f"[DEBUG]   GTA focused: {self.focus_manager.is_gta_focused()}"
                    )

                # Skip if focus required but not focused
                if self.require_game_focus and not self.focus_manager.is_gta_focused():
                    if DEBUG:
                        print("[DEBUG]   GTA not focused - ignoring")
                    return

                # Check hotkey matches - PRIORITIZE LONGEST COMBINATIONS
                current_frozen = frozenset(self.current_keys)
                
                # Find all matching hotkeys and select the longest one
                matches = [
                    (action, combo) 
                    for action, combo in self.hotkeys.items()
                    if action not in self.triggered and combo.issubset(current_frozen)
                ]
                
                if matches:
                    # Sort by combination length (descending) and take the first
                    action, combo = max(matches, key=lambda x: len(x[1]))
                    self.triggered.add(action)

                    if DEBUG:
                        print(f"[DEBUG] ✓✓✓ HOTKEY MATCHED: {action}")

                    THREAD_POOL.submit(self._handle_action, action)

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
                    action
                    for action in self.triggered
                    if normalized in self.hotkeys[action]
                    or not self.hotkeys[action].issubset(current_frozen)
                ]

                for action in to_clear:
                    self.triggered.discard(action)

                if DEBUG and to_clear:
                    print(f"[DEBUG]   Cleared combos: {to_clear}")

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Key release error: {e}")

    def _handle_action(self, action: str):
        """Route action to appropriate handler"""
        handlers = {
            "toggle_overlay": self._toggle_overlay,
            "toggle_nosave": lambda: self.firewall_manager.toggle_rule(
                self.manager, self.sound_manager
            ),
            "debug_toggle": self._toggle_debug,
            "autoclicker": lambda: self._toggle_tool(
                self.autoclicker, "AUTO CLICKER ⚡"
            ),
            "snack_spammer": lambda: self._toggle_tool(
                self.snack_spammer, "SNACK SPAMMER 🍔", " (Hold TAB)"
            ),
            "anti_afk": lambda: self._toggle_tool(
                self.anti_afk, "ANTI-AFK 🎮", " (S+A ↔ S+D)"
            ),
            "kill_gta": lambda: ProcessManager.kill_process(
                GameDetector().get_gta_process().name(), self.manager
            ),
            "job_warp": self.exploit_manager.job_warp,
            "casino_fingerprint": self.solver_manager.casino_fingerprint,
            "casino_keypad": self.solver_manager.casino_keypad,
            "cayo_fingerprint": self.solver_manager.cayo_fingerprint,
            "cayo_voltage": self.solver_manager.cayo_voltage,
        }

        if handler := handlers.get(action):
            try:
                handler()
            except Exception as e:
                if DEBUG:
                    print(f"[DEBUG] Action handler error: {e}")

    def _toggle_overlay(self):
        """Toggle overlay mode"""
        self.manager.toggle_mode()
        self.sound_manager.play_toggle()

        if self.manager.show_full:
            console.print(
                "◉ Switched to [bold cyan]FULL[/bold cyan] overlay mode", style="blue"
            )
            self.manager.show_notification(
                "OVERLAY MODE", "Full display enabled", "#3b82f6"
            )
        else:
            console.print(
                "◉ Switched to [bold cyan]MINI[/bold cyan] overlay mode", style="blue"
            )
            self.manager.show_notification(
                "OVERLAY MODE", "Compact indicator active", "#3b82f6"
            )
        console.print()

    def _toggle_debug(self):
        """Toggle debug mode"""
        global DEBUG
        DEBUG = not DEBUG
        status = "ENABLED" if DEBUG else "DISABLED"
        console.print(f"🐛 DEBUG MODE [bold]{status}[/bold]", style="yellow")
        self.manager.show_notification("DEBUG MODE 🐛", status, "#f59e0b")
        console.print()

    def _toggle_tool(self, tool, name: str, extra: str = ""):
        """Toggle tool on/off"""
        tool.toggle()
        if tool.active:
            console.print(f"[bold green]✓ {name} ENABLED{extra}[/bold green]")
            self.manager.show_notification(name, f"ENABLED{extra}", "#82D668")
        else:
            console.print(f"[bold red]✗ {name} DISABLED[/bold red]")
            self.manager.show_notification(name, "DISABLED", "#FF3B5C")
        console.print()

    def start_listening(self):
        """Start keyboard listener"""
        if DEBUG:
            print("[DEBUG] Starting initial keyboard listener...")

        try:
            with self._listener_lock:
                self._listener = keyboard.Listener(
                    on_press=self.on_press, on_release=self.on_release, suppress=False
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


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def cleanup(autoclicker, snack_spammer, anti_afk, firewall_manager):
    """Cleanup resources on exit"""
    for tool in (autoclicker, snack_spammer, anti_afk):
        if tool.active:
            tool.stop()

    if firewall_manager.cleanup():
        console.print("\n✓ Cleanup: Firewall rule removed", style="green")


def disable_console_quickedit():
    """Disable Windows console QuickEdit mode to prevent input freeze"""
    if sys.platform != "win32":
        return

    try:
        kernel32 = ctypes.windll.kernel32
        h_console = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE

        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(h_console, ctypes.byref(mode))

        # Disable interactive modes
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


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    """Main application entry point"""
    global DEBUG

    # Set global exception handler
    sys.excepthook = global_exception_handler

    if "--debug" in sys.argv:
        DEBUG = True
        console.print("[bold yellow]🐛 DEBUG MODE ENABLED[/bold yellow]")
        console.print()

    # ⭐ UPDATED: Pass BASE_DIR parameter
    ProcessManager.run_as_admin(BASE_DIR)
    ctypes.windll.user32.SetProcessDPIAware()
    disable_console_quickedit()

    # Load configuration
    config = AppConfig.load(CONFIG_PATH)

    # ⭐ UPDATED: Initialize managers with new signatures
    sound_manager = SoundManager(ASSETS_DIR)
    firewall_manager = FirewallManager(
        config.rule_name, config.remote_ip, config.test_port
    )
    overlay_manager = OverlayManager()

    # Initialize tools
    autoclicker = AutoClicker(sound_manager)
    snack_spammer = SnackSpammer(sound_manager)
    anti_afk = AntiAFK(sound_manager)

    # Initialize feature managers
    solver_manager = SolverManager(overlay_manager)
    exploit_manager = ExploitManager(overlay_manager)

    # ⭐ UPDATED: Display UI with new method signatures
    UIManager.print_header(APP_TITLE, VERSION)

    # Check for updates
    console.print("[dim]⏳ Checking for updates...[/dim]", end="")
    update_checker = UpdateChecker(VERSION)
    if update_checker.check_for_updates():
        console.print(" [yellow]✓[/yellow]")
        update_checker.print_update_notification()
    else:
        console.print(" [green]✓[/green] [dim](up to date)[/dim]")
    console.print()

    UIManager.print_hotkeys(config.hotkeys)

    initial_status = "ON" if firewall_manager.rule_exists() else "OFF"
    UIManager.print_status(config.hotkeys["debug_toggle"])

    overlay_manager.update_status(initial_status)

    # Setup hotkey handler
    hotkey_handler = HotkeyHandler(
        config,
        overlay_manager,
        sound_manager,
        firewall_manager,
        autoclicker,
        snack_spammer,
        anti_afk,
        solver_manager,
        exploit_manager,
    )

    # Register cleanup
    atexit.register(cleanup, autoclicker, snack_spammer, anti_afk, firewall_manager)

    # Start listener thread
    threading.Thread(
        target=hotkey_handler.start_listening, daemon=True, name="hotkey_listener"
    ).start()

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