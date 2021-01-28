import wavio
import numpy as np
import multiprocessing

REDUNDANCY_FACTOR = 2
DEBUG = True


if DEBUG:
    import logging
    logging.basicConfig(level=logging.DEBUG)


# convert bytes to message
def bytes_to_message(waver, recovered_bytes):

    # convert bytes to message
    recovered_bytes = np.concatenate(recovered_bytes, axis=0)

    # Handles case where message is split such that we can't have uniform sized frames
    # Note: assumes that we cannot have 0x00 as part of message
    # Other solution would be to bring back variable-length frames
    recovered_bytes = recovered_bytes[recovered_bytes != 0]

    recovered_bytes = recovered_bytes.tobytes().decode("utf-8", "replace")
    try:
        recovered_message = waver.unpad_message(recovered_bytes)
    except ValueError:
        recovered_message = recovered_bytes

    return recovered_message


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
def parallel_decode(waver, audio):

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

    recovered_message = bytes_to_message(waver, recovered_bytes)

    return recovered_message, num_frames


# demodulates according to which frame was demodulated (a duplicate vs original frame)
# Note: assumes redundancy factor of 2 and correct checksums
def linear_fast_decode(waver, audio):

    frame_samples = waver.samples_per_frame
    recovered_bytes = []
    recovered_frames = 0

    while len(audio) > waver.samples_per_frame - 1:
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

    recovered_message = bytes_to_message(waver, recovered_bytes)

    return recovered_message, recovered_frames


# demodulates any frame, maximize frames recovered
def linear_slow_decode(waver, audio):

    frame_samples = waver.samples_per_frame
    recovered_bytes = []
    recovered_frames = 0
    expected_frame = 1

    while len(audio) > waver.samples_per_frame - 1:
        try:
            # demodulate
            recovered_frame, frame_num = waver.dewavinate(audio)
            recovered_frames += 1

            if frame_num != expected_frame - 1:
                # even frame is a duplicate frame
                # if not a duplicate frame we expect next unique frame to be two frames away, otherwise one frame away
                if frame_num % 2 != 0:
                    expected_frame = frame_num + 2
                else:
                    expected_frame = frame_num + 1

                recovered_bytes.append(recovered_frame)

            audio = audio[frame_samples:]
        except ValueError:
            audio = audio[1:]

    recovered_message = bytes_to_message(waver, recovered_bytes)

    return recovered_message, recovered_frames


if __name__ == '__main__':
    # read audio signal
    file = "data/" + input("Enter filename: ") + ".wav"
    audio_signal = wavio.read(file)
    audio_signal = audio_signal.data.reshape((audio_signal.data.shape[0], ))

    from Wavinator.Wavinator import Wavinator
    frame_len = 2
    wavinator = Wavinator(frame_len=frame_len)
    audio_signal = wavinator.truncate(audio_signal, 20)

    # decode audio signal
    message, frames_recovered = parallel_decode(wavinator, audio_signal)

    # print message and stats
    print("Demodulated (received) data: " + message)
    print("Recovered " + str(frames_recovered) + " frames")
