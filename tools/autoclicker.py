import threading
import time
from rich.console import Console
import random


console = Console()
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
        self.clicks_per_second = 70
        self.use_directinput = PYDIRECTINPUT_AVAILABLE
        self.stop_event = threading.Event()  # 🔥 NEW


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


        while self.active and not self.stop_event.is_set():  # 🔥 CHANGED
            try:
                if self.use_directinput:
                    self._directinput_click()
                else:
                    self._pynput_click()


                click_count += 1
                
                # 🔥 CHANGED - Interruptible sleep
                if self.stop_event.wait(timeout=delay):
                    break
                    
            except Exception as exc:
                console.print(f"✗ Autoclicker error: {exc}", style="red")
                break


        console.print(f"⚡ Autoclicker [bold red]STOPPED[/bold red] ([cyan]{click_count}[/cyan] clicks)", style="green")
        console.print()


    def start(self) -> None:
        if self.active:
            return


        self.active = True
        self.stop_event.clear()  # 🔥 NEW
        self.thread = threading.Thread(target=self.click_loop, daemon=True)
        self.thread.start()
        self.sound_manager.play_on()


    def stop(self) -> None:
        if not self.active:
            return


        self.active = False
        self.stop_event.set()  # 🔥 NEW - Instant wake-up!
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)  # 🔥 CHANGED from 2s to 1s
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
        self.stop_event = threading.Event()  # 🔥 NEW
        
        if not KEYBOARD_AVAILABLE:
            console = Console()
            console.print("[yellow]⚠[/yellow] keyboard module not available for SnackSpammer", style="dim")
    
    def spam_loop(self) -> None:
        console = Console()
        console.print("🍔 Snack Spammer [bold green]STARTED[/bold green] (Hold TAB to spam 'C')", style="green")
        
        press_count = 0
        
        while self.active and not self.stop_event.is_set():  # 🔥 CHANGED
            try:
                # Only spam if TAB is held down
                if keyboard.is_pressed('tab'):
                    keyboard.press('c')
                    
                    # 🔥 CHANGED - Interruptible sleep
                    if self.stop_event.wait(timeout=self.spam_delay):
                        keyboard.release('c')
                        break
                        
                    keyboard.release('c')
                    
                    # 🔥 CHANGED - Interruptible sleep
                    if self.stop_event.wait(timeout=self.spam_delay):
                        break
                        
                    press_count += 1
                else:
                    # 🔥 CHANGED - Interruptible sleep when TAB not pressed
                    if self.stop_event.wait(timeout=0.1):
                        break
                    
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
        self.stop_event.clear()  # 🔥 NEW
        self.thread = threading.Thread(target=self.spam_loop, daemon=True)
        self.thread.start()
        self.sound_manager.play_on()


    def stop(self) -> None:
        if not self.active:
            return


        self.active = False
        self.stop_event.set()  # 🔥 NEW - Instant wake-up!
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)  # 🔥 CHANGED from 2s to 1s
        self.sound_manager.play_off()
    
    def toggle(self) -> None:
        if self.active:
            self.stop()
        else:
            self.start()
            
