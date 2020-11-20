import numpy as np
from Wavinator.Wavinator import Wavinator

TOTAL_BYTES = 0
BITS_PER_BYTE = 8
HEADER_SIZE = 6


def load_template(filename: str):
    model_samples = np.load(filename)['arr_0']
    return model_samples


def gen_audio_segment(wave_gen: Wavinator, duration: int):
    import secrets
    global TOTAL_BYTES

    # This get bit_rate from CC.py
    num_bytes = int(round(wave_gen.bit_rate * duration /
                          (BITS_PER_BYTE * wave_gen.redundancy_factor * (1 + (HEADER_SIZE / wave_gen.frame_len)))))
    TOTAL_BYTES += num_bytes
    data_tx = secrets.token_bytes(num_bytes)
    return wave_gen.wavinate(data_tx)


def fill_half_template(wave_gen: Wavinator, template_array: np.ndarray) -> np.ndarray:
    # first speaker
    audio_signal = np.zeros((1,))
    segment_start = -1
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
                new_signal = gen_audio_segment(wave_gen, segment_length)
            # append new waveform to end of existing waveform
            audio_signal = np.append(audio_signal, new_signal)
            segment_start = i

    return audio_signal


def pad_array(short, long):
    original_shape = np.shape(short)
    padded_array = np.zeros(np.shape(long))
    padded_array[:original_shape[0]] = short
    return padded_array


if __name__ == '__main__':
    temp_file = 'data/timing_templates/gan/009999.npz'
    templates = load_template(temp_file)

    waver = Wavinator()

    for temp_num, template in enumerate(templates):
        # first speaker
        print('speaker A')
        speaker_a = fill_half_template(waver, template[0, :])
        # print(TOTAL_BYTES)
        TOTAL_BYTES = 0

        # second speaker
        print('speaker B')
        speaker_b = fill_half_template(waver, template[1, :])
        # print(TOTAL_BYTES)

        # match length
        if len(speaker_a) < len(speaker_b):
            speaker_a = pad_array(speaker_a, speaker_b)
        elif len(speaker_b) < len(speaker_a):
            speaker_b = pad_array(speaker_b, speaker_a)

        import wavio
        file_a = 'data/output_audio/gan_modeled/{TEMPLATE_NUM:03}a.wav'.format(TEMPLATE_NUM=temp_num)
        wavio.write(file_a, speaker_a, waver.sample_rate, sampwidth=2)
        print('speaker_a duration: {}s/{}s'.format(len(speaker_a) / waver.sample_rate, '300'))

        file_b = 'data/output_audio/gan_modeled/{TEMPLATE_NUM:03}b.wav'.format(TEMPLATE_NUM=temp_num)
        wavio.write(file_b, speaker_b, waver.sample_rate, sampwidth=2)
        print('speaker_b duration: {}s/{}s'.format(len(speaker_b) / waver.sample_rate, '300'))

        # output ten hours worth of 5-minute samples
        break
