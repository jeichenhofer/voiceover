import numpy as np
import wavio
from Wavinator.Wavinator import Wavinator
from datetime import datetime as dt
timestamp = dt.utcnow().isoformat().replace(':', '_')

TOTAL_BYTES = 0
BITS_PER_BYTE = 8
HEADER_SIZE = 4  # 2-byte checksum + 2-byte frame number


def load_template(filename: str):
    model_samples = np.load(filename)['arr_0']
    return model_samples


def fill_half_template(wave_gen: Wavinator, template_array: np.ndarray, plaintext: bytes) -> np.ndarray:
    # first speaker
    audio_signal = np.zeros((1,))
    segment_start = -1
    plaintext_bytes = plaintext
    plaintext_len = len(plaintext_bytes)
    total_bytes = 0
    for i, curr_sample in enumerate(template_array):
        if i == len(template_array) - 1 or template_array[i + 1] != curr_sample:
            # reached end of segment or end of template
            segment_length = i - segment_start
            if curr_sample < 0:
                # not speaking, generate silence
                num_samples = int(round(segment_length * wave_gen.sample_rate))
                new_signal = np.zeros((num_samples,))
            else:
                # speaking, generate waveform
                num_bytes = int(round(wave_gen.bit_rate * segment_length /
                                      (BITS_PER_BYTE*wave_gen.redundancy_factor*(1+(HEADER_SIZE/wave_gen.frame_len)))))

                new_signal = wave_gen.wavinate(plaintext_bytes[0:num_bytes])

                plaintext_bytes = plaintext_bytes[num_bytes:]
                total_bytes += num_bytes
            # append new waveform to end of existing waveform
            audio_signal = np.append(audio_signal, new_signal)
            segment_start = i

            if total_bytes >= plaintext_len:
                break

    return audio_signal


if __name__ == '__main__':
    temp_file = 'data/timing_templates/gan/009999.npz'
    templates = load_template(temp_file)

    frame_len = 6
    waver = Wavinator(frame_len=frame_len)

    for temp_num, template in enumerate(templates):
        sentence = input('Input text for coding and modulation...')
        if sentence is not None and len(sentence) >= 16:
            sentence = waver.pad_message(sentence)
            sentence_bytes = bytes(sentence, encoding='utf-8')
        else:
            break

        speaker = fill_half_template(waver, template[0, :], sentence_bytes)

        file = 'data/output_audio/gan_modeled/sentence_signal_{}.wav'.format(timestamp)
        wavio.write(file, speaker, waver.sample_rate, sampwidth=2)
        print('speaker duration: {}s'.format(len(speaker) / waver.sample_rate))

        break
