import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import winsound
from dataclasses import dataclass
from threading import Thread
from typing import Optional

from pynput import keyboard
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from assets.ui import OverlayManager
from tools.autoclicker import AutoClicker, SnackSpammer, PYDIRECTINPUT_AVAILABLE


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
RULE_NAME = "gtanosavemode_rule"
REMOTE_IP = "192.81.241.171"
TEST_PORT = 80
VERSION = "v2.4"
APP_TITLE = "VKit - Toolbox"
GTA_PROCESS_NAME = "GTA5_Enhanced.exe"

# Debug mode toggle
DEBUG = False


@dataclass
class HotkeyConfig:
    """Configuration for hotkey bindings"""
    TOGGLE_OVERLAY = keyboard.Key.f8
    ENABLE_NOSAVE = keyboard.Key.f9
    DISABLE_NOSAVE = keyboard.Key.f12
    
    # Character keys (VK codes)
    AUTOCLICKER = (75, 'k')
    SNACK_SPAMMER = (67, 'c')
    JOB_WARP = (74, 'j')
    DEBUG_TOGGLE = (68, 'd')
    KILL_GTA = (221, ']')
    
    # Solver keys
    CASINO_FINGERPRINT = keyboard.Key.f5
    CASINO_KEYPAD = keyboard.Key.f6
    CAYO_FINGERPRINT = keyboard.Key.f5  # with CTRL
    CAYO_VOLTAGE = keyboard.Key.f6      # with CTRL


