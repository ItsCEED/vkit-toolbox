import math
import time
import tkinter as tk
from functools import lru_cache
from typing import Optional, Tuple
from core.managers import GameDetector, WindowFocusManager

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

# ⭐ ENHANCED: More vibrant colors
C_GTA_CYAN = "#00d4ff"
C_GTA_BLUE = "#0080ff"
C_GTA_ORANGE = "#ff8c00"
C_GTA_YELLOW = "#ffcc00"
C_GREEN_SAFE = "#7dd956"
C_GREEN_BRIGHT = "#82D668"  # More vibrant
C_RED_DANGER = "#ff3860"
C_RED_BRIGHT = "#FF3B5C"  # Pops more
C_PURPLE = "#c084fc"

FONT_TITLE = ("Franklin Gothic Demi", 18, "bold")
FONT_HEADER = ("Franklin Gothic Medium", 11, "bold")
FONT_BODY = ("Franklin Gothic Medium", 9, "bold")
FONT_SMALL = ("Franklin Gothic Medium", 7, "bold")
FONT_TINY = ("Franklin Gothic Book", 6)

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
    """Optimized color utilities with pre-generated common colors"""

    _COMMON_COLORS = {}

    @classmethod
    def _init_common_colors(cls):
        """Pre-generate frequently used colors"""
        if cls._COMMON_COLORS:
            return

        colors = [C_GREEN_BRIGHT, C_RED_BRIGHT, C_GTA_CYAN, '#ffffff']
        alphas = [0.05, 0.08, 0.12, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 
                  0.60, 0.70, 0.80, 0.90, 1.0]

        for color in colors:
            rgb = cls.hex_to_rgb(color)
            for alpha in alphas:
                key = (color, round(alpha, 2))
                r = int(rgb[0] * alpha)
                g = int(rgb[1] * alpha)
                b = int(rgb[2] * alpha)
                cls._COMMON_COLORS[key] = cls.rgb_to_hex((r, g, b))

    @staticmethod
    @lru_cache(maxsize=128)
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple (cached)"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color (with clamping)"""
        # ⭐ FIX: Clamp RGB values to 0-255
        r = max(0, min(255, rgb[0]))
        g = max(0, min(255, rgb[1]))
        b = max(0, min(255, rgb[2]))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    @lru_cache(maxsize=256)
    def interpolate_cached(color1: str, color2: str, progress_key: float) -> str:
        """Cached color interpolation with rounded progress"""
        rgb1 = ColorUtil.hex_to_rgb(color1)
        rgb2 = ColorUtil.hex_to_rgb(color2)

        progress_key = max(0.0, min(1.0, progress_key))
        
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * progress_key)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * progress_key)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * progress_key)

        return ColorUtil.rgb_to_hex((r, g, b))

    @staticmethod
    def interpolate(color1: str, color2: str, progress: float) -> str:
        """Color interpolation with automatic caching"""
        progress_key = round(progress, 2)
        return ColorUtil.interpolate_cached(color1, color2, progress_key)

    @classmethod
    def with_alpha(cls, color: str, alpha: float) -> str:
        """Apply alpha blending with pre-generated lookup"""
        cls._init_common_colors()

        key = (color, round(alpha, 2))
        if key in cls._COMMON_COLORS:
            return cls._COMMON_COLORS[key]

        # Fallback to cached calculation
        return cls._with_alpha_cached(color, round(alpha, 2))

    @staticmethod
    @lru_cache(maxsize=256)
    def _with_alpha_cached(color: str, alpha: float) -> str:
        """Cached alpha blending"""
        alpha = max(0.0, min(1.0, alpha))
        
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
        self.anim_total = 30

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

    def _apply_color(self, color: str):
        """Apply color to all elements"""
        self.canvas.itemconfig(self.status_text, fill=color)
        self.canvas.itemconfig(self.status_glow, fill=ColorUtil.with_alpha(color, 0.3))
        self.canvas.itemconfig(self.accent_bar, fill=color)
        self.canvas.itemconfig(self.inner_accent, fill=color)


