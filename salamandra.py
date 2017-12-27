#! /usr/bin/env python
#
# Salamandra
# Free-software SDR-based Tool that reads the output of rtl_power to detect and locate the presence of micropones transmitting
# Author: Sebastian Garcia eldraco@gmail.com, sebastian.garcia@agents.fel.cvut.cz

# Detection techniques
# 1- Detect a peak in the transmiting frequencies. Power over a threshold.

import argparse
import sys
import os
from datetime import datetime
from subprocess import Popen
from subprocess import PIPE
import curses
import curses.panel
import time
import select
import pygame.mixer


default_threshold = 10.8
version = '0.6alpha'

def process_line(line, ui, threshold, sound):
    """
    Process one line of input
    """
    ui.update_status('Reading')
    try:
        line = line.split(',')
        time = line[0]
        hour = line[1]
        minfreq = line[2]
        maxfreq = line[3]
        step = line[4]
        samples = line[5]
    except IndexError:
        return False
    if args.verbose > 2:
        print('Time: {} MinFreq: {}, Maxfreq:{}, step={}'.format(time + ' ' + hour, minfreq, maxfreq, step))
    # Analyze the dbm values
    dbm_threshold = threshold
    dbm_line = line[6:]
    max_value = float('-inf')
    max_pos = float('-inf')
    max_values_dict = {}
    index = 0
    detection_dict = {}
    while index < len(dbm_line):
        value = float(dbm_line[index])
        if value != float('-inf') and value > max_value:
            max_value = float(dbm_line[index])
            max_pos = index
        if value >= dbm_threshold:
            detection_dict[index] = value
        index += 1
    # Largest detection
    detection_freq = float(minfreq) + (float(step) * max_pos)
    detection_value = max_value
    if args.verbose > 2:
        print('\tMax value in this line: {}, at freq {}'.format(detection_value, detection_freq))
    # Were there any other detections?
    sorted_detection_dict = sorted(detection_dict, key=detection_dict.get, reverse=True)
    # When there is a detection?
    if not args.search:
        # 1 When at least 1 frequency is over the threshold
        #if detection_value >= dbm_threshold:
        #    line = '\t\tDetection in freq: {} with Dbm {}. Time: {}'.format(detection_freq, max_value, time + ' ' + hour)
        # 2 When more than threshold freqencies are over the threshold
        if len(detection_dict) >= args.detfreqthreshold:
            textline = '\t\tDetection because {} freq were over the threshold: {}. Time: {}'.format(len(detection_dict), dbm_threshold, time + ' ' + hour)
            ui.update_histogram(textline)
            if sound:
                pygame.mixer.music.play()
        else:
            if args.verbose > 1:
                textline = '\t\tNo detection'
                ui.update_histogram(textline)
    # This is the default mode of operation. The search with the histogram
    elif args.search:
        # Get the freqs in the detection
        freq_line = ''
        temp_uniq_dict = {}
        top_freq = ''
        for index in detection_dict:
            # In mhz
            detection_freq = (float(minfreq) + (float(step) * index)) / float(1000000)
            try:
                temp = temp_uniq_dict[detection_freq]
                temp_uniq_dict[detection_freq] += 1
            except KeyError:
                temp_uniq_dict[detection_freq] = 1
            detect_uniq_dict = sorted(temp_uniq_dict, key=temp_uniq_dict.get)
            top_freq = str(detect_uniq_dict[0])
        # Here we print the histogram
        line = '{:19} ({:>3}) [{:>6.6}]: {:160.160}'.format(str(datetime.now())[:-7], str(len(detection_dict)), top_freq, "#" * len(detection_dict))
        # Print the lines
        if args.verbose == 0 and len(detection_dict) > 0:
            ui.update_histogram(line)
            ui.update_status('DETECTION')
            if sound:
                pygame.mixer.music.play()
        elif args.verbose == 1 and len(detection_dict) > 0:
            ui.update_histogram(line)
            #print('\t[' + freq_line + ']')
            if sound:
                pygame.mixer.music.play()
        elif args.verbose > 1:
            # Print even if there is no detection
            ui.update_histogram(line)
            # Print even if there is no detection, plus freqs
            #if freq_line:
            #    print('\t[' + freq_line + ']')
            if len(detection_dict) > 0 and sound:
                pygame.mixer.music.play()


def process_file():
    """
    Reades a CSV file created by rtl_power and analysis it offline
    """
    if args.verbose > 0:
        print('Opening file {}'.format(args.file))
    try:
        f = open(args.file)
        return f
    except IOError:
        print('No such file.')
        sys.exit(-1)


def process_stdin():
    """
    Executes the rtl_power tool and gets the CSV formatted data
    """
    read_lines = 0
    # It will run by default for 24hs
    command = 'rtl_power -f ' + str(args.startfreq) + 'M:' + str(args.endfreq) + 'M:' + str(args.stepfreq) + 'Khz -g 25 -i 1 -e 86400 -'
    FNULL = open(os.devnull, 'w')
    p = Popen(command, shell=True, stdout=PIPE, bufsize=1, stderr=FNULL)
    return p.stdout