class SoundManager:
    """Manages sound effects for the application"""
    
    SOUND_FILES = {
        'on': 'on.wav',
        'off': 'off.wav',
        'toggle': 'toggle.wav'
    }
    
    def __init__(self) -> None:
        base_dir = os.path.dirname(__file__)
        self.sounds_dir = os.path.join(base_dir, "assets", "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)
        
        # Load sound paths and check existence
        self.sounds = {}
        for key, filename in self.SOUND_FILES.items():
            path = os.path.join(self.sounds_dir, filename)
            self.sounds[key] = {
                'path': path,
                'exists': os.path.exists(path)
            }
            
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
    
    def __init__(self, rule_name: str, remote_ip: str, test_port: int):
        self.rule_name = rule_name
        self.remote_ip = remote_ip
        self.test_port = test_port
    
    def rule_exists(self) -> bool:
        """Check if firewall rule exists"""
        cmd = f'netsh advfirewall firewall show rule name="{self.rule_name}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return "No rules match the specified criteria" not in result.stdout
    
    def test_ip_blocked(self, timeout: float = 2) -> bool:
        """Test if IP is blocked by attempting connection"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.remote_ip, self.test_port))
            sock.close()
            return result != 0
        except Exception:
            return True
    
    def add_rule(self, manager: OverlayManager, sound_manager: SoundManager) -> None:
        """Add firewall blocking rule"""
        cmd = (
            f'netsh advfirewall firewall add rule name="{self.rule_name}" '
            f'dir=out action=block remoteip="{self.remote_ip}"'
        )
        subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        
        time.sleep(0.5)
        if self.rule_exists():
            console.print("✓ NO SAVING MODE [bold red]ENABLED[/bold red]", style="green")
            manager.update_status("ON")
            manager.show_notification("✓ NO SAVING MODE ENABLED", "#ef4444")
            sound_manager.play_on()
            
            if self.test_ip_blocked():
                console.print(
                    f"✓ Connection to [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                    f"is [bold red]BLOCKED[/bold red]",
                    style="green",
                )
        else:
            console.print("✗ Failed to add firewall rule", style="red")
        console.print()
    
    def delete_rule(self, manager: OverlayManager, sound_manager: SoundManager) -> None:
        """Remove firewall blocking rule"""
        cmd = f'netsh advfirewall firewall delete rule name="{self.rule_name}"'
        subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        
        time.sleep(0.5)
        if not self.rule_exists():
            console.print("✓ NO SAVING MODE [bold green]DISABLED[/bold green]", style="green")
            manager.update_status("OFF")
            manager.show_notification("✓ NO SAVING MODE DISABLED", "#85BB65")
            sound_manager.play_off()
            
            if not self.test_ip_blocked():
                console.print(
                    f"✓ Connection to [cyan]{self.remote_ip}:{self.test_port}[/cyan] "
                    f"is [bold green]ACCESSIBLE[/bold green]",
                    style="green",
                )
        else:
            console.print("✗ Failed to delete firewall rule", style="red")
        console.print()
    
    def cleanup(self) -> bool:
        """Cleanup firewall rule on exit"""
        if self.rule_exists():
            cmd = f'netsh advfirewall firewall delete rule name="{self.rule_name}"'
            subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
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
        """Restart script with admin privileges"""
        if ProcessManager.is_admin():
            return
        
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1,
        )
        sys.exit()
    
    @staticmethod
    def kill_process(process_name: str, manager: OverlayManager) -> None:
        """Kill a process by name"""
        try:
            result = subprocess.run(
                f'taskkill /F /IM {process_name}',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            
            if result.returncode == 0:
                console.print(f"✓ {process_name} process [bold red]KILLED[/bold red]", style="green")
                manager.show_notification(f"✓ {process_name} Terminated", "#ef4444")
            else:
                console.print(f"✗ {process_name} process not found or already closed", style="yellow")
                manager.show_notification(f"⚠ {process_name} Not Running", "#f59e0b")
        except Exception as e:
            console.print(f"✗ Failed to kill {process_name}: {e}", style="red")
            manager.show_notification(f"✗ Failed to Kill {process_name}", "#ef4444")
        console.print()


class SolverManager:
    """Manages heist solver operations"""
    
    def __init__(self, manager: OverlayManager):
        self.manager = manager
    
    def _run_solver(self, label: str, color: str, func) -> None:
        """Generic solver runner"""
        if not SOLVERS_AVAILABLE:
            console.print("[red]✗[/red] Hack modules not available", style="red")
            return
        
        console.print(f"[cyan]➤[/cyan] Running {label}...", style="cyan")
        self.manager.show_notification(label, color)
        bbox = self.manager.get_window_bbox()
        
        if bbox:
            Thread(target=func, args=(bbox,), daemon=True).start()
    
    def casino_fingerprint(self) -> None:
        self._run_solver("🎰 Casino Fingerprint Solver", "#a855f7", casinofingerprint.main)
    
    def casino_keypad(self) -> None:
        self._run_solver("🎰 Casino Keypad Solver", "#a855f7", casinokeypad.main)
    
    def cayo_fingerprint(self) -> None:
        self._run_solver("🏝️ Cayo Fingerprint Solver", "#a855f7", cayofingerprint.main)
    
    def cayo_voltage(self) -> None:
        self._run_solver("🏝️ Cayo Voltage Solver", "#a855f7", cayovoltage.main)


class ExploitManager:
    """Manages exploit operations"""
    
    def __init__(self, manager: OverlayManager):
        self.manager = manager
    
    def job_warp(self) -> None:
        """Execute job warp exploit"""
        if not JOBWARP_AVAILABLE:
            console.print("[red]✗[/red] Job warp module not available", style="red")
            return
        
        bbox = self.manager.get_window_bbox()
        if not bbox:
            console.print("[red]✗[/red] GTA V window not found", style="red")
            self.manager.show_notification("✗ GTA V Not Found", "#ef4444")
            return
        
        console.print("[cyan]➤[/cyan] Triggering Job Warp exploit...", style="cyan")
        Thread(target=jobwarp.main, args=(bbox, self.manager), daemon=True).start()


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
        
        console.print(
            Panel(
                Align.center(title),
                box=box.DOUBLE,
                border_style="bright_cyan",
                padding=(0, 2),
            )
        )
        console.print()
    
    @staticmethod
    def print_overlay_info() -> None:
        """Print overlay features information"""
        overlay_text = Text()
        overlay_text.append("🔲 FULL MODE\n", style="bold green")
        overlay_text.append("🔴 MINI MODE\n", style="bold red")
        overlay_text.append("   Compact glowing orb indicator\n", style="white")
        overlay_text.append("   • Green (disabled) / Red (enabled)\n\n", style="dim")
        overlay_text.append("Behavior:\n", style="bold yellow")
        overlay_text.append("• Only visible when GTA V is focused\n", style="dim")
        overlay_text.append("• Auto-hide on Alt+Tab\n", style="dim")
        
        console.print(
            Panel(
                overlay_text,
                title="✨ [bold]Overlay Features[/bold]",
                box=box.ROUNDED,
                border_style="green",
                width=70,
                padding=(1, 2),
            )
        )
        console.print()
    
    @staticmethod
    def print_hotkeys() -> None:
        """Print hotkeys table"""
        hotkeys_table = Table(
            title="🎮  [bold]Hotkeys[/bold]",
            box=box.ROUNDED,
            border_style="magenta",
            show_header=True,
            header_style="bold magenta",
            width=70,
        )
        hotkeys_table.add_column("Shortcut", style="bold magenta", width=22)
        hotkeys_table.add_column("Action", style="white", width=41)
        
        # Core hotkeys
        hotkeys_table.add_row("CTRL + ALT + F8", "Toggle overlay mode (Full ↔ Mini)")
        hotkeys_table.add_row("CTRL + ALT + F9", "Enable NOSAVE (Block IP)")
        hotkeys_table.add_row("CTRL + ALT + F12", "Disable NOSAVE (Unblock IP)")
        hotkeys_table.add_row("CTRL + ALT + D", "🐛 Toggle Debug Mode")
        hotkeys_table.add_row("", "")
        
        # Tool hotkeys
        hotkeys_table.add_row("CTRL + ALT + K", "⚡ Toggle Fast Autoclicker (50 CPS)")
        hotkeys_table.add_row("CTRL + ALT + C", "🍔 Toggle Snack Spammer (Hold TAB)")
        hotkeys_table.add_row("CTRL + ALT + ]", "💀 Kill GTA5 Process (Instant)")
        
        # Optional features
        if JOBWARP_AVAILABLE:
            hotkeys_table.add_row("", "")
            hotkeys_table.add_row("CTRL + ALT + J", "🚀 Job Warp Exploit (Toggle)")
        
        if SOLVERS_AVAILABLE:
            hotkeys_table.add_row("", "")
            hotkeys_table.add_row("F5", "Casino Fingerprint Solver")
            hotkeys_table.add_row("F6", "Casino Keypad Solver")
            hotkeys_table.add_row("CTRL + F5", "Cayo Perico Fingerprint Solver")
            hotkeys_table.add_row("CTRL + F6", "Cayo Perico Voltage Solver")
        
        console.print(hotkeys_table)
        console.print()
    
    @staticmethod
    def print_status(initial_status: str, sound_manager: SoundManager) -> None:
        """Print current status table"""
        status_table = Table(
            title="📊  [bold]Current Status[/bold]",
            box=box.ROUNDED,
            border_style="yellow",
            show_header=False,
            width=70,
        )
        status_table.add_column("Item", style="bold white", width=18)
        status_table.add_column("Status", style="white", width=45)
        
        # Firewall status
        if initial_status == "ON":
            status_table.add_row(
                "Firewall Rule",
                f"[green]✓[/green] [bold red]ACTIVE[/bold red] (Blocking {REMOTE_IP})",
            )
        else:
            status_table.add_row(
                "Firewall Rule",
                "[dim]○[/dim] [bold green]INACTIVE[/bold green] (Traffic allowed)",
            )
        
        # Overlay mode
        status_table.add_row(
            "Overlay Mode",
            "[bold]🔲 FULL[/bold] [dim](Press CTRL+ALT+F8 to toggle)[/dim]",
        )
        
        # Autoclicker status
        clicker_mode = "DirectInput" if PYDIRECTINPUT_AVAILABLE else "Standard"
        status_table.add_row(
            "Autoclicker",
            f"[dim]○[/dim] [bold red]DISABLED[/bold red] [dim](CTRL+ALT+K - {clicker_mode})[/dim]",
        )
        
        # Sound status
        sounds_loaded = sound_manager.get_loaded_count()
        if sounds_loaded == 3:
            sound_status = "[green]✓[/green] All sounds loaded"
        elif sounds_loaded > 0:
            sound_status = f"[yellow]⚠[/yellow] {sounds_loaded}/3 sounds loaded"
        else:
            sound_status = "[dim]○[/dim] No sounds loaded"
        status_table.add_row("Sound Effects", sound_status)
        
        # Solver status
        hack_status = (
            "[green]✓[/green] Heist solvers loaded"
            if SOLVERS_AVAILABLE
            else "[yellow]⚠[/yellow] Heist solvers not available"
        )
        status_table.add_row("Heist Solvers", hack_status)
        
        # Job warp status
        if JOBWARP_AVAILABLE:
            status_table.add_row(
                "Job Warp",
                "[green]✓[/green] Available [dim](CTRL+ALT+J)[/dim]",
            )
        
        console.print(status_table)
        console.print()
        
        # Optional warnings
        if not PYDIRECTINPUT_AVAILABLE:
            console.print(
                Panel(
                    "[yellow]⚠[/yellow] For better autoclicker in fullscreen games, install:\n"
                    "[bold cyan]pip install pydirectinput[/bold cyan]",
                    box=box.ROUNDED,
                    border_style="yellow",
                    width=70,
                )
            )
            console.print()
        
        # Running status
        console.print(
            Panel(
                "[bold green]●[/bold green] Script is running... "
                "Press [bold red]CTRL+C[/bold red] to exit\n"
                "[dim]Press CTRL+ALT+D to toggle debug mode[/dim]",
                box=box.HEAVY,
                border_style="bright_green",
                width=70,
                padding=(0, 2),
            )
        )
        console.print()


class HotkeyHandler:
    """Handles all hotkey detection and routing"""
    
    def __init__(
        self,
        manager: OverlayManager,
        sound_manager: SoundManager,
        firewall_manager: FirewallManager,
        autoclicker: AutoClicker,
        snack_spammer: SnackSpammer,
        solver_manager: SolverManager,
        exploit_manager: ExploitManager,
    ):
        self.manager = manager
        self.sound_manager = sound_manager
        self.firewall_manager = firewall_manager
        self.autoclicker = autoclicker
        self.snack_spammer = snack_spammer
        self.solver_manager = solver_manager
        self.exploit_manager = exploit_manager
        self.current_keys: set[object] = set()
        self.config = HotkeyConfig()
    
    def _has_ctrl(self) -> bool:
        return any(key in self.current_keys for key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
    
    def _has_alt(self) -> bool:
        return any(key in self.current_keys for key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr))
    
    def _toggle_overlay_mode(self) -> None:
        self.manager.toggle_mode()
        self.sound_manager.play_toggle()
        
        if self.manager.show_full:
            console.print("◉ Switched to [bold cyan]FULL[/bold cyan] overlay mode", style="blue")
            self.manager.show_notification("◉ Switched to FULL overlay", "#3b82f6")
        else:
            console.print("◉ Switched to [bold cyan]MINI[/bold cyan] overlay mode (glowing indicator)", style="blue")
            self.manager.show_notification("◉ Switched to MINI overlay", "#3b82f6")
        console.print()
    
    def _toggle_debug(self) -> None:
        global DEBUG
        DEBUG = not DEBUG
        status = "ENABLED" if DEBUG else "DISABLED"
        console.print(f"🐛 DEBUG MODE [bold]{status}[/bold]", style="yellow")
        self.manager.show_notification(f"🐛 Debug Mode {status}", "#f59e0b")
        console.print()
    
    def _handle_character_key(self, vk_code: Optional[int], char: Optional[str]) -> None:
        """Handle character key presses with CTRL+ALT"""
        if char:
            char = char.lower()
        
        # Autoclicker toggle
        if vk_code == self.config.AUTOCLICKER[0] or char == self.config.AUTOCLICKER[1]:
            console.print("[bold green]✓ CTRL+ALT+K DETECTED - TOGGLING AUTOCLICKER[/bold green]")
            self.autoclicker.toggle()
            if self.autoclicker.active:
                self.manager.show_notification("⚡ Autoclicker ENABLED (50 CPS)", "#10b981")
            else:
                self.manager.show_notification("⚡ Autoclicker DISABLED", "#ef4444")
        
        # Snack spammer toggle
        elif vk_code == self.config.SNACK_SPAMMER[0] or char == self.config.SNACK_SPAMMER[1]:
            console.print("[bold green]✓ CTRL+ALT+C DETECTED - TOGGLING SNACK SPAMMER[/bold green]")
            self.snack_spammer.toggle()
            if self.snack_spammer.active:
                self.manager.show_notification("🍔 Snack Spammer ON (Hold TAB)", "#10b981")
            else:
                self.manager.show_notification("🍔 Snack Spammer OFF", "#ef4444")
        
        # Job warp exploit
        elif vk_code == self.config.JOB_WARP[0] or char == self.config.JOB_WARP[1]:
            self.exploit_manager.job_warp()
        
        # Debug toggle
        elif vk_code == self.config.DEBUG_TOGGLE[0] or char == self.config.DEBUG_TOGGLE[1]:
            self._toggle_debug()
        
        # Kill GTA5
        elif vk_code == self.config.KILL_GTA[0] or char == self.config.KILL_GTA[1]:
            console.print("[bold red]✓ CTRL+ALT+] DETECTED - KILLING GTA5[/bold red]")
            ProcessManager.kill_process(GTA_PROCESS_NAME, self.manager)
    
    def on_press(self, key) -> None:
        """Handle key press events"""
        if DEBUG:
            try:
                print(f"[DEBUG] Pressed: {key} (char: {key.char})")
            except AttributeError:
                print(f"[DEBUG] Pressed: {key}")
        
        self.current_keys.add(key)
        
        ctrl = self._has_ctrl()
        alt = self._has_alt()
        
        # CTRL + ALT combinations
        if ctrl and alt:
            if key == self.config.TOGGLE_OVERLAY:
                self._toggle_overlay_mode()
            elif key == self.config.ENABLE_NOSAVE:
                self.firewall_manager.add_rule(self.manager, self.sound_manager)
            elif key == self.config.DISABLE_NOSAVE:
                self.firewall_manager.delete_rule(self.manager, self.sound_manager)
            else:
                # Handle character keys
                vk_code = getattr(key, 'vk', None)
                char = getattr(key, 'char', None)
                self._handle_character_key(vk_code, char)
        
        # CTRL only (Cayo solvers)
        elif ctrl and not alt:
            if key == self.config.CAYO_FINGERPRINT:
                self.solver_manager.cayo_fingerprint()
            elif key == self.config.CAYO_VOLTAGE:
                self.solver_manager.cayo_voltage()
        
        # No modifiers (Casino solvers)
        elif not ctrl and not alt:
            if key == self.config.CASINO_FINGERPRINT:
                self.solver_manager.casino_fingerprint()
            elif key == self.config.CASINO_KEYPAD:
                self.solver_manager.casino_keypad()
    
    def on_release(self, key) -> None:
        """Handle key release events"""
        try:
            self.current_keys.discard(key)
        except Exception:
            pass
    
    def start_listening(self) -> None:
        """Start the keyboard listener"""
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
            suppress=False,
        ) as listener:
            listener.join()


def cleanup(
    autoclicker: AutoClicker,
    snack_spammer: SnackSpammer,
    firewall_manager: FirewallManager
) -> None:
    """Cleanup all resources before exit"""
    if autoclicker.active:
        autoclicker.stop()
    
    if snack_spammer.active:
        snack_spammer.stop()
    
    if firewall_manager.cleanup():
        console.print("\n✓ Cleanup: Firewall rule removed", style="green")


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
    
    # Initialize managers
    sound_manager = SoundManager()
    firewall_manager = FirewallManager(RULE_NAME, REMOTE_IP, TEST_PORT)
    overlay_manager = OverlayManager()
    
    # Initialize tools
    autoclicker = AutoClicker(sound_manager)
    snack_spammer = SnackSpammer(sound_manager)
    
    # Initialize feature managers
    solver_manager = SolverManager(overlay_manager)
    exploit_manager = ExploitManager(overlay_manager)
    
    # Display UI
    UIManager.print_header()
    UIManager.print_overlay_info()
    UIManager.print_hotkeys()
    
    initial_status = "ON" if firewall_manager.rule_exists() else "OFF"
    UIManager.print_status(initial_status, sound_manager)
    
    overlay_manager.update_status(initial_status)
    
    # Setup hotkey handler
    hotkey_handler = HotkeyHandler(
        overlay_manager,
        sound_manager,
        firewall_manager,
        autoclicker,
        snack_spammer,
        solver_manager,
        exploit_manager,
    )
    
    # Start listener thread
    listener_thread = threading.Thread(
        target=hotkey_handler.start_listening,
        daemon=True,
    )
    listener_thread.start()
    
    # Run overlay manager (blocks until exit)
    try:
        overlay_manager.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow] Shutting down...", style="bold")
    finally:
        cleanup(autoclicker, snack_spammer, firewall_manager)
        console.print("✓ Script terminated successfully\n", style="green bold")


if __name__ == "__main__":
    main()