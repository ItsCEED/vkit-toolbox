"""
GTA V Style Overlay - Optimized Edition
Performance optimizations with LRU cache, buffer reuse, and proper cleanup
"""
import ctypes
import math
import time
import tkinter as tk
from functools import lru_cache
from typing import Optional, Tuple
import win32gui


# ===== ENHANCED COLOR PALETTE =====
C_PURE_BLACK = "#000000"
C_BG_DARKEST = "#050505"
C_BG_DARK = "#0d0d0d"
C_BG_MEDIUM = "#1a1a1a"
C_BG_LIGHTER = "#242424"

C_TEXT_WHITE = "#ffffff"
C_TEXT_LIGHT = "#e8e8e8"
C_TEXT_GREY = "#b0b0b0"
C_TEXT_DIM = "#808080"
C_TEXT_DARKER = "#505050"

C_GTA_CYAN = "#00d4ff"
C_GTA_BLUE = "#0080ff"
C_GTA_ORANGE = "#ff8c00"
C_GTA_YELLOW = "#ffcc00"
C_GREEN_SAFE = "#7dd956"
C_GREEN_BRIGHT = "#85BB65"
C_RED_DANGER = "#ff3860"
C_RED_BRIGHT = "#E03232"
C_PURPLE = "#c084fc"

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_HEADER = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 7, "bold")
FONT_TINY = ("Segoe UI", 6)

GTA_WINDOW_TITLES = ["Grand Theft Auto V", "GTA V", "gta5.exe"]



class Animator:
    """Enhanced animation easing functions"""

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

    @staticmethod
    def ease_out_back(x: float) -> float:
        """Overshoots slightly then settles - very GTA-like"""
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * pow(x - 1, 3) + c1 * pow(x - 1, 2)



class ColorUtil:
    """Optimized color utilities with LRU cache"""

    @staticmethod
    @lru_cache(maxsize=128)
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple (cached)"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    @staticmethod
    @lru_cache(maxsize=256)
    def interpolate_cached(color1: str, color2: str, progress_key: float) -> str:
        """Cached color interpolation with rounded progress"""
        rgb1 = ColorUtil.hex_to_rgb(color1)
        rgb2 = ColorUtil.hex_to_rgb(color2)

        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * progress_key)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * progress_key)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * progress_key)

        return ColorUtil.rgb_to_hex((r, g, b))

    @staticmethod
    def interpolate(color1: str, color2: str, progress: float) -> str:
        """Color interpolation with automatic caching"""
        progress_key = round(progress, 2)
        return ColorUtil.interpolate_cached(color1, color2, progress_key)

    @staticmethod
    @lru_cache(maxsize=256)
    def with_alpha(color: str, alpha: float) -> str:
        """Apply alpha blending (cached)"""
        rgb = ColorUtil.hex_to_rgb(color)
        r = int(rgb[0] * alpha)
        g = int(rgb[1] * alpha)
        b = int(rgb[2] * alpha)
        return ColorUtil.rgb_to_hex((r, g, b))

    @staticmethod
    @lru_cache(maxsize=128)
    def add_glow(color: str, intensity: float = 1.2) -> str:
        """Add glow effect (cached)"""
        rgb = ColorUtil.hex_to_rgb(color)
        r = min(255, int(rgb[0] * intensity))
        g = min(255, int(rgb[1] * intensity))
        b = min(255, int(rgb[2] * intensity))
        return ColorUtil.rgb_to_hex((r, g, b))