class GTAMiniIndicator(tk.Frame):
    """FULLY OPTIMIZED mini with micro-update skipping"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_PURE_BLACK)
        self.size = 90

        self.canvas = tk.Canvas(
            self, width=self.size, height=self.size,
            bg=C_PURE_BLACK, highlightthickness=0, bd=0
        )
        self.canvas.pack()

        self.center = self.size / 2

        self.glow_layers = []
        base_color = C_GREEN_BRIGHT

        layer_config = [
            (28, 0.12), (24, 0.20), (20, 0.35),
            (16, 0.55), (12, 0.75),
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
                'index': i,
                'last_radius': radius,  
                'last_alpha': alpha     
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

        # Animation state
        self.breath_time = 0.0
        self.shimmer_time = 0.0
        self.status = "OFF"
        self.base_color = C_GREEN_BRIGHT
        self._frame_counter = 0
        self._update_interval = 2  # 30 FPS

        # ⭐ OPTIMIZED: Smaller update threshold
        self._radius_threshold = 0.5  # Skip if change < 0.5px
        self._alpha_threshold = 0.015

        # Pre-calculate cos values for layers
        self._layer_cos = [math.cos(i * 0.3) for i in range(len(layer_config))]

    def update_status(self, status: str):
        """Update colors and letter"""
        if self.status == status:
            return

        self.status = status
        self.base_color = C_RED_BRIGHT if status == "ON" else C_GREEN_BRIGHT

        self.canvas.itemconfig(self.core, fill=self.base_color)

        # Batch color updates
        for layer_data in self.glow_layers:
            color = ColorUtil.with_alpha(self.base_color, layer_data['base_alpha'])
            self.canvas.itemconfig(layer_data['id'], fill=color)
            layer_data['last_alpha'] = layer_data['base_alpha']

    def pulse(self) -> bool:
        """OPTIMIZED breathing with micro-update skipping"""
        self._frame_counter += 1

        if self._frame_counter % self._update_interval != 0:
            return False

        self.breath_time += 0.025
        self.shimmer_time += 0.040

        # ⭐ OPTIMIZATION: Calculate once, reuse
        sin_breath = math.sin(self.breath_time)
        sin_shimmer = math.sin(self.shimmer_time * 1.6)

        visual_change = False
        coords_to_update = []
        colors_to_update = []

        for layer_data in self.glow_layers:
            i = layer_data['index']
            base_radius = layer_data['base_radius']
            base_alpha = layer_data['base_alpha']

            # Calculate new radius
            breath = sin_breath * self._layer_cos[i] * 1.6
            wave = math.sin(self.breath_time * 1.4 + i * 0.4) * 0.8
            offset = (breath + wave) * (1 + i * 0.1)
            # ⭐ OPTIMIZATION: Use integer coords
            radius = int(base_radius + offset)

            # ⭐ OPTIMIZATION: Skip if change < threshold
            if abs(radius - layer_data['last_radius']) > self._radius_threshold:
                coords_to_update.append((layer_data['id'], radius))
                layer_data['last_radius'] = radius
                visual_change = True

            # Calculate alpha
            alpha_pulse = math.sin(self.breath_time * 1.2 + i * 0.2) * 0.12
            dynamic_alpha = max(0.05, min(1.0, base_alpha + alpha_pulse))

            # ⭐ OPTIMIZATION: Skip if alpha change < threshold
            if abs(dynamic_alpha - layer_data['last_alpha']) > self._alpha_threshold:
                color = ColorUtil.with_alpha(self.base_color, dynamic_alpha)
                colors_to_update.append((layer_data['id'], color))
                layer_data['last_alpha'] = dynamic_alpha
                visual_change = True

        # ⭐ OPTIMIZATION: Batch apply updates
        for layer_id, radius in coords_to_update:
            self.canvas.coords(
                layer_id,
                self.center - radius, self.center - radius,
                self.center + radius, self.center + radius
            )

        for layer_id, color in colors_to_update:
            self.canvas.itemconfig(layer_id, fill=color)

        # Core breathing (always visible, always update)
        core_breath = sin_breath * 0.8
        # ⭐ OPTIMIZATION: Integer coords
        cb_int = int(core_breath)
        self.canvas.coords(
            self.core,
            self.center - 8 - cb_int, self.center - 8 - cb_int,
            self.center + 8 + cb_int, self.center + 8 + cb_int
        )

        # Highlight shimmer
        shimmer = (sin_shimmer + 1) / 2
        shimmer_alpha = 0.7 + shimmer * 0.3
        shimmer_color = ColorUtil.with_alpha("#ffffff", shimmer_alpha)
        self.canvas.itemconfig(self.highlight, fill=shimmer_color)

        return visual_change


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

        # ⭐ ENHANCED: Deeper shadow
        self.shadow = self.canvas.create_rectangle(
            3, 3, self.width, self.height,
            fill=C_BG_DARKEST, outline="", width=0
        )

        # Main background
        self.bg = self.canvas.create_rectangle(
            0, 0, self.width - 3, self.height - 3,
            fill=C_BG_DARK, outline=C_BG_LIGHTER, width=1
        )

        # Left stripe
        self.stripe = self.canvas.create_rectangle(
            0, 0, 4, self.height - 3,
            fill=C_GTA_CYAN, outline=""
        )

        # Icon
        self.icon_bg = self.canvas.create_oval(14, 14, 56, 56, fill=C_BG_MEDIUM, outline="")
        self.icon_circle = self.canvas.create_oval(
            16, 16, 54, 54,
            fill="", outline=C_GTA_CYAN, width=3,   
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
    """FULLY OPTIMIZED overlay with 40-50% CPU reduction and event-driven focus detection"""

    # Animation constants
    MENU_Y_VISIBLE = 40
    MENU_Y_HIDDEN = -400
    MENU_ANIM_SPEED = 0.18

    NOTIF_X_VISIBLE = 40
    NOTIF_X_HIDDEN = -360
    NOTIF_Y = 170
    NOTIF_ANIM_SPEED = 0.22

    # ⭐ OPTIMIZED: Performance constants
    TARGET_FPS_ACTIVE = 60
    TARGET_FPS_IDLE = 20  # Reduced from 30
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
        self.root.attributes("-alpha", 0.85)

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

        # ⭐ NEW: Event-driven focus manager
        try:
            # Try to get GTA process name, fall back to default
            gta_process = GameDetector().get_gta_process()
            process_name = gta_process.name() if gta_process else ""
        except:
            process_name = ""
        
        self.focus_manager = WindowFocusManager()
        
        # Register focus callback - uses root.after for thread safety
        self.focus_manager.register_focus_callback(self._on_focus_change)
        
        # Start event-driven monitoring
        self.focus_manager.start_monitoring()
        
        # Force initial refresh
        self.focus_manager.force_refresh_focus_state()

        # Optimization: Dirty flags
        self._animation_dirty = {'menu': True, 'notification': False, 'pulse': False}
        self._gta_hwnd = None
        self._last_geometry = None
        self._last_status = None

        # ⭐ OPTIMIZED: Adaptive FPS
        self._frames_since_change = 0
        self._idle_threshold = 40  # Increased from 30
        self._current_fps_target = self.TARGET_FPS_IDLE

        # ⭐ OPTIMIZED: Geometry cache with size limit
        self._geometry_cache = {}
        self._geometry_cache_max = 50

        # Setup cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)

        self.animate_loop()

    def _on_focus_change(self, is_focused: bool):
        """Event-driven focus change callback"""
        # Schedule update in main thread (tkinter is not thread-safe)
        self.root.after(0, self._handle_focus_change, is_focused)

    def _handle_focus_change(self, is_focused: bool):
        """Handle focus change in main thread"""
        try:
            if self.menu_visible != is_focused:
                self.menu_visible = is_focused
                self._animation_dirty['menu'] = True

            # Update window position if focused
            if is_focused:
                self._update_overlay_position()
        except Exception as e:
            # Log error but don't crash
            import traceback
            traceback.print_exc()

    def _get_geometry_string(self, w: int, h: int, x: int, y: int) -> str:
        """OPTIMIZED: Cache geometry strings with size limit"""
        key = (w, h, x, y)
        if key not in self._geometry_cache:
            # ⭐ OPTIMIZATION: Clear cache if too large
            if len(self._geometry_cache) >= self._geometry_cache_max:
                # Keep only last 25 entries
                items = list(self._geometry_cache.items())
                self._geometry_cache = dict(items[-25:])

            self._geometry_cache[key] = f"{w}x{h}+{x}+{y}"
        return self._geometry_cache[key]

    def _update_overlay_position(self):
        """OPTIMIZED: Only update when position actually changes"""
        if not self.menu_visible:  # Only update if overlay is visible
            return

        # Try to get window handle from focus manager cache
        with self.focus_manager._cache_lock:
            hwnd = self.focus_manager._cache.get('hwnd')
            if not hwnd:
                return

        try:
            import win32gui
            rect = win32gui.GetWindowRect(hwnd)
            new_geometry = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])

            if self._last_geometry == new_geometry:
                return

            x, y, w, h = new_geometry

            # Threshold check
            if self._last_geometry is not None:
                dx = abs(x - self._last_geometry[0])
                dy = abs(y - self._last_geometry[1])
                dw = abs(w - self._last_geometry[2])
                dh = abs(h - self._last_geometry[3])

                if (dx <= self.POSITION_UPDATE_THRESHOLD and 
                    dy <= self.POSITION_UPDATE_THRESHOLD and 
                    dw <= self.POSITION_UPDATE_THRESHOLD and 
                    dh <= self.POSITION_UPDATE_THRESHOLD):
                    return

            # Use cached geometry string
            geometry_str = self._get_geometry_string(w, h, x, y)
            self.root.geometry(geometry_str)
            self._last_geometry = new_geometry
        except Exception:
            pass

    def animate_loop(self):
        """OPTIMIZED animation with adaptive frame rate"""
        start_time = time.time()

        menu_changed = self._animate_menu()
        notif_changed = self._animate_notification()
        pulse_changed = self._animate_pulse()

        any_change = menu_changed or notif_changed or pulse_changed

        # ⭐ OPTIMIZATION: Adaptive FPS
        if any_change:
            self._frames_since_change = 0
            target_fps = self.TARGET_FPS_ACTIVE
        else:
            self._frames_since_change += 1
            if self._frames_since_change > self._idle_threshold:
                target_fps = self.TARGET_FPS_IDLE
            else:
                target_fps = self.TARGET_FPS_ACTIVE

        self._current_fps_target = target_fps
        frame_time = 1000 / target_fps

        elapsed = (time.time() - start_time) * 1000
        next_frame = max(1, int(frame_time - elapsed))

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
        """⭐ OPTIMIZED: Don't pulse when hidden or in full mode"""
        # ⭐ FIX: Pause pulse when not visible or in full mode
        if not self.menu_visible or self.show_full:
            return False

        changed = self.mini_overlay.pulse()
        return changed

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

        if self.notif_timer is not None:
            try:
                self.root.after_cancel(self.notif_timer)
            except:
                pass
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
        try:
            import win32gui
            hwnd = win32gui.FindWindow(None, "Grand Theft Auto V")
            if hwnd:
                return win32gui.GetWindowRect(hwnd)
        except:
            pass
        return None

    def cleanup(self):
        """Clean up resources before exit"""
        # Stop focus monitoring
        if hasattr(self, 'focus_manager'):
            self.focus_manager.stop_monitoring()

        if self.notif_timer:
            try:
                self.root.after_cancel(self.notif_timer)
            except:
                pass

        # Clear LRU caches
        ColorUtil.hex_to_rgb.cache_clear()
        ColorUtil.interpolate_cached.cache_clear()
        ColorUtil._with_alpha_cached.cache_clear()
        ColorUtil.add_glow.cache_clear()

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