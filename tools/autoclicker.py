import threading
import time
from rich.console import Console

try:
    import pydirectinput
    pydirectinput.PAUSE = 0.001
    PYDIRECTINPUT_AVAILABLE = True
except ImportError:
    PYDIRECTINPUT_AVAILABLE = False
    from pynput import mouse

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class AutoClicker:
    def __init__(self, sound_manager) -> None:
        self.active = False
        self.thread: threading.Thread | None = None
        self.sound_manager = sound_manager
        self.clicks_per_second = 50
        self.use_directinput = PYDIRECTINPUT_AVAILABLE

        if not self.use_directinput:
            self.mouse_controller = mouse.Controller()

    def _directinput_click(self) -> None:
        """DirectInput click without moving mouse"""
        pydirectinput.mouseDown(button="left")
        time.sleep(0.02)
        pydirectinput.mouseUp(button="left")

    def _pynput_click(self) -> None:
        """Pynput click without moving mouse"""
        self.mouse_controller.press(mouse.Button.left)
        time.sleep(0.02)
        self.mouse_controller.release(mouse.Button.left)

    def click_loop(self) -> None:
        console = Console()
        
        mode = "DirectInput" if self.use_directinput else "Standard"
        console.print(f"⚡ Autoclicker [bold green]STARTED[/bold green] ({self.clicks_per_second} CPS - {mode})", style="green")
        
        click_count = 0
        delay = 1.0 / self.clicks_per_second

        while self.active:
            try:
                if self.use_directinput:
                    self._directinput_click()
                else:
                    self._pynput_click()

                click_count += 1
                time.sleep(delay)
            except Exception as exc:
                console.print(f"✗ Autoclicker error: {exc}", style="red")
                break

        console.print(f"⚡ Autoclicker [bold red]STOPPED[/bold red] ([cyan]{click_count}[/cyan] clicks)", style="green")
        console.print()

    def start(self) -> None:
        if self.active:
            return

        self.active = True
        self.thread = threading.Thread(target=self.click_loop, daemon=True)
        self.thread.start()
        self.sound_manager.play_on()

    def stop(self) -> None:
        if not self.active:
            return

        self.active = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.sound_manager.play_off()

    def toggle(self) -> None:
        if self.active:
            self.stop()
        else:
            self.start()


class SnackSpammer:
    def __init__(self, sound_manager) -> None:
        self.active = False
        self.thread: threading.Thread | None = None
        self.sound_manager = sound_manager
        self.spam_delay = 0.05  # 50ms between presses
        
        if not KEYBOARD_AVAILABLE:
            console = Console()
            console.print("[yellow]⚠[/yellow] keyboard module not available for SnackSpammer", style="dim")
    
    def spam_loop(self) -> None:
        console = Console()
        console.print("🍔 Snack Spammer [bold green]STARTED[/bold green] (Hold TAB to spam 'C')", style="green")
        
        press_count = 0
        
        while self.active:
            try:
                # Only spam if TAB is held down
                if keyboard.is_pressed('tab'):
                    keyboard.press('c')
                    time.sleep(self.spam_delay)
                    keyboard.release('c')
                    time.sleep(self.spam_delay)
                    press_count += 1
                else:
                    # Small delay when TAB is not pressed to avoid high CPU usage
                    time.sleep(0.1)
                    
            except Exception as exc:
                console.print(f"✗ SnackSpammer error: {exc}", style="red")
                break
        
        console.print(f"🍔 Snack Spammer [bold red]STOPPED[/bold red] ([cyan]{press_count}[/cyan] presses)", style="green")
        console.print()
    
    def start(self) -> None:
        if not KEYBOARD_AVAILABLE:
            console = Console()
            console.print("[red]✗[/red] keyboard module required for SnackSpammer", style="red")
            return
            
        if self.active:
            return

        self.active = True
        self.thread = threading.Thread(target=self.spam_loop, daemon=True)
        self.thread.start()
        self.sound_manager.play_on()

    def stop(self) -> None:
        if not self.active:
            return

        self.active = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.sound_manager.play_off()
    
    def toggle(self) -> None:
        if self.active:
            self.stop()
        else:
            self.start()