class GTAInteractionMenu(tk.Frame):
    """Enhanced full menu with glow effects and shake animation"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)
        self.width = 280
        self.height = 80

        self.canvas = tk.Canvas(
            self, width=self.width, height=self.height,
            bg=C_PURE_BLACK, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Layered background for depth
        self.canvas.create_rectangle(0, 0, self.width, self.height, 
                                      fill=C_BG_DARKEST, outline="", width=0)
        self.canvas.create_rectangle(12, 0, self.width, self.height,
                                      fill=C_BG_DARK, outline="", width=0)
        self.canvas.create_line(12, 0, self.width, 0, fill=C_BG_LIGHTER, width=1)

        # Left accent bar
        self.accent_bar = self.canvas.create_rectangle(
            0, 0, 12, self.height, 
            fill=C_GREEN_BRIGHT, outline="", width=0
        )

        # Inner accent line
        self.inner_accent = self.canvas.create_line(
            12, 0, 12, self.height, 
            fill=C_GREEN_BRIGHT, width=2
        )

        # Feature title
        self.canvas.create_text(24, 15, text="◆ NOSAVE", font=FONT_HEADER, 
                               fill=C_TEXT_GREY, anchor="nw")

        # Status text with glow effect
        self.status_glow = self.canvas.create_text(
            25, 46, text="DISABLED", 
            font=("Segoe UI", 28, "bold"), 
            fill=ColorUtil.with_alpha(C_GREEN_BRIGHT, 0.3), 
            anchor="w"
        )
        self.status_text = self.canvas.create_text(
            24, 47, text="DISABLED", 
            font=("Segoe UI", 28, "bold"), 
            fill=C_GREEN_BRIGHT, anchor="w"
        )

        # Animation state
        self.color_animating = False
        self.shake_amount = 0
        self.shake_offset = 0
        self.current_color = C_GREEN_BRIGHT
        self.target_color = C_GREEN_BRIGHT
        self.anim_step = 0
        self.anim_total = 45

    def set_status(self, is_enabled: bool, animated: bool = True):
        """Update status with animation and shake"""
        if is_enabled:
            self.canvas.itemconfig(self.status_text, text="ENABLED")
            self.canvas.itemconfig(self.status_glow, text="ENABLED")
            self.target_color = C_RED_BRIGHT
            self.shake_amount = 3
        else:
            self.canvas.itemconfig(self.status_text, text="DISABLED")
            self.canvas.itemconfig(self.status_glow, text="DISABLED")
            self.target_color = C_GREEN_BRIGHT
            self.shake_amount = 3

        if animated and not self.color_animating:
            self.color_animating = True
            self.anim_step = 0
            self._animate_color()
        else:
            self._apply_color(self.target_color)
            self.current_color = self.target_color

    def _animate_color(self):
        """Smooth transition with shake effect"""
        if self.anim_step >= self.anim_total:
            self._apply_color(self.target_color)
            self.current_color = self.target_color
            self.color_animating = False
            return

        progress = self.anim_step / self.anim_total
        eased = Animator.ease_out_back(progress)
        color = ColorUtil.interpolate(self.current_color, self.target_color, eased)

        try:
            self._apply_color(color)

            # Shake effect
            if self.shake_amount > 0:
                new_shake = math.sin(self.anim_step * 2) * self.shake_amount
                shake_delta = new_shake - self.shake_offset

                self.canvas.move(self.status_text, shake_delta, 0)
                self.canvas.move(self.status_glow, shake_delta, 0)

                self.shake_offset = new_shake
                self.shake_amount *= 0.85

            self.anim_step += 1
            self.after(16, self._animate_color)
        except tk.TclError:
            pass

    def _apply_color(self, color: str):
        """Apply color to all elements"""
        self.canvas.itemconfig(self.status_text, fill=color)
        self.canvas.itemconfig(self.status_glow, fill=ColorUtil.with_alpha(color, 0.3))
        self.canvas.itemconfig(self.accent_bar, fill=color)
        self.canvas.itemconfig(self.inner_accent, fill=color)



class GTAMiniIndicator(tk.Frame):
    """Enhanced mini with rotating ring and status letter"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)
        self.size = 90

        self.canvas = tk.Canvas(
            self, width=self.size, height=self.size,
            bg=C_PURE_BLACK, highlightthickness=0, bd=0
        )
        self.canvas.pack()

        self.center = self.size / 2

        # Rotating ring
        self.ring_radius = 38
        self.ring_arc = self.canvas.create_arc(
            self.center - self.ring_radius, self.center - self.ring_radius,
            self.center + self.ring_radius, self.center + self.ring_radius,
            start=0, extent=270, outline=C_GREEN_BRIGHT,
            width=3, style="arc"
        )

        # Glow layers
        self.glow_layers = []
        base_color = C_GREEN_BRIGHT

        layer_config = [
            (32, 0.08), (28, 0.15), (24, 0.25),
            (20, 0.40), (16, 0.60), (12, 0.80),
        ]

        for i, (radius, alpha) in enumerate(layer_config):
            color = ColorUtil.with_alpha(base_color, alpha)
            layer = self.canvas.create_oval(
                self.center - radius, self.center - radius,
                self.center + radius, self.center + radius,
                fill=color, outline="", width=0
            )
            self.glow_layers.append({
                'id': layer,
                'base_radius': radius,
                'base_alpha': alpha,
                'index': i
            })

        # Core
        self.core = self.canvas.create_oval(
            self.center - 8, self.center - 8,
            self.center + 8, self.center + 8,
            fill=C_GREEN_BRIGHT, outline="", width=0
        )

        # Highlight
        self.highlight = self.canvas.create_oval(
            self.center - 3, self.center - 3,
            self.center + 3, self.center + 3,
            fill="#ffffff", outline="", width=0
        )

        # Status letter
        self.status_letter = self.canvas.create_text(
            self.center, self.center, text="D",
            font=("Segoe UI", 12, "bold"), fill="#000000"
        )

        # Animation state
        self.breath_time = 0.0
        self.shimmer_time = 0.0
        self.ring_rotation = 0.0
        self.status = "OFF"
        self.base_color = C_GREEN_BRIGHT
        self._frame_counter = 0
        self._update_interval = 1

    def update_status(self, status: str):
        """Update colors and letter"""
        self.status = status
        self.base_color = C_RED_BRIGHT if status == "ON" else C_GREEN_BRIGHT
        letter = "E" if status == "ON" else "D"

        self.canvas.itemconfig(self.core, fill=self.base_color)
        self.canvas.itemconfig(self.ring_arc, outline=self.base_color)
        self.canvas.itemconfig(self.status_letter, text=letter)

        for layer_data in self.glow_layers:
            color = ColorUtil.with_alpha(self.base_color, layer_data['base_alpha'])
            self.canvas.itemconfig(layer_data['id'], fill=color)

    def pulse(self):
        """Optimized breathing with rotating ring"""
        self._frame_counter += 1
        if self._frame_counter % self._update_interval != 0:
            return

        self.breath_time += 0.025
        self.shimmer_time += 0.040
        self.ring_rotation += 2.5

        # Pre-calculate sine values
        sin_breath = math.sin(self.breath_time)
        sin_shimmer = math.sin(self.shimmer_time * 1.6)

        try:
            # Batch updates
            coords_updates = []
            color_updates = []

            for layer_data in self.glow_layers:
                i = layer_data['index']
                base_radius = layer_data['base_radius']
                base_alpha = layer_data['base_alpha']
                layer_id = layer_data['id']

                breath = sin_breath * math.cos(i * 0.3) * 1.6
                wave = math.sin(self.breath_time * 1.4 + i * 0.4) * 0.8
                offset = (breath + wave) * (1 + i * 0.1)
                radius = base_radius + offset

                alpha_pulse = math.sin(self.breath_time * 1.2 + i * 0.2) * 0.12
                dynamic_alpha = max(0.05, min(1.0, base_alpha + alpha_pulse))

                color = ColorUtil.with_alpha(self.base_color, dynamic_alpha)
                coords_updates.append((layer_id, radius))
                color_updates.append((layer_id, color))

            # Apply updates
            for layer_id, radius in coords_updates:
                self.canvas.coords(
                    layer_id,
                    self.center - radius, self.center - radius,
                    self.center + radius, self.center + radius
                )

            for layer_id, color in color_updates:
                self.canvas.itemconfig(layer_id, fill=color)

            # Core breathing
            core_breath = sin_breath * 0.8
            self.canvas.coords(
                self.core,
                self.center - 8 - core_breath, self.center - 8 - core_breath,
                self.center + 8 + core_breath, self.center + 8 + core_breath
            )

            # Highlight shimmer
            shimmer = (sin_shimmer + 1) / 2
            shimmer_alpha = 0.7 + shimmer * 0.3
            shimmer_color = ColorUtil.with_alpha("#ffffff", shimmer_alpha)
            self.canvas.itemconfig(self.highlight, fill=shimmer_color)

            # Rotate ring
            self.canvas.itemconfig(self.ring_arc, start=self.ring_rotation % 360)

        except tk.TclError:
            pass



