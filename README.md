# Salamandra Spy Microphone Detection Tool

Salamandra is a tool to detect and __locate__ spy microphones in closed environments. It find microphones based on the strength of the signal sent by the microphone and the amount of noise and overlapped frequencies. Based on the generated noise it can estimate how close or far away you are from the microphone.


# Installation

## USB SDR Device
To use Salamandra you nee to have a SDR (Software Define Radio) device. It can be any from the cheap USB devices, such as [this](http://www.dx.com/p/rtl2832u-r820t-mini-dvb-t-dab-fm-usb-digital-tv-dongle-black-170541).

## rtl_power software

Salamandra needs the rtl_power software installed in your computer. To install it you can do:

### On MacOS

Using [macports](https://www.macports.org/install.php):

```
sudo port install rtl-sdr
pip install pygame
```

Using [homebrew](https://brew.sh/):

```
brew install smpeg
brew install sdl_mixer --with-smpeg
brew install sdl
pip install pygame
```

### On Linux

```
apt-get install rtl-sdr
pip install pygame
```

### On Windows

See http://www.rtl-sdr.com/getting-the-rtl-sdr-to-work-on-windows-10/

If rtl_power was installed correctly, you should be able to run this command in any console:

```
rtl_test
```

And you should see one device detected.

# Usage

## Basic usage for detecting microphones

```
./salamandra.py
```

This command will use a default threshold of 10.8, a min freq of 100Mhz, a max freq of 400Mhz and sound. You can change the default values with parameters.

## Location Mode to find Hidden Microphones

Run Salamandra with a threshold of 0, starting in the frequency 100MHz and ending in the frequency 200MHz. Search is activated with (`-s`). And make sounds (`-S`)

```
./salamandra.py -t 0 -a 100 -b 200 -s -S
```

## Location Mode from a stored rtl_power file

```
./salamandra.py -t 0 -a 111 -b 113 -s -f stored.csv
```

To actually create the file with rtl_power, from 111MHz to 114MHz, with 4000Khz step, gain of 25, integration of 1s and capturing for 5min, you can do:

```
rtl_power -f 111M:114M:4000Khz -g 25 -i 1 -e 300 stored.csv
```

## Detection Mode (deprecated now). To detect microphones in one pass.

Run Salamandra with a threshold (`-t`) of 10.3 and a second threshold (`-F`) of 2, starting in the frequency 100MHz and ending in the frequency 200MHz.

```
./salamandra.py -t 10.3 -a 100 -b 200 -F 2
```


## Tips

- The wider the range of frequencies selected, the longer the analysis takes.
- The wider the range, the more probabilities to find microphones.
- Once you know the prob freq you can narrow it down with the parameters.


# TODO
1. Make more clear if there is a detection or not
2. Separate the FP by
    - Sound generation based on the length of the histogram
    - Discard the frequencies that do not look like analog audio (Equidistant freqs)
3. Logs in file
4. Make the execution of rtl_power in another process in the background
