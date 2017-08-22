#! /usr/bin/env python
#
# Salamandra
# Free-software SDR-based Tool that reads the output of rtl_power to detect and locate the presence of micropones transmitting
# Author: Sebastian Garcia eldraco@gmail.com, sebastian.garcia@agents.fel.cvut.cz

# Detection techniques
# 1- Detect a peak in the transmiting frequencies. Power over a threshold.

import argparse
import sys
from datetime import datetime
from subprocess import Popen
from subprocess import STDOUT
from subprocess import PIPE
import curses, curses.panel
import time
import sys
import select
import random


default_threshold = 10.8
version = 0.5
proc_lines = 0

def process_line(line, ui):
    global proc_lines
    line = line.split(',')
    time = line[0]
    hour = line[1]
    minfreq = line[2]
    maxfreq = line[3]
    step = line[4]
    samples = line[5]
    if args.verbose > 2:
        print 'Time: {} MinFreq: {}, Maxfreq:{}, step={}'.format(time+' '+hour, minfreq, maxfreq, step)
    # Analyze the dbm values
    dbm_threshold = args.threshold
    dbm_line = line[6:]
    max_value= float('-inf')
    max_pos= float('-inf')
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
        print '\tMax value in this line: {}, at freq {}'.format(detection_value, detection_freq)
    # Were there any other detections?
    sorted_detection_dict = sorted(detection_dict, key=detection_dict.get, reverse=True)
    # When there is a detection?
    if not args.search:
        # 1 When at least 1 frequency is over the threshold
        if detection_value >= dbm_threshold:
            print '\t\tDetection in freq: {} with Dbm {}. Time: {}'.format(detection_freq, max_value, time+' '+hour)
        # 2 When more than threshold freqencies are over the threshold
        if len(detection_dict) >= args.detfreqthreshold:
            print '\t\tDetection because {} freq were over the threshold: {}. Time: {}'.format(len(detection_dict), dbm_threshold, time+' '+hour)
            if args.sound:
                pygame.mixer.music.play()

        else:
            if args.verbose > 1:
                print '\t\tNo detection'
    elif args.search:
        # Get the freqs in the detection
        freq_line = ''
        for index in detection_dict:
            # In mhz
            detection_freq = (float(minfreq) + (float(step) * index)) / float(1000000)
            freq_line += ' {:0.3f}({})'.format(detection_freq, detection_dict[index]) + ','
        freq_line = freq_line[:-1]
        line = str(datetime.now()) + ' [' + str(len(detection_dict)) + '] ' + ': '
        line += "#" * len(detection_dict) 
        # Print the lines
        if args.verbose == 0 and len(detection_dict) > 0:
            print line
            ui.update_histogram(line)
            if args.sound:
                pygame.mixer.music.play()
        elif args.verbose == 1 and len(detection_dict) > 0:
            print line
            ui.update_histogram(line)
            print '\t[' + freq_line + ']'
            if args.sound:
                pygame.mixer.music.play()
        elif args.verbose > 1:
            # Print even if there is no detection
            print line
            ui.update_histogram(line)
            # Print even if there is no detection, plus freqs
            if  freq_line:
                print '\t[' + freq_line + ']'
            if len(detection_dict) > 0 and args.sound:
                pygame.mixer.music.play()
        # Play sound
        proc_lines += 1

def process_file(ui):
    if args.verbose > 0:
        print 'Opening file {}'.format(args.file)
    try:
        f = open(args.file)
    except IOError:
        print 'No such file.'
        sys.exit(-1)
    for line in f:
        process_line(line, ui)
    f.close()

