import wavio
import time
import numpy as np

frame_samples = 2604  # number of samples in a given frame


# demodulates according to which frame was demodulated (a duplicate vs original frame)
def fast_decode(audio):
    #import logging
    #logging.basicConfig(level=logging.DEBUG)

    # truncate silence from beginning
    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()
    audio = waver.truncate(audio, 20)

    recovered_bytes = []
    recovered_frames = []

    while len(audio) > 0:
        try:
            # demodulate
            recovered_frame, frame_num = waver.dewavinate(audio)

            # add to frames and bytes recovered
            recovered_frames.append(frame_num)
            recovered_bytes.append(recovered_frame)

            # if the frame we demodulated was a duplicate, only move by one frame
            if frame_num % 2 != 0:
                audio = audio[2*frame_samples:]
            else:
                audio = audio[frame_samples:]

        except ValueError:
            # failed to demodulate, brute force start of next frame
            audio = audio[1:]

    # convert bytes to message
    recovered_bytes = np.concatenate(recovered_bytes, axis=0)
    recovered_bytes = recovered_bytes.tobytes().decode("utf-8", "replace")
    recovered_message = waver.unpad_message(recovered_bytes)

    return recovered_message, recovered_frames


# demodulates any frame, maximize frames recovered
def slow_decode(audio):
    #import logging
    #logging.basicConfig(level=logging.DEBUG)

    # truncate silence from beginning
    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()
    audio = waver.truncate(audio, 20)

    recovered_bytes = []
    recovered_frames = []
    expected_frame = 1

    while len(audio) > 0:
        try:
            # demodulate
            recovered_frame, frame_num = waver.dewavinate(audio)
            recovered_frames.append(frame_num)

            if frame_num != expected_frame - 1:
                # even frame is a duplicate frame
                # if not a duplicate frame we expect next unique frame to be two frames away, otherwise one frame away
                if frame_num % 2 != 0:
                    expected_frame = frame_num + 2
                else:
                    expected_frame = frame_num + 1

                recovered_bytes.append(recovered_frame)

            audio = audio[frame_samples:]
        except (RuntimeError, ValueError):
            audio = audio[1:]

    # convert bytes to message
    recovered_bytes = np.concatenate(recovered_bytes, axis=0)
    recovered_bytes = recovered_bytes.tobytes().decode("utf-8", "replace")
    recovered_message = waver.unpad_message(recovered_bytes)

    return recovered_message, recovered_frames


if __name__ == '__main__':
    # read audio signal
    file = "data/" + input("Enter filename: ") + ".wav"
    audio_signal = wavio.read(file)
    audio_signal = audio_signal.data.reshape((audio_signal.data.shape[0], ))

    # decode audio signal
    message, frames_recovered = fast_decode(audio_signal)

    # print message and stats
    print("Demodulated (received) data: " + message)
    print("Recovered " + str(len(frames_recovered)) + " frames")
