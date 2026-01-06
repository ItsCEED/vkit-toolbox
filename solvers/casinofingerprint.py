import cv2
import time
import keyboard
import numpy as np
from PIL import ImageGrab
from collections import deque, namedtuple
from rich.console import Console


console = Console()


tofind = (950, 155, 1335, 685)


parts = [[(482, 279, 482 + 102, 279 + 102), (0, 0)],
[(627, 279, 627 + 102, 279 + 102), (1, 0)],
[(482, 423, 482 + 102, 423 + 102), (0, 1)],
[(627, 423, 627 + 102, 423 + 102), (1, 1)],
[(482, 566, 482 + 102, 566 + 102), (0, 2)],
[(627, 566, 627 + 102, 566 + 102), (1, 2)],
[(482, 711, 482 + 102, 711 + 102), (0, 3)],
[(627, 711, 627 + 102, 711 + 102), (1, 3)]]


def is_in(img, subimg):
    """return if 'subimg' is in 'img'"""
    subimg1 = cv2.cvtColor(np.array(subimg), cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(img, subimg1, cv2.TM_CCOEFF_NORMED)
    threshold = 0.65  # error coef
    loc = np.where(res >= threshold)
    for pt in zip(*loc[::-1]):
        return True
    return False


def find_shortest_solution(target_coordinates):
    Point = namedtuple('Point', ('x', 'y'))
    ReverseLinkedNode = namedtuple("ReverseLinkedNode", ('value', 'prev_node', 'idx'))
    rows, cols = 4, 2
    directions = [(0, 1, 's'), (1, 0, 'd'), (0, -1, 'w'), (-1, 0, 'a')]  # (delta_x, delta_y, key)

    target_coordinates = [p if isinstance(p, Point) else Point(*p) for p in target_coordinates]
    target_mask = 0
    for target in target_coordinates:
        target_mask |= 1 << ((target.y * cols) + target.x)

    # BFS initialization
    current_pos = Point(0, 0)
    visited_mask = 1
    path_head: ReverseLinkedNode = ReverseLinkedNode(None, None, -1)
    if current_pos in target_coordinates:
        path_head = ReverseLinkedNode('return', path_head, 0)
    queue = deque([(current_pos, visited_mask, path_head)])  # (current_position, visited_mask, path_head)

    # loop until all points have been visited or a solution has been found
    while len(queue) > 0:
        current_pos, visited_mask, path_head = queue.popleft()

        # if all target points are visited, return the final path
        if visited_mask & target_mask == target_mask:
            output_list = [None] * (path_head.idx + 1)
            while path_head.idx >= 0:
                output_list[path_head.idx] = path_head.value
                path_head = path_head.prev_node
            return output_list + ['tab']

        # explore neighbors
        for delta_x, delta_y, key in directions:
            new_x, new_y = current_pos.x + delta_x, current_pos.y + delta_y
            # correct for wrapping
            if new_x == -1:
                new_x, new_y = cols-1, new_y-1
            elif new_x == cols:
                new_x, new_y = 0, new_y+1
            new_y = new_y % rows

            next_pos = Point(new_x, new_y)
            pos_mask = 1 << ((next_pos.y * cols) + next_pos.x)
            next_visited_mask = visited_mask | pos_mask
            # skip if visited
            if visited_mask == next_visited_mask:
                continue

            next_path_head = ReverseLinkedNode(key, path_head, path_head.idx+1)
            # if next_pos is a target point
            if target_mask & pos_mask != 0:
                next_path_head = ReverseLinkedNode('return', next_path_head, next_path_head.idx+1)
            queue.append((next_pos, next_visited_mask, next_path_head))

    raise Exception('No solution found')


def main(bbox):
    console.print("🔍 [bold cyan]Casino Fingerprint Solver[/bold cyan]", style="cyan")
    
    # Capture and process screen
    im = ImageGrab.grab(bbox)
    im = im.resize((1920, 1080))
    sub0_ = im.crop(tofind)
    sub0 = cv2.cvtColor(
        np.array(sub0_.resize((round(sub0_.size[0] * 0.77), round(sub0_.size[1] * 0.77)))), 
        cv2.COLOR_BGR2GRAY
    )

    # Find matching fingerprint locations
    togo = [part[1] for part in parts if is_in(sub0, im.crop(part[0]))]
    
    # Cleanup
    sub0_.close()
    im.close()

    if not togo:
        console.print("[red]✗[/red] No fingerprint matches found", style="red")
        return

    # Calculate optimal path
    console.print(f"[green]✓[/green] Found [bold]{len(togo)}[/bold] fingerprint matches", style="green")
    moves = find_shortest_solution(togo)
    
    # Display solution
    move_keys = [k.upper() if k != 'return' and k != 'tab' else k for k in moves]
    console.print(f"[yellow]→[/yellow] Solution: [bold cyan]{' → '.join(move_keys)}[/bold cyan]", style="yellow")
    
    # Execute keystrokes
    for key in moves:
        keyboard.press_and_release(key)
        time.sleep(0.025)
    
    console.print("[green]✓[/green] Casino Fingerprint solved successfully", style="green")
    console.print()