class ui:
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)
        self.curr_height, self.curr_width = self.stdscr.getmaxyx()
        self.stdscr.keypad(1)
        self.hist_lines = []
        self.w1height = self.curr_height - 5
        self.w1width = self.curr_width

        # curses.newwin(DOWN RIGHT CORNER y from top, DOWN RIGHT CORNER x from left , TOP LEFT CORNER y from top , TOP LEFT CORNER x from left)
        # 0 means the size of the current window
        self.win1 = curses.newwin(self.w1height, self.w1width, 0, 0)
        self.win1.border(0)
        self.pan1 = curses.panel.new_panel(self.win1)
        self.win2 = curses.newwin(0, 0, self.w1height, 0)
        self.win2.border(0)
        self.pan3 = curses.panel.new_panel(self.win2)
        self.win1.addstr(1, 1, "Location Signal (the more, the closer)", curses.color_pair(4))
        self.win1.addstr(2, 1, "DateTime (Amount of peaks) [Top Freq Detected MHz] Histogram", curses.color_pair(4))
        self.update_status('Detecting...')
        self.win2.addstr(2, 1, "Press 's' to increase the threshold (less sensitivity), 'S' to decresase the threshold (more sensitivity).", curses.color_pair(4))
        self.win2.addstr(3, 1, "Press 'm' to toggle sound, or 'q' to quit.", curses.color_pair(4))
        self.update_sound(args.sound)
        self.pan1.hide()
        self.refresh()

    def refresh(self):
        curses.panel.update_panels()
        self.win1.refresh()
        self.win2.refresh()

    def refresh_threshold(self, threshold):
        self.win2.addstr(1, 25, "Threshold: {}".format(threshold), curses.color_pair(2))
        self.refresh()

    def update_sound(self, sound):
        line = '{:5}'.format(str(sound))
        self.win2.addstr(1, 45, "Sound: {}".format(line), curses.color_pair(2))
        self.refresh()

    def update_freq(self, freq1, freq2):
        self.win2.addstr(1, 60, "Min Freq: {}. Max Freq: {}".format(freq1, freq2), curses.color_pair(2))
        self.refresh()

    def update_status(self, text):
        status = '{:15.15}'.format(text)
        self.win2.addstr(1, 1, "Status: {}".format(status), curses.color_pair(2))
        self.refresh()

    def update_hour(self):
        self.win2.addstr(3, self.w1width - 45, 'Current Time: ' + str(datetime.now()), curses.color_pair(9))
        self.refresh()

    def update_histogram(self, text):
        """
        Put one more line in the histogram
        """
        self.hist_lines.append(text)
        # Redraw the complete histogram, from bottom up
        for lpos in range(self.w1height - 2, 2, -1):
            try:
                # -1 is to start from the last line
                # - so we go down the list
                # height of the window - 
                self.win1.addstr(lpos, 1, str(self.hist_lines[-1 - (self.w1height - 2 - lpos)])[:self.w1width - 2], curses.color_pair(7))
            except IndexError:
                pass
            self.refresh()

    def quit_ui(self):
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()
        print("UI quitted")
        exit(0)


class runner:
    """
    Class to read the input and manage the input lines
    """
    def __init__(self, rfile):
        self.running = False
        self.rfile = rfile
        self.ui = ui()
        self.threshold = args.threshold
        self.sound = args.sound
        self.ui.refresh_threshold(self.threshold)

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            self.ui.update_status('Detecting...')
            self.ui.update_hour()
            self.ui.update_freq(int(args.startfreq), int(args.endfreq))
            line = rfile.readline()
            resp = process_line(line, self.ui, self.threshold, self.sound)
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if char.strip() == "q":
                    self.stop()
                    self.ui.quit_ui()
                    break
                elif char.strip() == "s":
                    self.threshold += 1
                    self.ui.refresh_threshold(self.threshold)
                elif char.strip() == "S":
                    self.threshold -= 1
                    self.ui.refresh_threshold(self.threshold)
                elif char.strip() == "m" and self.sound:
                    self.sound = False
                    self.ui.update_sound(self.sound)
                elif char.strip() == "m" and not self.sound:
                    self.sound = True
                    self.ui.update_sound(self.sound)
            self.ui.refresh()



####################
# Main
####################
if __name__ == "__main__":
    # Parse the parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='CSV file from rtl_power.', action='store', required=False)
    parser.add_argument('-t', '--threshold', help='DBm threshold. First threshold in our paper.', action='store', required=False, type=float, default=default_threshold)
    parser.add_argument('-v', '--verbose', help='Verbose level.', action='store', required=False, type=int, default=0)
    parser.add_argument('-F', '--detfreqthreshold', help='Second threshold in our paper. It is the threshold of the amount of frequencies that should be over the dbm threshold to have a detection.', action='store', required=False, type=int, default=1)
    parser.add_argument('-s', '--search', help='Search mode. Prints the amount of frequencies found to be over the specified threshold of -t. The more, the closer. In this mode, the -F threshold is not used.', action='store_true', required=False, default=True)
    parser.add_argument('-S', '--sound', help='Play a sound when there is some detection in this time frame.', action='store_true', required=False, default=True)
    parser.add_argument('-a', '--startfreq', help='Start frequency for rtl_power. Defaults to 50 MHz', action='store', type=int, required=False, default=100)
    parser.add_argument('-b', '--endfreq', help='End frequency for rtl_power. Defaults to 1760 MHz (USB device)', action='store', type=int, required=False, default=400)
    parser.add_argument('-c', '--stepfreq', help='Step frequency for rtl_power. Defaults to 4000 MHz', action='store', type=int, required=False, default=4000)
    args = parser.parse_args()

    if args.verbose > 0:
        print('Salamandra Hidden Microphone Detector. Version {}\n'.format(version))

    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=8196)
    if args.sound:
        pygame.mixer.music.load('start3.mp3')
        pygame.mixer.music.play()
    time.sleep(1)
    pygame.mixer.music.load('detection.mp3')

    try:
        if args.file:
            rfile = process_file()
        else:
            rfile = process_stdin()
        r = runner(rfile)
        r.run()
    except KeyboardInterrupt:
        print('Exiting.')
