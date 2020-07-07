import numpy as np


class Wavinator:

    def __init__(self, f_carrier=None):
        from Wavinator.ConvolutionCodec import ConvolutionCodec
        from Wavinator.IQModem import IQModem

        self._codec = ConvolutionCodec()
        if f_carrier is not None:
            self._modem = IQModem(f_carrier=f_carrier)
        else:
            self._modem = IQModem()

    def wavinate(self, message: bytes):
        # convert bytes to ndarray of uint8 (unsigned byte array)
        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        byte_array = np.frombuffer(message, dtype=data_type)

        # encode with convolution coder and modulate into waveform
        coded = self._codec.encode(byte_array)
        return self._modem.modulate(coded)

    def dewavinate(self, rx_wave: np.ndarray):
        coded = self._modem.demodulate(rx_wave)
        return self._codec.decode(coded)

    @staticmethod
    def truncate(rx_wave: np.ndarray, threshold):
        # Remove any zeroes at front
        for i in range(len(rx_wave)):
            if abs(rx_wave[i]) > threshold:
                rx_wave = rx_wave[i:]
                break

        return rx_wave

    @property
    def bit_rate(self):
        return self._codec.coding_rate * self._modem.bitrate

    @property
    def sample_rate(self):
        return self._modem.sample_rate
