import cv2
import time
import keyboard
import numpy as np
from PIL import ImageGrab
from collections import deque, namedtuple
from rich.console import Console

console = Console()

# Casino Keypad specific constants (adjusted from your example)
DIGITS_LOOKUP = {
    (1, 0, 0, 0, 0): 1,
    (0, 1, 0, 0, 0): 2,
    (0, 0, 1, 0, 0): 3,
    (0, 0, 0, 1, 0): 4,
    (0, 0, 0, 0, 1): 5
}

height = [41, 149, 257, 365, 473]
length = [44, 152, 260, 368, 476, 584]
tofind = (454, 300, 1080, 830)

def dot_check(a, img):
    """Detect digit from dot pattern"""
    hint = []
    for i in range(0, 5):
        crop_img = img[height[i] - 20:height[i] + 20, length[a] - 20:length[a] + 20]
        if np.mean(crop_img) > 125:
            hint.append(1)
        else:
            hint.append(0)
    return DIGITS_LOOKUP[tuple(hint)]

def check_ready(bbox):
    """Wait for ready state (black pixel at specific position)"""
    while True:
        im = ImageGrab.grab(bbox)
        screen = im.resize((1920,1080)).crop(tofind)
        grayImage = cv2.cvtColor(np.array(screen), cv2.COLOR_BGR2GRAY)
        (thresh, blackAndWhiteImage) = cv2.threshold(grayImage, 215, 255, cv2.THRESH_BINARY)
        crop_img = blackAndWhiteImage[92:92 + 1, 44:44 + 1]
        if np.mean(crop_img) == 0:
            keyboard.press_and_release('w')
            time.sleep(0.025)
        elif np.mean(crop_img) == 255:
            break

def calculate_key_sequence(numbers):
    """Calculate optimal key sequence from detected numbers"""
    keyboardgo = []
    for i in range(0, 6):
        if i == 0:
            if numbers[i] == 1:
                keyboardgo.append('1')
            elif numbers[i] == 2:
                keyboardgo.append('s')
            elif numbers[i] == 3:
                keyboardgo.append('s')
                keyboardgo.append('s')
            elif numbers[i] == 4:
                keyboardgo.append('s')
                keyboardgo.append('s')
                keyboardgo.append('s')
            elif numbers[i] == 5:
                keyboardgo.append('s')
                keyboardgo.append('s')
                keyboardgo.append('s')
                keyboardgo.append('s')
        if i > 0:
            a = i - 1
            if numbers[i] == numbers[a]:
                keyboardgo.append('1')
            elif numbers[i] < numbers[a]:
                value = numbers[a] - numbers[i]
                for _ in range(0, value):
                    keyboardgo.append('w')
            elif numbers[i] > numbers[a]:
                value = numbers[i] - numbers[a]
                for _ in range(0, value):
                    keyboardgo.append('s')
        keyboardgo.append('return')
    return keyboardgo

def main(bbox):
    console.print("🔍 [bold cyan]Casino Keypad Solver[/bold cyan]", style="cyan")

    # Capture screen
    im = ImageGrab.grab(bbox)
    im = im.resize((1920,1080)).crop(tofind)

    # Process image (HSV for cyan detection)
    hsv = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV)
    lower = np.array([50, 50, 50])
    upper = np.array([96, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    mintimg = cv2.bitwise_and(np.array(im), np.array(im), mask=mask)
    grayImage = cv2.cvtColor(mintimg, cv2.COLOR_RGB2GRAY)
    (thresh, blackAndWhiteImage) = cv2.threshold(grayImage, 100, 255, cv2.THRESH_BINARY)

    try:
        # Detect all 6 numbers
        numbers = []
        for a in range(0, 6):
            numbers.append(dot_check(a, blackAndWhiteImage))
        
        console.print(f"[green]✓[/green] Detected numbers: [bold cyan]{numbers}[/bold cyan]", style="green")
        
        # Wait for ready and execute
        check_ready(bbox)
        moves = calculate_key_sequence(numbers)
        move_keys = [k.upper() if k != 'return' else k for k in moves]
        console.print(f"[yellow]→[/yellow] Solution: [bold cyan]{' → '.join(move_keys)}[/bold cyan]", style="yellow")
        
        # Execute keystrokes
        for key in moves:
            keyboard.press_and_release(key)
            if key in ['s', 'w']:
                time.sleep(0.025)
            if key == 'return':
                time.sleep(1.95)
        
        console.print("[green]✓[/green] Casino Keypad solved successfully", style="green")
        console.print()
        
    except KeyError as e:
        console.print(f"[red]✗[/red] Cyan pattern not detected. {e} - current resolution {bbox[2]}x{bbox[3]}", style="red")
        console.print()
    
