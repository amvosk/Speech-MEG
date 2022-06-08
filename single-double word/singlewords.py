# -*- coding: utf-8 -*-
"""
Created on Thu Feb 10 12:36:33 2022

@author: AlexVosk
"""
import os
import sys
import time
import re
import copy
import random

import codecs
import numpy as np

from PIL import ImageFont, ImageDraw, Image
import PIL.ImageQt as ImageQt
import PyQt5
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtCore import QTimer

# from psychopy import parallel

# import rusyllab
# from russian_g2p.Accentor import Accentor
# from russian_g2p.Grapheme2Phoneme import Grapheme2Phoneme

from queue import Queue





parrallel_port_idle = True

if parrallel_port_idle:
    WINDOW_X = 1920
    WINDOW_Y = 1080 
else:
    WINDOW_X = 1280
    WINDOW_Y = 1024
    
back_ground_color = (0,0,0)
font_size = 64
font_color = (255,255,255)
unicode_font = ImageFont.truetype("DejaVuSans.ttf", font_size)
X, Y = 240, 70
# epoch_time = 1500
update_time = 500

green = (0, 153, 76)
orange = (204, 102, 0)

course = ['rest', 'rest', 'rest', 'rest', 'rest',
          'focus', 'focus', 
          'stimulus', 
          'blank', 'blank', 'blank', 
          'line', 'line', 'line', 
          'blank']

ntypes = 2
nblocks = 1
c = 255


def pil2pixmap(im):
    if im.mode == "RGB":
        r, g, b = im.split()
        im = Image.merge("RGB", (b, g, r))
    elif  im.mode == "RGBA":
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (b, g, r, a))
    elif im.mode == "L":
        im = im.convert("RGBA")
    # Bild in RGBA konvertieren, falls nicht bereits passiert
    im2 = im.convert("RGBA")
    data = im2.tobytes("raw", "RGBA")
    qim = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)
    pixmap = QPixmap.fromImage(qim)
    return pixmap


class Word:
    def __init__(self, word, nwords):
        self.unicode_font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        self.x_size, self.y_size = self.unicode_font.getsize(word)

        self.position_text = (WINDOW_X - self.x_size)/2, (WINDOW_Y - self.y_size)/2
        self.word = word
        self.nwords = nwords
        self.index = word2index[word]

    def get_image(self, speech_type):
        return self.images[speech_type]
    
    def get_image_frame(self, speech_type):
        return self.images_frame[speech_type]
    
    
    def get_index(self, speech_type):
        return self.index + self.nwords*speech_type

    def update_position(self, y_size_max):
        self.y_size_max = y_size_max
        self.position_text = (WINDOW_X - self.x_size)/2, (WINDOW_Y - y_size_max)/2
        self.images = [self._make_image(color=green), self._make_image(color=orange)]
        self.images_frame = [self._make_image_frame(color=green), self._make_image_frame(color=orange)]
        
    def _make_image(self, color=None):
        picture = Image.new ( "RGB", (WINDOW_X, WINDOW_Y), back_ground_color)
        draw = ImageDraw.Draw(picture)
        draw.text(self.position_text, self.word, font=unicode_font, fill=color if color is not None else font_color)
        pixmap = pil2pixmap(picture)
        return pixmap
    
    def _make_image_frame(self, color=None):
        picture = Image.new ( "RGB", (WINDOW_X, WINDOW_Y), back_ground_color)
        draw = ImageDraw.Draw(picture)
        position_corner1 = (WINDOW_X - self.x_size)/2, (WINDOW_Y - self.y_size_max)/2
        position_corner2 = (WINDOW_X + self.x_size)/2, (WINDOW_Y + self.y_size_max)/2
        draw.rectangle((position_corner1, position_corner2), fill=back_ground_color, outline=color if color is not None else font_color)
        pixmap = pil2pixmap(picture)
        return pixmap
    

        
def make_black_image(text=None, color=None, y_max=None):
    picture = Image.new ( "RGB", (WINDOW_X, WINDOW_Y), back_ground_color)
    if text is not None:
        draw = ImageDraw.Draw(picture)
        unicode_font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        x_size, y_size = unicode_font.getsize(text)
        #print(y_size, y_max)
        y_size = y_max if y_max is not None else y_size
        position_text = (WINDOW_X - x_size)/2, (WINDOW_Y - y_size)/2
        draw.text(position_text, text, font=unicode_font, fill=color if color is not None else font_color)
    pixmap = pil2pixmap(picture)
    return pixmap
    
        

        



def make_order_block(nwords, seed=None):
    def check_order(order):
        index_last = -1
        for index, _ in order:
            if index == index_last:
                return False
            else:
                index_last = index
        return True
    
    order_overt = []
    order_covert = []
    splits = [0] + [1]*2 + [2]*3 + [3]*4
    
    for index in range(nwords):
        order_overt.append((index, 0))
        order_covert.append((index, 1))
        order_covert.append((index, 1))
        
    shuffled = False
    if seed is not None:
        random.seed(seed)
    while not shuffled:
        random.shuffle(order_overt)
        random.shuffle(order_covert)
        random.shuffle(splits)
        order = []
        count = 0
        for i, overt in enumerate(order_overt):
            order.append(overt)
            for _ in range(splits[i]):
                order.append(order_covert[count])
                count += 1
        shuffled = check_order(order)
    return order
            
def make_order(nwords, nblocks, seed=None):
    order = make_order_block(nwords, seed=seed)
    for block in range(1, nblocks):
        block_seed = seed + block if seed is not None else None
        order_block = make_order_block(nwords, seed=block_seed)
        index_last = order[-1][0]
        seed_counter = 100
        while order_block[0][0] == index_last:
            order_block = make_order_block(nwords, seed=(block_seed)*seed_counter if block_seed is not None else None)
            seed_counter += 1
        order += order_block
    return order
        


