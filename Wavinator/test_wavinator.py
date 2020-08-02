from unittest import TestCase
import numpy as np


class TestWavinator(TestCase):
    def test_wavinator_random(self):
        # instantiate the wavinator
        from Wavinator.Wavinator import Wavinator
        waver = Wavinator()

        # create test data
        data_tx = bytes(np.random.bytes(1024))

        # create transmit signal
        signal_tx = waver.wavinate(data_tx)

        # perfect loss-less signal transmission
        signal_rx = signal_tx

        # recover original data from signal
        data_rx = waver.dewavinate(signal_rx)

        for i, byte in enumerate(data_rx):
            assert byte == data_rx[i]

    def test_message_frame(self):
        from Wavinator.MessageFrame import construct_frame, check_extract_frame

        message = bytes('well hello there!', 'utf-8')

        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        byte_array = np.frombuffer(message, dtype=data_type)

        frame = construct_frame(byte_array)
        extracted = check_extract_frame(frame)

        for i, val in enumerate(extracted):
            assert val == message[i]

    def test_message_checksum(self):
        from Wavinator.MessageFrame import construct_frame, check_extract_frame
        import random

        message = bytes('well hello there!', 'utf-8')

        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        byte_array = np.frombuffer(message, dtype=data_type)

        frame = construct_frame(byte_array)
        random_index = random.randint(0, len(frame))
        frame[random_index] = 1 if frame[random_index] == 0 else 0

        try:
            extracted = check_extract_frame(frame)
            assert False
        except ValueError as e:
            assert 'checksum' in str(e)