def process_stdin(ui):
    """
    """
    # Rtl_power produces a compact CSV file with minimal redundancy. The columns are:
    # Timestamps are ISO-8601
    # date, time, Hz low, Hz high, Hz step, samples, dB, dB, dB, ...
    # Date and time apply across the entire row. The exact frequency of a dB value can be found by (hz_low + N * hz_step). The samples column indicated how many points went into each average.

    read_lines = 0
    # Specific for a given frequency at 113Mhz
    #command = 'rtl_power -f 113M:114M:4000Khz -g 25 -i 1 -e 14400 -'
    # Range of normal FM transmitters
    #command = 'rtl_power -f 100M:900M:4000Khz -g 25 -i 1 -e 14400 -'
    # For Baby Monitor
    #command = 'rtl_power -f 600M:900M:4000Khz -g 25 -i 1 -e 14400 -'
    # Complete range of the DVB-T+DAB+FM
    command = 'rtl_power -f 50M:1760M:4000Khz -g 25 -i 1 -e 14400 -'
    #command = 'rtl_power -f 200M:1760M:4000Khz -g 25 -i 1 -e 14400 -'
    p = Popen(command, shell=True, stdout=PIPE, bufsize=1)
    line = p.stdout.readline()
    while line:
        process_line(line)
        read_lines += 1
        line = p.stdout.readline()
    if args.verbose:
        print 'Processed Lines: {}'.format(proc_lines)
        print 'Original Lines: {}'.format(read_lines)

class ui:
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.stdscr.keypad(1)

        # curses.newwin(DOWN RIGHT CORNER y from top, DOWN RIGHT CORNER x from left , TOP LEFT CORNER y from top , TOP LEFT CORNER x from left)
        # 0 means the size of the current window
        self.win1 = curses.newwin(31, 200, 0, 0)
        self.win1.border(0)
        self.pan1 = curses.panel.new_panel(self.win1)
        self.win2 = curses.newwin(0, 0, 31, 0)
        self.win2.border(0)
        self.pan3 = curses.panel.new_panel(self.win2)
        self.win1.addstr(1, 1, "Location Signal")
        self.win2.addstr(1, 1, "Status: Active.")
        self.win2.addstr(2, 1, "Press 's' to increase senstivity or 'q' to quit.")
        self.pan1.hide()

    def refresh(self):
        curses.panel.update_panels()
        self.win1.refresh()
        self.win2.refresh()

    def refresh_sensitivity(self, sensitivity):
        self.win2.addstr(1, 17, "Window Sensitivity: {}".format(sensitivity))
        self.refresh()

    def update_histogram(self, text):
        self.win1.addstr(2, 1, text)

    def quit_ui(self):
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()
        print "UI quitted"
        exit(0)


class runner:
    """
    Class to read the input and manage the input lines
    """
    def __init__(self):
        self.running = False
        self.ui = ui()
        self.sensitivity = args.threshold
        self.ui.refresh_sensitivity(self.sensitivity)

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        if args.file:
            process_file(self.ui)
        else:
            process_stdin(self.ui)
        
        self.loop()

    def loop(self):
        while self.running :
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.read(1)
                if line.strip() == "q":
                    self.stop()
                    self.ui.quit_ui()
                    break
                elif line.strip() == "s":
                    self.sensitivity += 1
                    self.ui.refresh_sensitivity(self.sensitivity)
                elif line.strip() == "S":
                    self.sensitivity -= 1
                    self.ui.refresh_sensitivity(self.sensitivity)
            self.ui.refresh()
            #time.sleep(0.1)

####################
# Main
####################
if __name__ == "__main__":
    # Parse the parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='CSV file from rtl_power.', action='store', required=False)
    parser.add_argument('-t', '--threshold', help='DBm threshold. First threshold in our paper.', action='store', required=True, type=float, default=default_threshold)
    parser.add_argument('-v', '--verbose', help='Verbose level.', action='store', required=False, type=int, default=0)
    parser.add_argument('-F', '--detfreqthreshold', help='Second threshold in our paper. It is the threshold of the amount of frequencies that should be over the dbm threshold to have a detection.', action='store', required=False, type=int, default=1)
    parser.add_argument('-s', '--search', help='Search mode. Prints the amount of frequencies found to be over the specified threshold of -t. The more, the closer. In this mode, the -F threshold is not used.', action='store_true', required=False)
    parser.add_argument('-S', '--sound', help='Play a sound when there is some detection in this time frame.', action='store_true', required=False)
    args = parser.parse_args()

    if args.verbose > 0:
        print 'Salamandra Hiden Microphone Detector. Version {}\n'.format(version)

    if args.sound:
        import pygame.mixer
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=8196)
        pygame.mixer.music.load('start3.mp3')
        pygame.mixer.music.play()
        time.sleep(1)
        pygame.mixer.music.load('detection.mp3')

    try:
        r = runner()
        r.run()
    except KeyboardInterrupt:
        print 'Exiting.'