class AntiAFK:
    """Anti-AFK system - alternates S+A and S+D every 20-30 seconds"""
    
    def __init__(self, sound_manager):
        self.sound_manager = sound_manager
        self.active = False
        self.thread = None
        self.stop_event = threading.Event()
        self.current_keys = []  # 🔥 NEW - Track pressed keys
    
    def _release_all_keys(self):
        """Force release all keys - cleanup helper"""
        try:
            if PYDIRECTINPUT_AVAILABLE:
                import pydirectinput as pdi
                pdi.keyUp('s')
                pdi.keyUp('d')
                pdi.keyUp('a')
            elif KEYBOARD_AVAILABLE:
                from pynput.keyboard import Controller
                kbd = Controller()
                kbd.release('s')
                kbd.release('d')
                kbd.release('a')
            console.print("✓ Released all Anti-AFK keys", style="dim")
        except Exception as e:
            console.print(f"⚠ Key release error: {e}", style="yellow")
    
    def _hold_keys(self) -> None:
        """Main anti-AFK loop - alternates between S+A and S+D"""
        try:
            if PYDIRECTINPUT_AVAILABLE:
                import pydirectinput as pdi
                
                # Start with S+D
                pdi.keyDown('s')
                pdi.keyDown('d')
                self.current_keys = ['s', 'd']  # 🔥 Track
                console.print("✓ Anti-AFK: Starting with S+D", style="green")
                
                use_sd = True
                
                while not self.stop_event.is_set():
                    # Random wait between 20-30 seconds
                    wait_time = random.uniform(20, 30)
                    console.print(f"⏳ Anti-AFK: Next switch in {wait_time:.1f}s", style="dim")  # 🔥 DEBUG
                    
                    if self.stop_event.wait(wait_time):
                        console.print("🛑 Anti-AFK: Stop signal received", style="yellow")  # 🔥 DEBUG
                        break
                    
                    # Switch combo
                    if use_sd:
                        pdi.keyUp('d')
                        pdi.keyDown('a')
                        self.current_keys = ['s', 'a']  # 🔥 Track
                        console.print("◉ Anti-AFK: Switched to S+A", style="cyan")
                        use_sd = False
                    else:
                        pdi.keyUp('a')
                        pdi.keyDown('d')
                        self.current_keys = ['s', 'd']  # 🔥 Track
                        console.print("◉ Anti-AFK: Switched to S+D", style="cyan")
                        use_sd = True
                
                # 🔥 IMPROVED - Release all keys on stop
                console.print("🔓 Releasing keys...", style="dim")
                self._release_all_keys()
                
            elif KEYBOARD_AVAILABLE:
                from pynput.keyboard import Controller
                kbd = Controller()
                
                # Start with S+D
                kbd.press('s')
                kbd.press('d')
                self.current_keys = ['s', 'd']  # 🔥 Track
                console.print("✓ Anti-AFK: Starting with S+D", style="green")
                
                use_sd = True
                
                while not self.stop_event.is_set():
                    wait_time = random.uniform(20, 30)
                    console.print(f"⏳ Anti-AFK: Next switch in {wait_time:.1f}s", style="dim")  # 🔥 DEBUG
                    
                    if self.stop_event.wait(wait_time):
                        console.print("🛑 Anti-AFK: Stop signal received", style="yellow")  # 🔥 DEBUG
                        break
                    
                    # Switch combo
                    if use_sd:
                        kbd.release('d')
                        kbd.press('a')
                        self.current_keys = ['s', 'a']  # 🔥 Track
                        console.print("◉ Anti-AFK: Switched to S+A", style="cyan")
                        use_sd = False
                    else:
                        kbd.release('a')
                        kbd.press('d')
                        self.current_keys = ['s', 'd']  # 🔥 Track
                        console.print("◉ Anti-AFK: Switched to S+D", style="cyan")
                        use_sd = True
                
                # 🔥 IMPROVED - Release all keys on stop
                console.print("🔓 Releasing keys...", style="dim")
                self._release_all_keys()
            
            else:
                console.print("[red]✗[/red] No keyboard library available", style="red")
                
        except Exception as e:
            console.print(f"[red]✗[/red] Anti-AFK error: {e}", style="red")
            self._release_all_keys()  # 🔥 Cleanup on error too
    
    def toggle(self) -> None:
        """Toggle anti-AFK on/off"""
        if self.active:
            self.stop()
        else:
            self.start()
    
    def start(self) -> None:
        """Start anti-AFK"""
        if self.active:
            return
        
        self.active = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._hold_keys, daemon=True)
        self.thread.start()
        
        console.print("✓ Anti-AFK [bold green]ENABLED[/bold green] (Alternating S+D ↔ S+A)", style="green")
        self.sound_manager.play_on()
        console.print()
    
    def stop(self) -> None:
        """Stop anti-AFK"""
        if not self.active:
            return
        
        console.print("⏹ Stopping Anti-AFK...", style="yellow")  # 🔥 DEBUG
        
        self.active = False
        self.stop_event.set()  # Signal thread to stop
        
        console.print("⏹ Waiting for thread...", style="yellow")  # 🔥 DEBUG
        
        if self.thread:
            self.thread.join(timeout=1.0)
            if self.thread.is_alive():  # 🔥 NEW - Check if thread is stuck
                console.print("⚠ Thread still alive after 1s, forcing cleanup", style="yellow")
                self._release_all_keys()  # Force release keys even if thread stuck
        
        console.print("✓ Anti-AFK [bold red]DISABLED[/bold red]", style="green")
        self.sound_manager.play_off()
        console.print()