"""
GTA V Style Overlay - Refined
Custom colors + perfected mini circle
"""
import ctypes
import math
import time
import tkinter as tk
from typing import Optional
import win32gui

# --- Color Palette (UPDATED) ---
C_PURE_BLACK = "#000000"
C_BG_DARK = "#0a0a0a"
C_BG_MEDIUM = "#0f0f0f"
C_BG_LIGHTER = "#1a1a1a"

C_TEXT_WHITE = "#ffffff"
C_TEXT_GREY = "#aaaaaa"
C_TEXT_DIM = "#666666"

# Custom colors
C_GREEN_BRIGHT = "#85BB65"  # Your green
C_GREEN_MED = "#6a9a50"     # Derived medium
C_GREEN_DARK = "#4f7a3b"    # Derived dark
C_RED_BRIGHT = "#E03232"    # Your red
C_RED_MED = "#c02828"       # Derived medium
C_RED_DARK = "#a01e1e"      # Derived dark

C_BLUE_BRIGHT = "#3b82f6"
C_PURPLE_BRIGHT = "#a855f7"
C_ORANGE_BRIGHT = "#f59e0b"

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_HEADER = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_SMALL = ("Segoe UI", 8)

GTA_WINDOW_TITLES = ["Grand Theft Auto V", "GTA V", "gta5.exe"]


class Animator:
    @staticmethod
    def ease_out_cubic(x: float) -> float:
        return 1 - pow(1 - x, 3)
    
    @staticmethod
    def ease_in_out_cubic(x: float) -> float:
        if x < 0.5:
            return 4 * x * x * x
        return 1 - pow(-2 * x + 2, 3) / 2
    
    @staticmethod
    def ease_out_quint(x: float) -> float:
        return 1 - pow(1 - x, 5)


class ColorUtil:
    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    @staticmethod
    def interpolate(color1: str, color2: str, progress: float) -> str:
        rgb1 = ColorUtil.hex_to_rgb(color1)
        rgb2 = ColorUtil.hex_to_rgb(color2)
        
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * progress)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * progress)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * progress)
        
        return ColorUtil.rgb_to_hex((r, g, b))
    
    @staticmethod
    def with_alpha(color: str, alpha: float) -> str:
        """Simulate alpha by darkening the color"""
        rgb = ColorUtil.hex_to_rgb(color)
        r = int(rgb[0] * alpha)
        g = int(rgb[1] * alpha)
        b = int(rgb[2] * alpha)
        return ColorUtil.rgb_to_hex((r, g, b))


