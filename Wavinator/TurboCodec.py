import logging
import numpy as np
import commpy.channelcoding.convcode as cc
import commpy.channelcoding as cx

LENGTH_SIZE = 2
INTERLEAVER_LEN = 15
SEED = 0


class TurboCodec:
    def __init__(self):
        """
        Initialize the codec scheme with trellis structure:
            G(D) = [[1, 0, 0], [0, 1, 1+D]]
            F(D) = [[D, D], [1+D, 1]]
        """
        # instantiate trellis object
        self._trellis = self._make_trellis()
        self._interleaver = cx.RandInterlv(INTERLEAVER_LEN, SEED)

        logging.info('Instantiated TurboCodec with default trellis r = 2/3')

    @staticmethod
    def _make_trellis() -> cc.Trellis:
        """
        Convlutional Code:
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

        # prepend length to message
        message_length = len(message)
        data_type = np.dtype('uint8')
        data_type = data_type.newbyteorder('>')
        length_bytes = np.frombuffer(
            message_length.to_bytes(LENGTH_SIZE, byteorder='big', signed=False),
            dtype=data_type
        )
        message = np.insert(message, 0, length_bytes)

        # convert bytes to bit array
        bits = np.unpackbits(message, bitorder='big')

        # perform the turbo encoding
        encoded_streams = cx.turbo_encode(bits, self._trellis, self._trellis, self._interleaver)
        logging.info('Encoded {}-byte message into {}-bit turbo coded systematic output '
                     'with {}-bit and {}-bit parity streams'.format(
                            message_length, len(encoded_streams[0]), len(encoded_streams[1]), len(encoded_streams[2]))
        )
        return encoded_streams

    def decode(self, encoded_streams) -> np.ndarray:
        """
        Use the configured trellis to perform vitirbi decoding algorithm on the received encoded bits.

        :param encoded_streams: array of bits encoded then received
        :return: array of decoded message bits that were originally encoded (with probability varying by signal noise)
        """
        # decode the probable bits from the encoded string
        decoded = cx.turbo_decode(encoded_streams[0], encoded_streams[1], encoded_streams[2], self._trellis)

        # return the bytes from the decoded bits
        message = np.packbits(decoded, bitorder='big')

        # detect message length and truncate
        message_length = int.from_bytes(message[0:LENGTH_SIZE], byteorder='big', signed=False)
        if message_length > len(message) - LENGTH_SIZE:
            logging.info("Message-length tag: {} > {} - 4".format(message_length, len(message)))
            raise RuntimeError('Invalid message-length tag')
        message = message[LENGTH_SIZE:LENGTH_SIZE+message_length]

        logging.info('Decoded {} turbo coded bit stream with {} and {} bit parity streams into {}-byte message'.format(
            len(encoded_streams[0]), len(encoded_streams[1]), len(encoded_streams[2]), message_length)
        )
        return message

    @property
    def coding_rate(self):
        return 0.7435  # i have no idea why this works...
        # return self._trellis.k / (self._trellis.n * 0.895)  # i have no idea why this works...
        # return self._trellis.k / self._trellis.n
