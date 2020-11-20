import logging
import numpy as np
from time import time
from datetime import datetime as dt
timestamp = dt.utcnow().isoformat().replace(':', '_')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # instantiate codec and modem parameters
    from Wavinator.Wavinator import Wavinator
    frame_len = 2
    redundancy_factor = 2
    frame_samples = 2604
    waver = Wavinator(frame_len=frame_len, redundancy_factor=redundancy_factor)

    import wavio

    while True:
        sentence = input('Input text for coding and modulation...')
        if sentence is not None and len(sentence) >= 16:
            sentence = waver.pad_message(sentence)
            sentence_bytes = bytes(sentence, encoding='utf-8')

            signal_tx = waver.wavinate(sentence_bytes)

            signal_rx = signal_tx
            recovered_bytes = np.array([], dtype=np.uint8)
            while len(signal_rx) > 0:
                recovered_frame, frame_num = waver.dewavinate(signal_rx)
                recovered_bytes = np.concatenate([recovered_bytes, recovered_frame])
                if frame_num % 2 != 0:
                    signal_rx = signal_rx[frame_samples*2:]
                else:
                    signal_rx = signal_rx[frame_samples:]

            recovered_sentence = str(recovered_bytes.tobytes(), encoding='utf-8')
            recovered_sentence = waver.unpad_message(recovered_sentence)

            wavio.write('data/sentence_signal_{}.wav'.format(timestamp), signal_tx, waver.sample_rate, sampwidth=2)
            logging.info('Saved audio to data/sentence_signal_{}.wav'.format(timestamp))
            print('Recovered from audio: ' + recovered_sentence)
        else:
            break