class GTANotification(tk.Frame):
    """Enhanced notification with title/message split"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)
        self.width = 340
        self.height = 70

        self.canvas = tk.Canvas(
            self, width=self.width, height=self.height,
            bg=C_PURE_BLACK, highlightthickness=0, bd=0
        )
        self.canvas.pack()

        # Shadow layer
        self.shadow = self.canvas.create_rectangle(
            2, 2, self.width, self.height,
            fill=C_BG_DARKEST, outline="", width=0
        )

        # Main background
        self.bg = self.canvas.create_rectangle(
            0, 0, self.width - 2, self.height - 2,
            fill=C_BG_DARK, outline=C_BG_LIGHTER, width=1
        )

        # Left stripe
        self.stripe = self.canvas.create_rectangle(
            0, 0, 4, self.height - 2,
            fill=C_GTA_CYAN, outline=""
        )

        # Icon
        self.icon_bg = self.canvas.create_oval(14, 14, 56, 56, fill=C_BG_MEDIUM, outline="")
        self.icon_circle = self.canvas.create_oval(
            16, 16, 54, 54,
            fill="", outline=C_GTA_CYAN, width=3
        )
        self.icon_text = self.canvas.create_text(
            35, 35, text="✓",
            font=("Segoe UI", 20, "bold"),
            fill=C_GTA_CYAN
        )

        # Title and message
        self.title_text = self.canvas.create_text(
            68, 22, text="",
            font=FONT_HEADER, fill=C_TEXT_WHITE, anchor="w"
        )
        self.msg_text = self.canvas.create_text(
            68, 42, text="",
            font=FONT_BODY, fill=C_TEXT_GREY, anchor="w", width=260
        )

    def set_message(self, title: str, message: str = "", icon: str = "✓", 
                    accent_color: str = C_GTA_CYAN):
        """Set notification content"""
        self.canvas.itemconfig(self.title_text, text=title.upper())
        self.canvas.itemconfig(self.msg_text, text=message)
        self.canvas.itemconfig(self.stripe, fill=accent_color)
        self.canvas.itemconfig(self.icon_text, text=icon, fill=accent_color)
        self.canvas.itemconfig(self.icon_circle, outline=accent_color)



class OverlayManager:
    """Optimized overlay with LRU cache and proper cleanup"""

    # Animation constants
    MENU_Y_VISIBLE = 40
    MENU_Y_HIDDEN = -400
    MENU_ANIM_SPEED = 0.18

    NOTIF_X_VISIBLE = 40
    NOTIF_X_HIDDEN = -360
    NOTIF_Y = 170
    NOTIF_ANIM_SPEED = 0.22

    # Performance constants
    TARGET_FPS = 60
    WINDOW_CHECK_INTERVAL = 0.5
    POSITION_UPDATE_THRESHOLD = 10

    # Notification icon mapping
    ICON_MAP = {
        C_RED_BRIGHT: "✗", C_RED_DANGER: "✗",
        C_GREEN_BRIGHT: "✓", C_GREEN_SAFE: "✓",
        C_GTA_CYAN: "ℹ", C_GTA_BLUE: "ℹ",
        C_PURPLE: "⚡",
        C_GTA_ORANGE: "⚠", C_GTA_YELLOW: "⚠",
    }

    def __init__(self):
        self.root = tk.Tk()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.attributes("-alpha", 0.95)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_w}x{self.screen_h}+0+0")

        self.master_frame = tk.Frame(self.root, bg="black")
        self.master_frame.pack(fill="both", expand=True)

        # UI Components
        self.full_overlay = GTAInteractionMenu(self.master_frame)
        self.full_overlay.place(x=self.MENU_Y_VISIBLE, y=self.MENU_Y_VISIBLE)

        self.mini_overlay = GTAMiniIndicator(self.master_frame)
        self.mini_overlay.place(x=self.MENU_Y_VISIBLE, y=self.MENU_Y_VISIBLE)
        self.mini_overlay.place_forget()

        self.notification = GTANotification(self.master_frame)
        self.notification.place_forget()

        # State
        self.show_full = True
        self.menu_visible = False
        self.notif_visible = False
        self.notif_timer: Optional[str] = None
        self.notif_animating = False

        # Animation
        self.menu_y_target = self.MENU_Y_VISIBLE
        self.menu_y_current = self.MENU_Y_HIDDEN
        self.notif_x_current = self.NOTIF_X_HIDDEN
        self.notif_x_target = self.NOTIF_X_HIDDEN

        # Optimization
        self._animation_dirty = {'menu': True, 'notification': False, 'pulse': False}
        self._gta_hwnd = None
        self._last_window_check = 0
        self._window_check_interval = self.WINDOW_CHECK_INTERVAL
        self._last_geometry = None
        self._last_status = None
        self._frame_time = 1000 / self.TARGET_FPS

        # Window buffer for reuse
        self._window_buffer = ctypes.create_unicode_buffer(256)

        # Setup cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)

        self.check_gta_focused()
        self.animate_loop()

    def check_gta_focused(self):
        """Optimized focus check with buffer reuse"""
        current_time = time.time()

        if current_time - self._last_window_check < self._window_check_interval:
            self.root.after(100, self.check_gta_focused)
            return

        self._last_window_check = current_time

        try:
            hwnd_active = ctypes.windll.user32.GetForegroundWindow()

            if self._gta_hwnd and hwnd_active == self._gta_hwnd:
                if not self.menu_visible:
                    self.menu_visible = True
                    self._animation_dirty['menu'] = True
                self._update_overlay_position()
                self.root.after(500, self.check_gta_focused)
                return

            # Reuse window buffer
            length = ctypes.windll.user32.GetWindowTextW(
                hwnd_active, self._window_buffer, 256
            )

            if length == 0:
                if self.menu_visible:
                    self.menu_visible = False
                    self._animation_dirty['menu'] = True
                self.root.after(500, self.check_gta_focused)
                return

            active_title = self._window_buffer.value

            is_gta = any(t.lower() in active_title.lower() for t in GTA_WINDOW_TITLES)

            if is_gta:
                self._gta_hwnd = hwnd_active
                if not self.menu_visible:
                    self.menu_visible = True
                    self._animation_dirty['menu'] = True
                self._update_overlay_position()
            else:
                if self.menu_visible:
                    self.menu_visible = False
                    self._animation_dirty['menu'] = True
                    self._gta_hwnd = None

        except Exception:
            if self.menu_visible:
                self.menu_visible = False
                self._animation_dirty['menu'] = True
                self._gta_hwnd = None

        self.root.after(500, self.check_gta_focused)

    def _update_overlay_position(self):
        """Throttled position updates"""
        if not win32gui or not self._gta_hwnd:
            return

        try:
            rect = win32gui.GetWindowRect(self._gta_hwnd)
            new_geometry = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])

            if self._last_geometry != new_geometry:
                x, y, w, h = new_geometry

                if (self._last_geometry is None or
                    abs(x - self._last_geometry[0]) > self.POSITION_UPDATE_THRESHOLD or
                    abs(y - self._last_geometry[1]) > self.POSITION_UPDATE_THRESHOLD or
                    abs(w - self._last_geometry[2]) > self.POSITION_UPDATE_THRESHOLD or
                    abs(h - self._last_geometry[3]) > self.POSITION_UPDATE_THRESHOLD):

                    self.root.geometry(f"{w}x{h}+{x}+{y}")
                    self._last_geometry = new_geometry
        except Exception:
            pass

    def animate_loop(self):
        """Optimized animation with adaptive frame rate"""
        start_time = time.time()

        menu_updated = self._animate_menu()
        notif_updated = self._animate_notification()
        pulse_updated = self._animate_pulse()

        any_animation = menu_updated or notif_updated or pulse_updated

        if not any_animation:
            self.root.after(33, self.animate_loop)
        else:
            elapsed = (time.time() - start_time) * 1000
            next_frame = max(1, int(self._frame_time - elapsed))
            self.root.after(next_frame, self.animate_loop)

    def _animate_menu(self) -> bool:
        """Menu animation with back easing"""
        if not self._animation_dirty['menu']:
            return False

        self.menu_y_target = self.MENU_Y_VISIBLE if self.menu_visible else self.MENU_Y_HIDDEN
        diff = self.menu_y_target - self.menu_y_current

        if abs(diff) < 0.5:
            self.menu_y_current = self.menu_y_target
            self._animation_dirty['menu'] = False
            return False

        self.menu_y_current += diff * self.MENU_ANIM_SPEED
        y = int(self.menu_y_current)

        if self.show_full:
            self.full_overlay.place(x=self.MENU_Y_VISIBLE, y=y)
        else:
            self.mini_overlay.place(x=self.MENU_Y_VISIBLE, y=y)

        return True

    def _animate_notification(self) -> bool:
        """Notification slide animation"""
        if not self.notif_animating:
            return False

        notif_diff = self.notif_x_target - self.notif_x_current

        if abs(notif_diff) < 0.5:
            self.notif_x_current = self.notif_x_target
            self.notification.place(x=int(self.notif_x_current), y=self.NOTIF_Y)
            self.notif_animating = False

            if not self.notif_visible:
                self.notification.place_forget()
            return False

        self.notif_x_current += notif_diff * self.NOTIF_ANIM_SPEED
        self.notification.place(x=int(self.notif_x_current), y=self.NOTIF_Y)
        return True

    def _animate_pulse(self) -> bool:
        """Pulse animation for mini mode (only when visible)"""
        if not self.show_full and self.menu_visible:
            self.mini_overlay.pulse()
            return True
        return False

    def show_notification(
        self,
        title: str,
        message: str = "",
        color: str = C_GTA_CYAN,
        duration: int = 4000
    ) -> None:
        """Show notification with title/message"""
        icon = self.ICON_MAP.get(color, "●")
        self.notification.set_message(title, message, icon, color)

        # Cancel existing timer safely
        if self.notif_timer:
            try:
                self.root.after_cancel(self.notif_timer)
            except (ValueError, tk.TclError):
                pass
            finally:
                self.notif_timer = None

        if self.notif_visible:
            self.notif_timer = self.root.after(duration, self._hide_notification)
            return

        self.notif_x_current = self.NOTIF_X_HIDDEN
        self.notification.place(x=self.NOTIF_X_HIDDEN, y=self.NOTIF_Y)

        self.notif_x_target = self.NOTIF_X_VISIBLE
        self.notif_visible = True
        self.notif_animating = True

        self.notif_timer = self.root.after(duration, self._hide_notification)

    def _hide_notification(self):
        """Hide notification"""
        self.notif_x_target = self.NOTIF_X_HIDDEN
        self.notif_visible = False
        self.notif_animating = True
        self.notif_timer = None

    def update_status(self, status: str):
        """Update status with lazy evaluation"""
        is_enabled = (status == "ON")

        if hasattr(self, '_last_status') and self._last_status == status:
            return

        self._last_status = status
        self.full_overlay.set_status(is_enabled, animated=True)
        self.mini_overlay.update_status(status)
        self._animation_dirty['menu'] = True

    def toggle_mode(self):
        """Toggle display mode"""
        self.show_full = not self.show_full

        if self.show_full:
            self.mini_overlay.place_forget()
            self.full_overlay.place(x=self.MENU_Y_VISIBLE, y=int(self.menu_y_current))
        else:
            self.full_overlay.place_forget()
            self.mini_overlay.place(x=self.MENU_Y_VISIBLE, y=int(self.menu_y_current))

        self.root.update_idletasks()

    @staticmethod
    def get_window_bbox() -> Optional[Tuple[int, int, int, int]]:
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

    def cleanup(self):
        """Clean up resources before exit"""
        # Cancel timers
        if self.notif_timer:
            try:
                self.root.after_cancel(self.notif_timer)
            except:
                pass

        # Clear LRU caches
        ColorUtil.hex_to_rgb.cache_clear()
        ColorUtil.interpolate_cached.cache_clear()
        ColorUtil.with_alpha.cache_clear()
        ColorUtil.add_glow.cache_clear()

        # Destroy window
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

    def start(self):
        """Start overlay"""
        try:
            self.root.mainloop()
        finally:
            self.cleanup()
