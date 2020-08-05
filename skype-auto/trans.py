#!/usr/bin/env python3
"""Load an audio file into memory and play its contents.

NumPy and the soundfile module (https://PySoundFile.readthedocs.io/)
must be installed for this to work.

This example program loads the whole file into memory before starting
playback.
To play very long files, you should use play_long_file.py instead.

"""
import argparse
import tempfile
import queue
import sys
import os
import sounddevice as sd
import soundfile as sf
import numpy  # Make sure NumPy is loaded before it is used in the callback
assert numpy  # avoid "imported but unused" message (W0611)


def record_wav():
    q = queue.Queue()
    filename = "output.wav"
    if os.path.exists(filename): os.remove(filename)
    samplerate = 48000
    channels = 1
    subtype = None
    device = None


    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())


    try:
        with sf.SoundFile(filename, mode='x', samplerate=samplerate,
                          channels=channels, subtype=subtype) as file:
            with sd.InputStream(samplerate=samplerate, device=device,
                                channels=channels, callback=callback):
                print('#' * 80)
                print('press Ctrl+C to stop the recording')
                print('#' * 80)
                while True:
                    file.write(q.get())
    except KeyboardInterrupt:
        print('\nRecording finished: ' + repr(filename))
        # exit(0)
    except Exception as e:
        exit(type(e).__name__ + ': ' + str(e))



def play_wav():
    filename = "input.wav"
    device = None
    try:
        data, fs = sf.read(filename, dtype='float32')
        sd.play(data, fs, device=device)
        status = sd.wait()
    except KeyboardInterrupt:
        exit('\nInterrupted by user')
    except Exception as e:
        print (type(e).__name__ + ': ' + str(e))
    if status:
        print ('Error during playback: ' + str(status))

if __name__ == '__main__':
    play_wav()