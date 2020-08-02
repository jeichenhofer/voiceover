import numpy as np

LENGTH_SIZE = 2
CHECKSUM_SIZE = 2


def construct_frame(message_bytes: np.ndarray) -> np.ndarray:
    # setup standard data type
    data_type = np.dtype('uint8')
    data_type = data_type.newbyteorder('>')

    # create frame buffer
    frame_len = LENGTH_SIZE + CHECKSUM_SIZE + len(message_bytes)
    message_start = LENGTH_SIZE + CHECKSUM_SIZE
    if frame_len % 2 != 0:
        frame_len += 1
        message_start += 1
    frame_buffer = np.zeros((frame_len,), dtype=data_type)

    # set message
    frame_buffer[message_start:] = message_bytes

    # set length in buffer
    message_length = len(message_bytes)
    len_bytes = message_length.to_bytes(LENGTH_SIZE, byteorder='big', signed=False)
    frame_buffer[:LENGTH_SIZE] = np.frombuffer(len_bytes, dtype=data_type)

    # compute checksum value
    checksum = _compute_checksum(frame_buffer)
    # set checksum in buffer
    checksum_bytes = checksum.to_bytes(LENGTH_SIZE, byteorder='big', signed=False)
    frame_buffer[LENGTH_SIZE:(LENGTH_SIZE + CHECKSUM_SIZE)] = np.frombuffer(checksum_bytes, dtype=data_type)

    # convert to bit array
    frame_bits = np.unpackbits(frame_buffer, bitorder='big')
    return frame_bits


def check_extract_frame(frame_bits: np.ndarray) -> np.ndarray:
    # convert to byte array from bit array
    frame_buffer = np.packbits(frame_bits, bitorder='big')

    if _compute_checksum(frame_buffer) != 0:
        raise ValueError('message checksum invalid')

    # get message length
    message_length = int.from_bytes(frame_buffer[0:LENGTH_SIZE], byteorder='big', signed=False)
    # compute start of message
    message_start = LENGTH_SIZE + CHECKSUM_SIZE
    if message_length % 2 != 0:
        message_start += 1

    # extract message bytes
    message = frame_buffer[message_start:]

    if len(message) != message_length:
        raise ValueError('message length invalid')

    return message


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
