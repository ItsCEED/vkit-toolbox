import cv2
import time
import keyboard
import numpy as np
from PIL import ImageGrab

DIGITS_LOOKUP = {
    (1, 1, 1, 0, 1, 1, 1): 0,
    (0, 0, 1, 0, 0, 1, 0): 1,
    (1, 0, 1, 1, 1, 0, 1): 2,
    (1, 0, 1, 1, 0, 1, 1): 3,
    (0, 1, 1, 1, 0, 1, 0): 4,
    (1, 1, 0, 1, 0, 1, 1): 5,
    (1, 1, 0, 1, 1, 1, 1): 6,
    (1, 0, 1, 0, 0, 1, 0): 7,
    (1, 1, 1, 1, 1, 1, 1): 8,
    (1, 1, 1, 1, 0, 1, 1): 9
}

RIGHT_SYMBOLS = {
    (0, 1): 10,
    (1, 0): 2,
    (0, 0): 1
}

moves = {
    (0, 0, 1, 1, 2, 2): ['enter', 'return', 'enter', 'return', 'enter', 'return'], # (1-1) + (2-2) + (3-3)
    (0, 0, 1, 2, 2, 1): ['enter', 'return', 'enter', 's', 'return', 'enter', 'return'], # (1-1) + (2-3) + (3-2)
    (0, 1, 1, 0, 2, 2): ['enter', 's', 'return', 'enter', 'w', 'return', 'enter', 'return'], #(1-2) + (2-1) + (3-3)
    (0, 1, 1, 2, 2, 0): ['enter', 's', 'return', 'enter', 'return', 'enter', 'return'], # (1-2) + (2-3) + (3-1)
    (0, 2, 1, 0, 2, 1): ['enter', 'w', 'return', 'enter', 'w', 'return', 'enter', 'return'], # (1-3) + (2-1) + (3-2)
    (0, 2, 1, 1, 2, 0): ['enter', 'w', 'return', 'enter', 'return', 'enter', 'return'] # (1-3) + (2-2) + (3-1) 
}

# target numbers
target_number_height = [123, 137, 137, 154, 173, 173, 195] # target numbers have same height
target_number_length_0 = [865, 849, 881, 865, 849, 881, 865] # first number
target_number_length_1 = [955, 939, 971, 955, 939, 971, 955] # second number
target_number_length_2 = [1043, 1029, 1061, 1043, 1029, 1061, 1043] # third number

# left numbers
left_number_length = [509, 495, 527, 509, 495, 527, 509] # left nubmers have same length
left_number_height_0 = [271, 287, 287, 303, 323, 323, 343] # first number
left_number_height_1 = [507, 522, 522, 540, 557, 557, 579] # second number
left_number_height_2 = [741, 755, 755, 773, 791, 791, 813] # third number

# right symbols
right_symbol_length = [1351, 1349] # right symbols have same length
right_symbol_height_0 = [305, 277] # first symbol
right_symbol_height_1 = [541, 513] # second symbol
right_symbol_height_2 = [775, 747] # third symbol

def pixel_check(x, y, img, dictionary):
    hints = []

    for i in range(0, len(list(dictionary)[0])):
        pixel = img[y[i]:y[i] + 1, x[i]:x[i] + 1]

        if np.mean(pixel):
            hints.append(1)
        else:
            hints.append(0)
            
    return dictionary[tuple(hints)]

def calculate(target_number, left_numbers, right_numbers):
    try:
        for i in range(0, 6):
            keys = []
            keys.append(list(tuple(moves)[i]))

            for z, x, v, n, k, l in keys:
                if (target_number == left_numbers[z] * right_numbers[x] + left_numbers[v] * right_numbers[n] + left_numbers[k] * right_numbers[l]):
                    print('-', moves[tuple(moves)[i]])
                    for key in (moves[tuple(moves)[i]]):
                        keyboard.press_and_release(key)
                        if key == 's' or 'w' or 'enter':
                            time.sleep(0.025)
                        if key == 'return':
                            time.sleep(1.3)
                    raise NotImplementedError
    except:
        print('[*] END')

def main(bbox):
    print('[*] Cayo Voltage Hack')

    im = ImageGrab.grab(bbox)
    im = im.resize((1920,1080))

    grayImage = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
    (thresh, blackAndWhiteImage) = cv2.threshold(grayImage, 100, 255, cv2.THRESH_BINARY)
    
    try:
        target_number = (
            (100 * (pixel_check(target_number_length_0, target_number_height, blackAndWhiteImage, DIGITS_LOOKUP)))
        + (10 * (pixel_check(target_number_length_1, target_number_height, blackAndWhiteImage, DIGITS_LOOKUP)))
        + pixel_check(target_number_length_2, target_number_height, blackAndWhiteImage, DIGITS_LOOKUP)
        )
        left_numbers = [
            pixel_check(left_number_length, left_number_height_0, blackAndWhiteImage, DIGITS_LOOKUP),
            pixel_check(left_number_length, left_number_height_1, blackAndWhiteImage, DIGITS_LOOKUP),
            pixel_check(left_number_length, left_number_height_2, blackAndWhiteImage, DIGITS_LOOKUP)
        ]
        right_numbers = [
            pixel_check(right_symbol_length, right_symbol_height_0, blackAndWhiteImage, RIGHT_SYMBOLS),
            pixel_check(right_symbol_length, right_symbol_height_1, blackAndWhiteImage, RIGHT_SYMBOLS),
            pixel_check(right_symbol_length, right_symbol_height_2, blackAndWhiteImage, RIGHT_SYMBOLS)
        ]

        print('- ', target_number, left_numbers, right_numbers)
        calculate(target_number, left_numbers, right_numbers)
    except KeyError as e:
        print(f'[!] Target number not detected. {e} - current resolution {bbox[2]}x{bbox[3]}')
        print('=============================================')