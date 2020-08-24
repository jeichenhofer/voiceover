import logging
import numpy as np
from time import time
from datetime import datetime as dt
timestamp = dt.utcnow().isoformat().replace(':', '_')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # instantiate codec and modem parameters
    from Wavinator.Wavinator import Wavinator
    waver = Wavinator()

    import wavio

    while True:
        sentence = input('Input text for coding and modulation...')
        if sentence is not None and len(sentence) >= 16:
            sentence_bytes = bytes(sentence, encoding='utf-8')

            frame_len = 2
            signal_tx = np.array([], dtype=np.float64)
            for i in range(0, len(sentence_bytes), frame_len):
                frame = waver.wavinate(sentence_bytes[i:i+frame_len])
                signal_tx = np.concatenate([signal_tx, frame])

            signal_rx = signal_tx
            recovered_bytes = np.array([], dtype=np.uint8)
            while len(signal_rx) > 0:
                recovered_frame = waver.dewavinate(signal_rx)
                recovered_bytes = np.concatenate([recovered_bytes, recovered_frame])
                signal_rx = signal_rx[2604:]
            recovered_sentence = str(recovered_bytes.tobytes(), encoding='utf-8')

            wavio.write('data/sentence_signal_{}.wav'.format(timestamp), signal_tx, waver.sample_rate, sampwidth=2)
            logging.info('Saved audio to data/sentence_signal_{}.wav'.format(timestamp))
            print('Recovered from audio: ' + recovered_sentence)
        else:
            break