class ParallelPort():
    def __init__(self, idle=False, verbose=True):
        self.idle = idle
        self.verbose = verbose
        if self.idle:
            print('Idle parallel port created')
        else:
            try:
                from psychopy import parallel
                self.p_port = parallel.ParallelPort(address='0xE030')
            except:
                print('Something went wrong, parallel port wasn\'t created, started idle mode')
                self.idle = True                      

    def set_parallel_port(self, index):
        if self.idle and self.verbose:
            print('parralel port: idle {}'.format(int(index)))
        elif not self.idle:
            try:
                self.p_port.setData(int(index))
            except:
                print('Something went wrong, can\'t sent into the parallel port, started idle mode')
                self.idle = True                      
            if self.verbose:
                print('parralel port: real {}'.format(int(index)))
            

        
        

class App(QWidget):
    def __init__(self, vocabulary, word2index, ntypes, nblocks):
        super().__init__()
        self.title = 'PyQt5 Solution'
        self.left = 10
        self.top = 10

        self.nwords = len(vocabulary)
        self.ntypes = ntypes
        self.nblocks = nblocks
        self.ntotal = self.nwords * 3 * self.nblocks
        
        
        self.order = make_order(self.nwords, self.nblocks)
        print(len(self.order))
        print('expected time:', len(self.order)*len(course)*update_time / 1000 / 60)
        print(self.order)
        self.words = [Word(word, self.nwords) for word in vocabulary]
        y_max = np.max([word.y_size for word in self.words])
        for word in self.words:
            word.update_position(y_max)

        colors = [green, orange]
        self.image_black = make_black_image()
        self.image_focus = [make_black_image(text='+', color=color, y_max=y_max) for color in colors]
        self.image_line = [make_black_image(text='- - - - -', color=color, y_max=y_max) for color in colors]
        self.image_rest = [make_black_image(text='...', color=color, y_max=y_max) for color in colors]
        
        self.port = ParallelPort(idle=parrallel_port_idle, verbose=True)       
        self.port.set_parallel_port(0)

        
        self.current_index = -10
        self.cycle_index = 0
        
        
        self.width = WINDOW_X
        self.height = WINDOW_Y
        
        # self.recorder = Recorder(self.q)
        # self.recorder.start()
        # self.triggerbox = Triggerbox(verbose=False)
        # self.triggerbox.connect()
        #time.sleep(2)
        
        #self.q.put(('inlet_state', 1))
        #print(('inlet_state', 1))
        #time.sleep(7)
        
        self.initUI()

    def set_parallel_port(self, k):
        print(k)
        self.p_port.setData(int(k))


    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.label = QLabel(self)
        timer = QTimer(self)
        # self.update_image()

        timer.timeout.connect(self._update)
        timer.start(update_time)



    def _update(self):
        if self.current_index < 0 or self.current_index >= self.ntotal:
            pixmap, index = self.image_black, 0
            self.current_index += 1
        else:
            word_index, speech_type = self.order[self.current_index]
            word = self.words[word_index]

            word.get_image(speech_type)
            
            if course[self.cycle_index] == 'rest':
                pixmap, index = self.image_rest[speech_type], 0
            elif course[self.cycle_index] == 'focus':
                pixmap, index = self.image_focus[speech_type], 0
            elif course[self.cycle_index] == 'stimulus':
                pixmap, index = word.get_image(speech_type), 0
            elif course[self.cycle_index] == 'blank':
                pixmap, index = self.image_black, 0
            elif course[self.cycle_index] == 'line':
                pixmap, index = word.get_image_frame(speech_type), word.get_index(speech_type)

            self.cycle_index += 1
            if self.cycle_index % len(course) == 0:
                self.cycle_index = 0
                self.current_index += 1

        self.port.set_parallel_port(index)
        if not pixmap.isNull():
            self.label.setPixmap(pixmap)
            self.label.adjustSize()
            self.resize(pixmap.size())
            

    
def read_words():
    def read_file(filename):
        words = []
        with codecs.open(filename, 'r', encoding='utf-8') as file:
            for line in file.readlines():
                line = line.strip()
                if len(line) > 0:
                    words.append(line)
        return words
    word2index = {}
    vocabulary = read_file('nouns5.txt')
    vocabulary += read_file('verbs5.txt')
    for index, word in enumerate(vocabulary):
        word2index[word] = index + 1
    return vocabulary, word2index


if __name__ == '__main__':
    n = 1
    if '-test' in sys.argv:
        n = 10
    elif '-5min' in sys.argv:
        n = 20
    elif '-10min' in sys.argv:
        n = 60

    vocabulary, word2index = read_words()
    
    index2stimulus = {}
    for w, i in word2index.items():
        index2stimulus[i] = [w, 'overt']
        index2stimulus[i+10] = [w, 'covert']
        
    import json
    with open('index2stimulus.json', 'w', encoding='utf8') as f:
        json.dump(index2stimulus, f, ensure_ascii=False)
        
    

    q = Queue()
    app = QApplication(sys.argv)
    
    try:
        display_monitor = 1
        monitor = QDesktopWidget().screenGeometry(display_monitor)
    except:
        display_monitor = 0
        monitor = QDesktopWidget().screenGeometry(display_monitor)
        
    print('display_monitor:', display_monitor)

    ex = App(vocabulary, word2index, ntypes, nblocks)
    ex.move(monitor.left(), monitor.top())
    ex.showFullScreen()
    
    ex.show()
    sys.exit(app.exec_())


   