import numpy as np


class Wavinator:

    def __init__(self, f_symbol=None, f_carrier=None, frame_len=None, redundancy_factor=None):
        from Wavinator.ConvolutionCodec import ConvolutionCodec
        from Wavinator.IQModem import IQModem

        self._codec = ConvolutionCodec()

        # handle user-specified baud and carrier frequencies
        if f_carrier is not None and f_symbol is not None:
            self._modem = IQModem(f_symbol=f_symbol, f_carrier=f_carrier)
        elif f_carrier is not None:
            self._modem = IQModem(f_carrier=f_carrier)
        elif f_symbol is not None:
            self._modem = IQModem(f_symbol=f_symbol)
        else:
            self._modem = IQModem()

        # defaults: frame length = 2, 72 bits per frame
        if frame_len is None:
            self._frame_len = 2
            self._bits = 72
        else:
            # handle user-specified frame length
            self._frame_len = frame_len
            # ensure frame size pairs (i, i+1) where i is odd have same number of encoded bits
            if frame_len % 2 == 0:
                self._bits = 72 + (24 * ((frame_len - 1) // 2))
            else:
                self._bits = 72 + (24 * (frame_len // 2))

        # handle user-specified redundancy factor (default: 2 frames (1 original + 1 duplicate))
        if redundancy_factor is None:
            self._redundancy_factor = 2
        else:
            self._redundancy_factor = redundancy_factor

        # number of samples per frame
        # (not sure if this works for all baud+carrier frequency combos but it works for the default)
        self._base_samples = 41

    def wavinate(self, message: bytes):
        # initialize frame number for frame number portion of header
        frame_num = 1
        signal_tx = np.array([], dtype=np.float64)

        # create a frame for each portion of the message, stepping by frame_len
        for i in range(0, len(message), self._frame_len):
            # create duplicate frames if necessary
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
        frame, frame_num = self._codec.decode(coded[:self._bits])

        if len(frame) == self._frame_len + 1:
            frame = frame[1:]

        return frame, frame_num

    def pad_message(self, message):
        # apply PKCS7 padding to the message to ensure constant frame lengths
        padding_len = self._frame_len - (len(message) % self._frame_len)

        for i in range(padding_len):
            message += str(padding_len)
        return message

    def unpad_message(self, message):
        # remove PKCS7 padding
        padding_len = int(message[len(message) - 1])
        return message[:len(message) - padding_len]

    @staticmethod
    def truncate(rx_wave: np.ndarray, threshold):
        # Truncate the head of the signal if it is less than the threshold (real-valued number)
        for i in range(len(rx_wave)):
            if abs(rx_wave[i]) > threshold:
                rx_wave = rx_wave[i:]
                break

        return rx_wave

    @property
    # Bit rate given by convolutional codec and modem (for GAN)
    def bit_rate(self):
        return self._codec.coding_rate * self._modem.bitrate

    @property
    # Sample rate of modem
    def sample_rate(self):
        return self._modem.sample_rate

    @property
    # Redundancy factor
    def redundancy_factor(self):
        return self._redundancy_factor

    @property
    # Frame length
    def frame_len(self):
        return self._frame_len

    @property
    # Samples per frame
    def samples_per_frame(self):
        if self._frame_len % 2 == 0:
            return (self._base_samples + (12 * ((self._frame_len - 1) // 2))) * self._modem.samples_per_symbol
        else:
            return (self._base_samples + (12 * (self._frame_len // 2))) * self._modem.samples_per_symbol
