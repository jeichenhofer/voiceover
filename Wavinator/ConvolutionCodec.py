import logging
import numpy as np
import commpy.channelcoding.convcode as cc

LENGTH_SIZE = 4
SYNCWORD = 0xFFFFFFFF


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

    @staticmethod
    def _find_preamble(message: np.ndarray):
        position = -1
        skip = 1
        for i in range(0, len(message)-LENGTH_SIZE, skip):
            skip = 0
            for j in range(LENGTH_SIZE-1, -1, -1):
                if message[i+j] != 0xFF:
                    skip = j+1
            if skip == 0:
                position = i
                break

        return position

    def encode(self, message: np.ndarray) -> np.ndarray:
        """
        Use the configured trellis to perform convolutional encoding on the given message bits.

        :param message: array of message bits (minimum length determined by trellis)
        :return: array of encoded message bits ready for modulation
        """

        # prepend length to message
        message_length = len(message)
        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        length_bytes = np.frombuffer(
            message_length.to_bytes(LENGTH_SIZE, byteorder='big', signed=False),
            dtype=data_type
        )
        message = np.insert(message, 0, length_bytes)

        # prepend syncword to message
        syncword_bytes = np.frombuffer(
            SYNCWORD.to_bytes(LENGTH_SIZE, byteorder='big', signed=False),
            dtype=data_type
        )
        message = np.insert(message, 0, syncword_bytes)

        # convert bytes to bit array
        bits = np.unpackbits(message, bitorder='big')

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

        # align with syncword
        start = self._find_preamble(message)
        if start == -1:
            raise RuntimeError('Aligning failed')
        # truncate syncword to get rest of message
        message = message[start+LENGTH_SIZE:]

        # detect message length and truncate
        message_length = int.from_bytes(message[0:LENGTH_SIZE], byteorder='big', signed=False)
        if message_length > len(message) - LENGTH_SIZE:
            logging.info("Message-length tag: {} > {} - 4".format(message_length, len(message)))
            raise RuntimeError('Invalid message-length tag')
        message = message[LENGTH_SIZE:LENGTH_SIZE+message_length]

        logging.info('Decoded {} convolution coded parity bits into {}-byte message'.format(
            len(encoded), message_length)
        )
        return message

    @property
    def coding_rate(self):
        return 0.7435  # i have no idea why this works...
        # return self._trellis.k / (self._trellis.n * 0.895)  # i have no idea why this works...
        # return self._trellis.k / self._trellis.n
