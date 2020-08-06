import numpy as np


class Wavinator:

    def __init__(self, f_carrier=None, f_symbol=None):
        from Wavinator.ConvolutionCodec import ConvolutionCodec
        from Wavinator.IQModem import IQModem

        self._codec = ConvolutionCodec()
        if f_carrier is not None and f_symbol is not None:
            self._modem = IQModem(f_carrier=f_carrier, f_symbol=f_symbol)
        elif f_carrier is not None and f_symbol is None:
            self._modem = IQModem(f_carrier=f_carrier)
        elif f_carrier is None and f_symbol is not None:
            self._modem = IQModem(f_symbol=f_symbol)
        else:
            self._modem = IQModem()

    def wavinate(self, message: bytes):
        # convert bytes to ndarray of uint8 (unsigned byte array)
        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        message_bytes = np.frombuffer(message, dtype=data_type)

        frame_len = 2
        coded_bytes = np.array([], dtype=data_type)
        for i in range(0, len(message_bytes), frame_len):
            frame = self._codec.encode_frame(message_bytes[i:i+frame_len])
            coded_bytes = np.concatenate([coded_bytes, frame])

        coded = self._codec.encode(coded_bytes)

        # encode with convolution coder and modulate into waveform
        return self._modem.modulate(coded)

    def dewavinate(self, rx_wave: np.ndarray):
        coded = self._modem.demodulate(rx_wave)
        return self._codec.decode(coded)

    def dewavinate_dilated_signal(self, rx_wave: np.ndarray, num_symbols):
        return self._modem.demodulate_dilated_signal(rx_wave, num_symbols)

    @staticmethod
    def truncate(rx_wave: np.ndarray, threshold):
        # Remove any zeroes at front
        for i in range(len(rx_wave)):
            if abs(rx_wave[i]) > threshold:
                rx_wave = rx_wave[i:]
                break

        return rx_wave

    @staticmethod
    def divide_frames(byte_array: np.ndarray, num_frames):
        raise NotImplementedError()

    @property
    def bit_rate(self):
        return self._codec.coding_rate * self._modem.bitrate

    @property
    def sample_rate(self):
        return self._modem.sample_rate