class GTAInteractionMenu(tk.Frame):
    """
    Original simple style - exactly as you had it
    """
    
    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)
        self.width = 360
        self.height = 90
        
        self.canvas = tk.Canvas(
            self, width=self.width, height=self.height,
            bg=C_PURE_BLACK, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Background
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0a0a0a", outline="", width=0)
        self.canvas.create_rectangle(9, 0, self.width, self.height, fill="#0a0a0a", outline="", width=0)
        
        # Left accent bar
        self.accent_bar = self.canvas.create_rectangle(0, 0, 10, self.height, fill=C_GREEN_BRIGHT, outline="", width=0)
        
        # Small title
        self.canvas.create_text(18, 22, text="NOSAVE", font=("Segoe UI", 9, "bold"), fill="#7a7a7a", anchor="w")
        
        # Large status
        self.status_text = self.canvas.create_text(18, 45, text="DISABLED", font=("Segoe UI", 26, "bold"), fill=C_GREEN_BRIGHT, anchor="w")
        
        # Bottom hint
        self.canvas.create_text(18, 70, text="CTRL+ALT • F8: MODE • F9: ON • F12: OFF", font=("Segoe UI", 6), fill="#c2c2c2", anchor="w")
        
        # Animation state
        self.color_animating = False
        self.current_color = C_GREEN_BRIGHT
        self.target_color = C_GREEN_BRIGHT
        self.anim_step = 0
        self.anim_total = 60
    
    def set_status(self, is_enabled: bool, animated: bool = True):
        """Update status with color animation"""
        if is_enabled:
            self.canvas.itemconfig(self.status_text, text="ENABLED")
            self.target_color = C_RED_BRIGHT
        else:
            self.canvas.itemconfig(self.status_text, text="DISABLED")
            self.target_color = C_GREEN_BRIGHT
        
        if animated and not self.color_animating:
            self.color_animating = True
            self.anim_step = 0
            self._animate_color()
        else:
            self._apply_color(self.target_color)
            self.current_color = self.target_color
    
    def _animate_color(self):
        """Smooth color transition"""
        if self.anim_step >= self.anim_total:
            self._apply_color(self.target_color)
            self.current_color = self.target_color
            self.color_animating = False
            return
        
        progress = self.anim_step / self.anim_total
        eased = Animator.ease_out_quint(progress)
        color = ColorUtil.interpolate(self.current_color, self.target_color, eased)
        
        try:
            self._apply_color(color)
            self.anim_step += 1
            self.after(16, self._animate_color)
        except tk.TclError:
            pass
    
    def _apply_color(self, color: str):
        """Apply color to status elements"""
        self.canvas.itemconfig(self.status_text, fill=color)
        self.canvas.itemconfig(self.accent_bar, fill=color)


class GTAMiniIndicator(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)  # ← Line 1: Frame transparent
        self.size = 75
        
        self.canvas = tk.Canvas(
            self, width=self.size, height=self.size,
            bg=C_PURE_BLACK,  # ← Line 2: Canvas transparent
            highlightthickness=0, bd=0,
            highlightbackground=C_PURE_BLACK  # ← Line 3: Border transparent
        )
        
        self.canvas.pack()
        
        center = self.size / 2
        
        # Create smooth fading glow layers (6 layers for perfect gradient)
        self.glow_layers = []
        base_color = C_GREEN_BRIGHT
        
        # Layer configuration: radius and alpha
        layer_config = [
            (30, 0.01),  # Outermost - very faint
            (26, 0.15),
            (22, 0.25),
            (18, 0.40),
            (14, 0.60),
            (11, 0.70),  # Innermost - almost solid
        ]
        
        for radius, alpha in layer_config:
            color = ColorUtil.with_alpha(base_color, alpha)
            layer = self.canvas.create_oval(
                center - radius, center - radius,
                center + radius, center + radius,
                fill=color, outline="", width=0
            )
            self.glow_layers.append((layer, radius, alpha))
        
        # Solid bright core
        self.core = self.canvas.create_oval(
            center - 7, center - 7, center + 7, center + 7,
            fill=C_GREEN_BRIGHT, outline="", width=0
        )
        
        # Bright highlight (glass reflection effect)
        self.highlight = self.canvas.create_oval(
            center - 2.5, center - 2.5, center + 2.5, center + 2.5,
            fill="#ffffff", outline="", width=0
        )
        
        # Animation state
        self.breath_time = 0.0
        self.shimmer_time = 0.0
        self.wave_time = 0.0
        self.status = "OFF"
        self.base_color = C_GREEN_BRIGHT
    
    def update_status(self, status: str):
        """Update colors maintaining glass effect"""
        self.status = status
        
        if status == "ON":
            self.base_color = C_RED_BRIGHT
        else:
            self.base_color = C_GREEN_BRIGHT
        
        # Update core
        self.canvas.itemconfig(self.core, fill=self.base_color)
        
        # Update all glow layers with proper alpha
        for layer, radius, alpha in self.glow_layers:
            color = ColorUtil.with_alpha(self.base_color, alpha)
            self.canvas.itemconfig(layer, fill=color)
    
    def pulse(self):
        """
        Ultra-natural breathing animation
        Combines multiple sine waves + alpha pulsing for lifelike effect
        """
        # Three synchronized but offset time tracks
        self.breath_time += 0.022    # Primary breathing
        self.shimmer_time += 0.035   # Highlight shimmer
        self.wave_time += 0.028      # Secondary wave
        
        center = self.size / 2
        
        try:
            # Animate each glow layer with parallax + alpha fade
            for i, (layer, base_radius, base_alpha) in enumerate(self.glow_layers):
                # Multi-wave organic movement
                breath = math.sin(self.breath_time + i * 0.3) * 1.8
                wave = math.sin(self.wave_time * 1.2 + i * 0.4) * 0.9
                micro = math.sin(self.breath_time * 2.5 + i * 0.2) * 0.3
                
                # Combined smooth movement
                offset = (breath + wave + micro) * (1 + i * 0.08)
                radius = base_radius + offset
                
                # Alpha pulsing (breathing opacity)
                alpha_pulse = math.sin(self.breath_time * 1.3 + i * 0.15) * 0.15
                dynamic_alpha = max(0.05, min(1.0, base_alpha + alpha_pulse))
                
                # Apply color with dynamic alpha
                color = ColorUtil.with_alpha(self.base_color, dynamic_alpha)
                self.canvas.itemconfig(layer, fill=color)
                
                # Update position
                self.canvas.coords(
                    layer,
                    center - radius, center - radius,
                    center + radius, center + radius
                )
            
            # Gentle core breathing
            core_breath = math.sin(self.breath_time * 0.95) * 0.6
            self.canvas.coords(
                self.core,
                center - 7 - core_breath, center - 7 - core_breath,
                center + 7 + core_breath, center + 7 + core_breath
            )
            
            # Glass highlight shimmer (realistic light reflection)
            shimmer = (math.sin(self.shimmer_time * 1.8) + 1) / 2  # 0 to 1
            shimmer_alpha = 0.6 + shimmer * 0.4  # 0.6 to 1.0
            shimmer_color = ColorUtil.with_alpha("#ffffff", shimmer_alpha)
            self.canvas.itemconfig(self.highlight, fill=shimmer_color)
            
            # Subtle highlight position shift (light moving)
            highlight_offset = math.sin(self.shimmer_time * 0.7) * 0.5
            self.canvas.coords(
                self.highlight,
                center - 2.5 + highlight_offset, center - 2.5 + highlight_offset,
                center + 2.5 + highlight_offset, center + 2.5 + highlight_offset
            )
            self.canvas.configure(bg=C_PURE_BLACK)
            self.configure(bg=C_PURE_BLACK)
        except tk.TclError:
            pass


class GTANotification(tk.Frame):
    """Clean notification"""
    
    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)
        self.width = 300
        self.height = 60
        
        self.canvas = tk.Canvas(
            self, width=self.width, height=self.height,
            bg=C_PURE_BLACK, highlightthickness=0, bd=0
        )
        self.canvas.pack()
        
        # Background
        self.bg = self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=C_BG_DARK, outline=C_BG_MEDIUM, width=1
        )
        
        # Left stripe
        self.stripe = self.canvas.create_rectangle(
            0, 0, 3, self.height,
            fill=C_BLUE_BRIGHT, outline=""
        )
        
        # Icon
        self.icon_circle = self.canvas.create_oval(
            12, 12, 48, 48,
            fill=C_BG_MEDIUM, outline=C_BLUE_BRIGHT, width=2
        )
        
        self.icon_text = self.canvas.create_text(
            30, 30,
            text="✓",
            font=("Segoe UI", 16, "bold"),
            fill=C_BLUE_BRIGHT
        )
        
        # Message
        self.msg_text = self.canvas.create_text(
            58, 30,
            text="",
            font=FONT_BODY,
            fill=C_TEXT_WHITE,
            anchor="w",
            width=230
        )
    
    def set_message(self, text: str, icon: str = "✓", accent_color: str = C_BLUE_BRIGHT):
        """Set message"""
        self.canvas.itemconfig(self.msg_text, text=text.upper())
        self.canvas.itemconfig(self.stripe, fill=accent_color)
        self.canvas.itemconfig(self.icon_text, text=icon, fill=accent_color)
        self.canvas.itemconfig(self.icon_circle, outline=accent_color)


