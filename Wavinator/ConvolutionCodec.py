import logging
import numpy as np
import commpy.channelcoding.convcode as cc

LENGTH_SIZE = 2
CHECKSUM_SIZE = 2

class ConvolutionCodec:
    def __init__(self):
        """
        Initialize the codec scheme with trellis structure:
            G(D) = [[1, 0, 0], [0, 1, 1+D]]
            F(D) = [[D, D], [1+D, 1]]
        """
        # instantiate trellis object
        self._trellis = self._make_trellis()

        logging.info('Instantiated ConvolutionCodec with default trellis r = 2/3')

    @staticmethod
    def _make_trellis() -> cc.Trellis:
        """
        Convolutional Code:
            G(D) = [[1, 0, 0], [0, 1, 1+D]]
            F(D) = [[D, D], [1+D, 1]]

        :return: trellis object implementing this convolutional encoding scheme
        """
        # Number of delay elements in the convolutional encoder
        memory = np.array((1, 1))

        # Generator matrix & feedback matrix
        g_matrix = np.array(((1, 0, 0), (0, 1, 3)))
        feedback = np.array(((2, 2), (3, 1)))

        # Create trellis data structure
        return cc.Trellis(memory, g_matrix, feedback, 'rsc')

    def encode(self, message: np.ndarray) -> np.ndarray:
        """
        Use the configured trellis to perform convolutional encoding on the given message bits.

        :param message: array of message bits (minimum length determined by trellis)
        :return: array of encoded message bits ready for modulation
        """
        # setup data type
        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')

        # create frame buffer
        frame_len = LENGTH_SIZE + CHECKSUM_SIZE + len(message)
        message_start = LENGTH_SIZE + CHECKSUM_SIZE
        if frame_len % 2 != 0:
            frame_len += 1
            message_start += 1
        frame_buffer = np.zeros((frame_len,), dtype=data_type)

        # set message
        frame_buffer[message_start:] = message

        # prepend length to message
        message_length = len(message)
        length_bytes = np.frombuffer(
            message_length.to_bytes(LENGTH_SIZE, byteorder='big', signed=False),
            dtype=data_type
        )
        frame_buffer[:LENGTH_SIZE] = np.frombuffer(length_bytes, dtype=data_type)

        # compute checksum value
        checksum = self._compute_checksum(frame_buffer)
        # set checksum in buffer
        checksum_bytes = checksum.to_bytes(LENGTH_SIZE, byteorder='big', signed=False)
        frame_buffer[LENGTH_SIZE:(LENGTH_SIZE + CHECKSUM_SIZE)] = np.frombuffer(checksum_bytes, dtype=data_type)

        # convert bytes to bit array
        bits = np.unpackbits(frame_buffer, bitorder='big')

        # perform the convolution encoding
        encoded = cc.conv_encode(bits, self._trellis, termination='cont')
        logging.info('Encoded {}-byte message into {}-bit convolution coded parity message'.format(
            message_length, len(encoded))
        )
        return encoded

    def decode(self, encoded: np.ndarray) -> np.ndarray:
        """
        Use the configured trellis to perform vitirbi decoding algorithm on the received encoded bits.

        :param encoded: array of bits encoded then received
        :return: array of decoded message bits that were originally encoded (with probability varying by signal noise)
        """
        # decode the probable bits from the encoded string
        decoded = cc.viterbi_decode(encoded, self._trellis, decoding_type='hard')

        # return the bytes from the decoded bits
        message = np.packbits(decoded, bitorder='big')
        # detect message length and truncate
        message_length = int.from_bytes(message[0:LENGTH_SIZE], byteorder='big', signed=False)
        if message_length > len(message) - LENGTH_SIZE:
            raise RuntimeError('Invalid message-length tag')
        message_end = message_length + LENGTH_SIZE + CHECKSUM_SIZE
        if message_length % 2 != 0:
            message_end += 1
        message = message[:message_end]

        if self._compute_checksum(message) != 0:
            raise ValueError('message checksum invalid')

        # compute start of message
        message_start = LENGTH_SIZE + CHECKSUM_SIZE
        if message_length % 2 != 0:
            message_start += 1

        # extract message bytes
        message = message[message_start:]

        logging.info('Decoded {} convolution coded parity bits into {}-byte message'.format(
            len(encoded), message_length)
        )
        return message

    def decode_segment(self, segment: np.ndarray) -> np.ndarray:
        # decode the probable bits from the encoded string
        decoded = cc.viterbi_decode(segment, self._trellis, decoding_type='hard')

        logging.info('Decoded {} convolution coded parity bits into {}-byte message'.format(
            len(segment), len(decoded))
        )
        return decoded

    @staticmethod
    def _compute_checksum(buffer):
        checksum = 0
        it = iter(buffer)
        for val in it:
            # combine two bytes into checksum word
            curr_word = (val << 8) + (next(it) & 0x00ff)
            # add to running sum
            checksum += curr_word
        # add remainder back into checksum
        checksum = (checksum >> 16) + (checksum & 0xffff)
        return int(~checksum & 0xffff)

    @property
    def coding_rate(self):
        return 0.7435  # i have no idea why this works...
        # return self._trellis.k / (self._trellis.n * 0.895)  # i have no idea why this works...
        # return self._trellis.k / self._trellis.n
