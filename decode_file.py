import wavio
import numpy as np

if __name__ == '__main__':
    file = "data/" + input("Enter filename: ") + ".wav"
    audio = wavio.read(file)
    audio = audio.data.reshape((audio.data.shape[0], ))

    import logging
    logging.basicConfig(level=logging.DEBUG)

    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()
    audio = waver.truncate(audio, 20)
    recovered_bytes = np.array([], dtype=np.uint8)
    recovered = []
    num_recovered = 0
    expected_frame = 1
    frame_samples = 3348  # number of samples in a given frame
    while len(audio) > 0:
        try:
            recovered_frame, frame_num = waver.dewavinate(audio)
            recovered.append(frame_num)
            if frame_num != expected_frame - 1:
                if frame_num % 2 != 0:
                    expected_frame = frame_num + 2
                else:
                    expected_frame = frame_num + 1
                recovered_bytes = np.concatenate([recovered_bytes, recovered_frame])
            audio = audio[frame_samples:]
            num_recovered += 1
        except (RuntimeError, ValueError):
            audio = audio[1:]

    print("Demodulated (received) data: " + recovered_bytes.tobytes().decode("utf-8", "replace"))
    print("Recovered " + str(num_recovered) + " frames")
    print(recovered)