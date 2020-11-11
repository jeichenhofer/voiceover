import argparse
import tempfile
import queue
import sys
import os
import sounddevice as sd
import soundfile as sf
import numpy  # Make sure NumPy is loaded before it is used in the callback
assert numpy  # avoid "imported but unused" message (W0611)
import time
from datetime import datetime as dt

def record_wav():
    q = queue.Queue()
    filename_base = "output.wav"
    # if os.path.exists(filename): os.remove(filename)
    samplerate = 8000
    channels = 1
    subtype = None
    device = None


    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())


    target_fs = [v.split(",")[0] for v in open("msg_list.csv").readlines()]
    target_fs = ["test1.wav", "test2.wav"]
    while True:
        try:
            timestamp = dt.utcnow().isoformat().replace(':', '-')
            filename = "result/%s" % (target_fs[0])
            target_fs = target_fs[1:]
            file = sf.SoundFile(filename, mode='x', samplerate=samplerate,
                          channels=channels, subtype=subtype)
            with sd.InputStream(samplerate=samplerate, device=device,
                                channels=channels, callback=callback):
                print('#' * 80)
                print ("Wait for signals...")
                # print('press Ctrl+C to stop the recording')
                # print('#' * 80)
                is_st = 0
                end_cnt = 0
                while True:
                    t = q.get()
                    c = numpy.count_nonzero(t)
                    if is_st == 0:
                        if c != 0:
                            print ("A client joins the meeting")
                            print ("Start recording...")
                            file.write(t)
                            is_st = 1
                    else:
                        file.write(t)
                        if end_cnt == 2500:
                            print ("Prepare for save, 50%")
                        if end_cnt == 3000:
                            print ("Prepare for save, 100%")
                        if c == 0:
                            end_cnt += 1
                            if end_cnt > 3000:
                                print ("Save to %s, wait for next messsage" % filename)
                                file.close()
                                break
                        else:
                            end_cnt = 0


        except KeyboardInterrupt:
            print ("Exit...")
            # print('\nRecording finished: ' + repr(filename))
            exit(0)
        except Exception as e:
            exit(type(e).__name__ + ': ' + str(e))

def play_wav(filename):
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
