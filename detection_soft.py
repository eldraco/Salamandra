#! /usr/bin/env python
# Tool to read a rtl_power csv file and detect the presence of micropones transmitting
# Author: Sebastian Garcia eldraco@gmail.com

# Detection technique
# 1- Detect a peak in the transmiting frequencies. Power over a threshold.

import argparse
import sys
import operator

version = 0.0001

def process_line(line):
        line = line.split(',')
        time = line[0]
        hour = line[1]
        minfreq = line[2]
        maxfreq = line[3]
        step = line[4]
        samples = line[5]
        if args.verbose:
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
        if args.verbose:
            print '\tMax value in this line: {}, at freq {}'.format(detection_value, detection_freq)
        # Were there any other detections?
        sorted_detection_dict = sorted(detection_dict, key=detection_dict.get, reverse=True)
        # When there is a detection?
        # 1 When at least 1 frequency is over the threshold
        if detection_value >= dbm_threshold:
            print '\t\tDetection in freq: {} with Dbm {}. Time: {}'.format(detection_freq, max_value, time+' '+hour)
        # 2 When more than threshold freqencies are over the threshold
        print detection_dict
        if len(detection_dict) >= args.detfreqthreshold:
            print '\t\tDetection because {} freq were over the threshold: {}. Time: {}'.format(len(detection_dict), dbm_threshold, time+' '+hour)

def process_file():
    if args.verbose > 0:
        print 'Opening file {}'.format(args.file)
    try:
        f = open(args.file)
    except IOError:
        print 'No such file.'
        sys.exit(-1)
    for line in f:
        process_line(line)
    f.close()

def process_stdin():
    for line in sys.stdin:
        process_line(line)



####################
# Main
####################

# Parse the parameters
parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file', help='CSV file from rtl_power.', action='store', required=True)
parser.add_argument('-t', '--threshold', help='DBm threshold.', action='store', required=True, type=float)
parser.add_argument('-v', '--verbose', help='Verbose level.', action='store', required=False, type=int, default=0)
parser.add_argument('-F', '--detfreqthreshold', help='Threshold of the amount of frequencies that should be over the dbm threshold to have a detection.', action='store', required=False, type=int, default=1)
args = parser.parse_args()
if args.verbose > 0:
    print 'Detector. Version {}\n'.format(version)
    print 'Dbm Threshold: {}'.format(args.threshold)


if args.file == '-':
    process_stdin()
elif args.file != '-':
    process_file()



# Rtl_power produces a compact CSV file with minimal redundancy. The columns are:
# Timestamps are ISO-8601
# date, time, Hz low, Hz high, Hz step, samples, dB, dB, dB, ...
# Date and time apply across the entire row. The exact frequency of a dB value can be found by (hz_low + N * hz_step). The samples column indicated how many points went into each average.