class OverlayManager:
    """Overlay manager"""
    
    def __init__(self):
        self.root = tk.Tk()
        
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.attributes("-alpha", 0.80)
        
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        
        self.master_frame = tk.Frame(self.root, bg="black")
        self.master_frame.pack(fill="both", expand=True)
        
        # UI Components
        self.full_overlay = GTAInteractionMenu(self.master_frame)
        self.full_overlay.place(x=30, y=30)
        
        self.mini_overlay = GTAMiniIndicator(self.master_frame)
        self.mini_overlay.configure(bg=C_PURE_BLACK)  
        self.mini_overlay.place(x=30, y=30)
        self.mini_overlay.place_forget()
        
        self.notification = GTANotification(self.master_frame)
        self.notification_x_rest = 30
        self.notification_x_hidden = -320
        self.notification_y = 145  # Adjusted for 100px height menu
        
        self.notification.place_forget()
        
        # State
        self.show_full = True
        self.menu_visible = False
        self.notif_visible = False
        self.notif_timer: Optional[str] = None
        self.notif_animating = False
        
        # Animation
        self.menu_y_target = 30
        self.menu_y_current = -300
        
        self.notif_x_current = self.notification_x_hidden
        self.notif_x_target = self.notification_x_hidden
        
        self.last_time = time.time()
        
        self.check_gta_focused()
        self.animate_loop()
    
    def animate_loop(self):
        """Animation loop"""
        current_time = time.time()
        self.last_time = current_time
        
        # Menu slide
        if self.menu_visible:
            self.menu_y_target = 30
        else:
            self.menu_y_target = -300
        
        diff = self.menu_y_target - self.menu_y_current
        
        if abs(diff) > 1.0:
            self.menu_y_current += diff * 0.15
            
            y = int(self.menu_y_current)
            if self.show_full:
                self.full_overlay.place(x=30, y=y)
            else:
                self.mini_overlay.place(x=30, y=y)
        
        # Notification slide
        if self.notif_animating:
            notif_diff = self.notif_x_target - self.notif_x_current
            
            if abs(notif_diff) > 1.0:
                self.notif_x_current += notif_diff * 0.2
                self.notification.place(x=int(self.notif_x_current), y=self.notification_y)
            else:
                self.notif_x_current = self.notif_x_target
                self.notification.place(x=int(self.notif_x_current), y=self.notification_y)
                self.notif_animating = False
                
                if not self.notif_visible:
                    self.notification.place_forget()
        
        # Mini pulse
        if not self.show_full and self.menu_visible:
            self.mini_overlay.pulse()
        
        self.root.after(16, self.animate_loop)
    
    def show_notification(
        self,
        message: str,
        color: str = C_BLUE_BRIGHT,
        duration: int = 4000
    ):
        """Show notification"""
        color_map = {
            "#ef4444": ("✗", C_RED_BRIGHT),
            "#E03232": ("✗", C_RED_BRIGHT),
            "#85BB65": ("✓", C_GREEN_BRIGHT),
            "#3b82f6": ("ℹ", C_BLUE_BRIGHT),
            "#a855f7": ("⚡", C_PURPLE_BRIGHT),
            "#10b981": ("✓", C_GREEN_BRIGHT),
            "#f59e0b": ("⚠", C_ORANGE_BRIGHT),
        }
        
        icon, actual_color = color_map.get(color, ("ℹ", color))
        
        self.notification.set_message(message, icon, actual_color)
        
        if self.notif_timer:
            try:
                self.root.after_cancel(self.notif_timer)
            except:
                pass
        
        if self.notif_visible:
            self.notif_timer = self.root.after(duration, self._hide_notification)
            return
        
        self.notif_x_current = self.notification_x_hidden
        self.notification.place(x=self.notification_x_hidden, y=self.notification_y)
        
        self.notif_x_target = self.notification_x_rest
        self.notif_visible = True
        self.notif_animating = True
        
        self.notif_timer = self.root.after(duration, self._hide_notification)
    
    def _hide_notification(self):
        """Hide notification"""
        self.notif_x_target = self.notification_x_hidden
        self.notif_visible = False
        self.notif_animating = True
    
    def update_status(self, status: str):
        """Update status"""
        is_enabled = (status == "ON")
        self.full_overlay.set_status(is_enabled, animated=True)
        self.mini_overlay.update_status(status)
    
    def toggle_mode(self):
        """Toggle mode"""
        self.show_full = not self.show_full
        
        if self.show_full:
            self.mini_overlay.place_forget()
            self.full_overlay.place(x=30, y=int(self.menu_y_current))
        else:
            self.full_overlay.place_forget()
            self.mini_overlay.place(x=30, y=int(self.menu_y_current))
    
    def check_gta_focused(self):
        """Check GTA focus"""
        try:
            hwnd_active = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd_active)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd_active, buff, length + 1)
            active_title = buff.value
            
            is_gta = any(t.lower() in active_title.lower() for t in GTA_WINDOW_TITLES)
            
            if is_gta:
                if win32gui:
                    try:
                        hwnd_gta = win32gui.FindWindow(None, "Grand Theft Auto V")
                        if hwnd_gta:
                            rect = win32gui.GetWindowRect(hwnd_gta)
                            x, y = rect[0], rect[1]
                            w, h = rect[2] - rect[0], rect[3] - rect[1]
                            
                            if abs(self.root.winfo_x() - x) > 10 or abs(self.root.winfo_y() - y) > 10:
                                self.root.geometry(f"{w}x{h}+{x}+{y}")
                    except:  # noqa: E722
                        pass
                
                if not self.menu_visible:
                    self.menu_visible = True
            else:
                if self.menu_visible:
                    self.menu_visible = False
        
        except Exception:
            pass
        
        self.root.after(500, self.check_gta_focused)
    
    @staticmethod
    def get_window_bbox() -> tuple[int, int, int, int] | None:
        """Get GTA window bounds"""
        if not win32gui:
            return None
        
        try:
            hwnd = win32gui.FindWindow(None, "Grand Theft Auto V")
            if hwnd:
                return win32gui.GetWindowRect(hwnd)
        except:
            pass
        return None
    
    def start(self):
        """Start"""
        self.root.mainloop()