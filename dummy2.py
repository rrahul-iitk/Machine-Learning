import subprocess
import os
import numpy
import sys
from PIL import Image
import easyocr
import string
import random

def write_on_line(text):
    sys.stdout.write(f'\r{text}' + ' ' * 40)
    sys.stdout.flush()


def crop_from_path(image_path, coords, saved_location):
    image_obj = Image.open(image_path)
    # print(image_obj.size)
    x0, y0, w, h = coords

    cropped_image = image_obj.crop([x0, y0, x0 + w, y0 + h])
    cropped_image.save(saved_location)
    # cropped_image.show()


def lcs(X, Y, m, n):
    L = [[0 for x in range(n + 1)] for x in range(m + 1)]

    # Following steps build L[m+1][n+1] in bottom up fashion. Note
    # that L[i][j] contains length of LCS of X[0..i-1] and Y[0..j-1] 
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0 or j == 0:
                L[i][j] = 0
            elif X[i - 1] == Y[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])

    # Following code is used to print LCS
    index = L[m][n]

    # Create a character array to store the lcs string
    lcs = [""] * (index + 1)
    lcs[index] = ""

    # Start from the right-most-bottom-most corner and
    # one by one store characters in lcs[]
    i = m
    j = n
    while i > 0 and j > 0:

        # If current character in X[] and Y are same, then
        # current character is part of LCS
        if X[i - 1] == Y[j - 1]:
            lcs[index - 1] = X[i - 1]
            i -= 1
            j -= 1
            index -= 1

        # If not same, then find the larger of two and
        # go in the direction of larger value
        elif L[i - 1][j] > L[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return "".join(lcs)


def area_concatenate(a, b):
    atext = a['text']
    btext = b['text']
    ascore = a['score']
    bscore = b['score']
    abox = a['box']
    bbox = b['box']
    #############################

    ax0 = abox[0]
    ay0 = abox[1]
    aw = abox[2]
    ah = abox[3]
    ax1, ay1 = ax0 + aw, ay0
    ax2, ay2 = ax0 + aw, ay0 + ah
    ax3, ay3 = ax0, ay0 + ah
    #     print(ax0, ay0)
    #     print(ax1, ay1)
    #     print(ax2, ay2)
    #     print(ax3, ay3)
    # ############################

    bx0 = bbox[0]
    by0 = bbox[1]
    bw = bbox[2]
    bh = bbox[3]
    bx1, by1 = bx0 + bw, by0
    bx2, by2 = bx0 + bw, by0 + bh
    bx3, by3 = bx0, by0 + bh
    #     print('--------')
    #     print(bx0, by0)
    #     print(bx1, by1)
    #     print(bx2, by2)
    #     print(bx3, by3)
    #     print('-------')
    # ##########################
    x0 = max(ax0, bx0)
    x1 = min(ax1, bx1)
    y0 = max(ay0, by0)
    y1 = min(ay2, by2)
    if x0 > x1 or y0 > y1:
        return 0

    return (x1 - x0) * (y1 - y0)


def text_ocr_ensemble(path_to_image, cell_coords, lang):
    """
    Args:
        path_to_image: path to the original table
        cell_coords:  the coordinates of the cell box [left, top, width, height]
        lang:  language code from the list ['chi_sim', 'eng','rus', 'spa','deu','ara']
    Returns: text, the text that is present in the cell
    """
    # coords adapter from xmin, ymin, xmax, ymax  ==> to  ==> left, top, width, height
    left, top = cell_coords[0], cell_coords[1]
    width, height = cell_coords[2] - cell_coords[0], cell_coords[3] - cell_coords[1]

    cell_coords = [left, top, width, height]

    tesseract_result = tesseract_recognize(path_to_image, cell_coords, lang)
    easyocr_result = easyocr_recognize(path_to_image, cell_coords, lang)
    a_char_score = [1]
    a_char = ['#']
    for a in tesseract_result:
        for c in a['text']:
            a_char_score.append(a['score'])
            a_char.append(c)
        a_char_score.append(a['score'])
        a_char.append(' ')
    a_char_score.append(1)
    a_char.append('#')

    b_char_score = [1]
    b_char = ['#']
    for a in easyocr_result:
        for c in a['text']:
            b_char_score.append(a['score'])
            b_char.append(c)
        b_char_score.append(a['score'])
        b_char.append(' ')

    b_char_score.append(1)
    b_char.append('#')

    Atext = list(a_char)
    Btext = list(b_char)

    lcs_ = lcs(Atext, Btext, len(Atext), len(Btext))
    a_indices, b_indices = [], []
    a_cnt, b_cnt = 0, 0
    for i, c in enumerate(lcs_):
        while Atext[a_cnt] != c:
            a_cnt += 1
        a_indices.append(a_cnt)
        while Btext[b_cnt] != c:
            b_cnt += 1
        b_indices.append(b_cnt)
    text = ''
    score = 0

    for i in range(len(lcs_) - 1):
        aleft, aright = a_indices[i], a_indices[i + 1]
        bleft, bright = b_indices[i], b_indices[i + 1]
        aproba = sum(a_char_score[aleft:aright + 1]) / (aright - aleft + 1)
        bproba = sum(b_char_score[bleft:bright + 1]) / (bright - bleft + 1)

        text += lcs_[i]
        score += max(a_char_score[i], b_char_score[i])
        if aproba > bproba:
            text += ''.join(Atext[aleft + 1:aright])
            score += sum(a_char_score[aleft + 1:aright])
        else:
            text += ''.join(Btext[bleft + 1:bright])
            score += sum(b_char_score[bleft + 1:bright])

    return {'text': text[1:], 'score': score / len(text)}


if __name__ == 'main':
    print(text_ocr_ensemble(f'table_images/table_117-17-de.jpg', [1416, 0, 62, 55], 'deu'))