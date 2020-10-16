import numpy as np


class Wavinator:

    def __init__(self, f_carrier=None, frame_len=None, redundancy_factor=None):
        from Wavinator.ConvolutionCodec import ConvolutionCodec
        from Wavinator.IQModem import IQModem

        self._codec = ConvolutionCodec()
        if f_carrier is not None:
            self._modem = IQModem(f_carrier=f_carrier)
        else:
            self._modem = IQModem()

        if frame_len is None:
            self._frame_len = 2
            self._bits = 96
        else:
            # ensure frame size pairs (i, i+1) where i is odd have same number of encoded bits
            self._frame_len = frame_len
            if frame_len % 2 == 0:
                self._bits = 96 + (24 * ((frame_len - 1) // 2))
            else:
                self._bits = 96 + (24 * (frame_len // 2))

        if redundancy_factor is None:
            self._redundancy_factor = 2
        else:
            self._redundancy_factor = redundancy_factor

    def wavinate(self, message: bytes):
        frame_num = 1

        signal_tx = np.array([], dtype=np.float64)
        for i in range(0, len(message), self._frame_len):
            for j in range(self._redundancy_factor):
                frame = self.wavinate_frame(message[i:i + self._frame_len], frame_num)
                signal_tx = np.concatenate([signal_tx, frame])
                frame_num += 1

        return signal_tx

    def wavinate_frame(self, message: bytes, frame_number):

        # convert bytes to ndarray of uint8 (unsigned byte array)
        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        message_bytes = np.frombuffer(message, dtype=data_type)

        # encode with convolution coder and modulate into waveform
        coded = self._codec.encode(message_bytes, frame_number)
        return self._modem.modulate(coded)

    def dewavinate(self, rx_wave: np.ndarray):
        coded = self._modem.demodulate(rx_wave)
        return self._codec.decode(coded[:self._bits])

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
