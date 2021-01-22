import wavio
import numpy as np
import multiprocessing

REDUNDANCY_FACTOR = 2


# decoding of each unique frame
def decode_frame(waver, audio):
    recovered_frame = None
    frame_samples = waver.samples_per_frame

    # brute force decode up to 2 frames worth of samples, accepting the first successful decoding
    for i in range(REDUNDANCY_FACTOR*frame_samples):
        try:
            recovered_frame, frame_num = waver.dewavinate(audio)
            break
        except ValueError:
            audio = audio[1:]

    return recovered_frame


# parallelize decoding of each unique frame
def parallel_decode(audio, debug=False):
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()
    audio = waver.truncate(audio, 20)

    # after truncation we expect this many possible unique frames
    frame_samples = waver.samples_per_frame
    total_frames = len(audio) // (REDUNDANCY_FACTOR * frame_samples)

    # parallelize decoding among all possible CPU cores
    pool = multiprocessing.Pool()
    # split audio signal where we expect unique frames to be
    recovered_bytes = pool.starmap(decode_frame,
                                   [(waver, audio[i*(REDUNDANCY_FACTOR*frame_samples):]) for i in range(total_frames)])
    pool.close()
    pool.join()

    # filter out None values
    recovered_bytes = list(filter(lambda x: x is not None, recovered_bytes))

    # calculate recovered frames
    num_frames = len(recovered_bytes)

    # convert bytes to message
    recovered_bytes = np.concatenate(recovered_bytes, axis=0)
    recovered_bytes = recovered_bytes.tobytes().decode("utf-8", "replace")
    try:
        recovered_message = waver.unpad_message(recovered_bytes)
    except ValueError:
        recovered_message = recovered_bytes

    return recovered_message, num_frames


# demodulates according to which frame was demodulated (a duplicate vs original frame)
# Note: assumes redundancy factor of 2 and correct checksums
def fast_decode(audio, debug=False):
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # truncate silence from beginning
    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()
    audio = waver.truncate(audio, 20)

    frame_samples = waver.samples_per_frame
    recovered_bytes = []
    recovered_frames = 0

    while len(audio) > 0:
        try:
            # demodulate
            recovered_frame, frame_num = waver.dewavinate(audio)

            # add to frames and bytes recovered
            recovered_frames += 1
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
    try:
        recovered_message = waver.unpad_message(recovered_bytes)
    except ValueError:
        recovered_message = recovered_bytes

    return recovered_message, recovered_frames


# demodulates any frame, maximize frames recovered
def slow_decode(audio, debug=False):
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # truncate silence from beginning
    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()
    audio = waver.truncate(audio, 20)

    frame_samples = waver.samples_per_frame
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
    message, frames_recovered = parallel_decode(audio_signal)

    # print message and stats
    print("Demodulated (received) data: " + message)
    print("Recovered " + str(frames_recovered) + " frames")
