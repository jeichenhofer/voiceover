import logging
import numpy as np


class IQModem:
    def __init__(self, const_size: int = 4, f_symbol: int = 128, f_sample: int = int(8e3), f_carrier: int = int(1e3)):
        """
        Initialize the audio component of a modulator/demodulator using IQ modulation of complex QAM symbols.

        :param const_size: number of points in QPSK constellation
        :param f_symbol: symbol frequency (symbols per second)
        :param f_carrier: carrier frequency for the signal
        :param f_sample: sample rate for DAC/ADC
        """
        from Wavinator.ConvolutionCodec import ConvolutionCodec
        self._codec = ConvolutionCodec()
        # instantiate the QAM map for 4QPSK
        from commpy import modulation as mod
        self._modem = mod.PSKModem(const_size)

        # define basic parameters
        self._f_symbol = f_symbol
        self._f_sample = f_sample
        self._f_carrier = f_carrier

        self._w_carrier = 2 * np.pi * self._f_carrier  # angular frequency of raw carrier
        self._symbol_period = 1 / self._f_symbol  # seconds per symbol
        self._upsmple_factor = int(self._symbol_period * self._f_sample)  # samples per symbol

        # compute/construct filter FIR coefficents and delays
        rrc_delay, self._rrc_fir = self._construct_rrc_filter()
        lp_delay, self._lp_fir = self._construct_lowpass_filter()
        self._filter_delay_samples = int((2 * rrc_delay + lp_delay) * self._f_sample)

        logging.info(
            'Instantiated IQModem with const_size {CS}, f_symbol {FSY}, f_sample {FSA}, and f_carrier {FC}'.format(
                CS=const_size,
                FSY=f_symbol,
                FSA=f_sample,
                FC=f_carrier,
            )
        )

    def _construct_rrc_filter(self):
        # filter parameters
        rrc_len_factor = 6
        rrc_alpha_coefficient = 0.4

        from commpy.filters import rrcosfilter
        filter_len_sec = rrc_len_factor * self._symbol_period
        filter_len_samples = int(filter_len_sec * self._f_sample)
        _, rrc = rrcosfilter(N=filter_len_samples, alpha=rrc_alpha_coefficient, Ts=self._symbol_period, Fs=self._f_sample)

        delay = filter_len_sec / 2
        return delay, rrc

    def _construct_lowpass_filter(self):
        # filter parameters
        lp_cutoff_factor = 5
        lp_order = 51

        from scipy.signal import firwin
        nyquist_bandwidth = self._f_symbol / 2
        cutoff = lp_cutoff_factor * nyquist_bandwidth
        lp_filter = firwin(lp_order, cutoff / (self._f_sample / 2))

        delay = (lp_order // 2) / self._f_sample
        return delay, lp_filter

    def modulate(self, coded_bits: np.ndarray) -> np.ndarray:
        """
        Take a series of bits (the baseband digital signal) and modulate it into an analog bandpass
        signal at the carrier frequency using IQ modulation.

        Coded bits -> QPSK Map -> Upsample Comb -> RRC Filter -> IQ Modulation -> Waveform (sampled analog signal)

        :param coded_bits: digital baseband signal as series of bits (probably encoded)
        :return: sampled analog signal of the modulated waveform
        """
        # map bits to QPSK symbols
        qam_symbols = self._modem.modulate(coded_bits)

        # upsample the qam symbols to a comb signal and apply pulse shaping rrc filter
        from scipy.signal import upfirdn
        baseband_signal = upfirdn(self._rrc_fir, qam_symbols, self._upsmple_factor)
        baseband_signal_t = np.arange(len(baseband_signal)) / self._f_sample

        # compute the in-phase and quadrature components of the signal
        i_quad = baseband_signal.real * np.cos(self._w_carrier * baseband_signal_t)
        q_quad = baseband_signal.imag * np.sin(self._w_carrier * baseband_signal_t) * (-1)

        # sum the quadrature signals to get a real-valued signal for transmission
        signal = i_quad + q_quad
        logging.info('Modulated {}-bit coded signal with {} samples'.format(len(coded_bits), len(signal)))
        return signal

    def demodulate(self, rx_wave: np.ndarray) -> np.ndarray:
        """
        Extract the complex QAM symbols modulated into the given rx_wave. Demodulates the IQ modulation implemented by
        the modulate method above.

        Waveform -> IQ Extraction -> Image Reject Filter -> RRC Filter -> Downsample -> Demodulate QPSK -> coded bits

        :param rx_wave: sampled analog IQ modulated waveform
        :return: message bits extracted from the modulated signal
        """

        # extract the quadrature components
        rx_wave_t = np.arange(len(rx_wave)) / self._f_sample
        i_quad = rx_wave * np.cos(self._w_carrier * rx_wave_t)
        q_quad = rx_wave * np.sin(self._w_carrier * rx_wave_t) * (-1)

        # filter the quadrature signals
        from scipy.signal import lfilter
        i_quad = lfilter(self._lp_fir, 1, i_quad)
        q_quad = lfilter(self._lp_fir, 1, q_quad)

        # combine the signals back into complex quadrature representation
        recovered = i_quad + 1.j * q_quad

        # apply the second rrc filter for full raised cosine filter
        recovered_signal = np.convolve(recovered, self._rrc_fir)

        # discard prepended delay samples from filtering and sample remaining signal to recover original symbols
        recovered_symbols = recovered_signal[self._filter_delay_samples::int(self._upsmple_factor)]

        # demodulate the symbols into bits modulating the signal
        bits = self._modem.demodulate(recovered_symbols, demod_type='hard')
        # truncate to nearest length that is a multiple of 24
        if len(bits) % 24 != 0:
            bits = bits[:(len(bits) // 24) * 24]
        logging.info('Demodulated signal with {} samples to a {}-bit message'.format(len(rx_wave), len(bits)))
        return bits

    def demodulate_dilated_signal(self, rx_wave: np.ndarray, num_symbols) -> np.ndarray:
        windowsize = num_symbols * self._upsmple_factor
        expected_freq = 1000
        error = 100
        length_size = 2
        message = np.array([], dtype=np.int)

        # divide signal into windows and calculated the fft for each window
        for i in range(0, len(rx_wave), windowsize):
            window = rx_wave[i:i+windowsize]
            y = np.fft.fft(window)
            freqs = np.fft.fftfreq(windowsize)
            peak = np.argmax(y)  # find index of peak
            freq = freqs[peak]
            freq_hz = abs(freq * self._f_sample)
            baud = 128

            # brute forcing baud rate loop
            data_rx = None
            while data_rx is None:
                data_rx = self.demodulate_segment(window)
                if freq_hz < expected_freq - error:
                    baud -= 1
                elif freq_hz > expected_freq + error:
                    baud += 1
                self.__init__(f_carrier=freq_hz, f_symbol=baud)
                pass
            bits = self._codec.decode_segment(data_rx)
            message = np.concatenate([message, bits])

        message = np.packbits(message, bitorder='big')
        # truncate message-length tag
        message_length = int.from_bytes(message[0:length_size], byteorder='big', signed=False)
        if message_length > len(message) - length_size:
            raise RuntimeError('Invalid message-length tag')
        message = message[length_size:length_size+message_length]

        return message

    def demodulate_segment(self, segment: np.ndarray) -> np.ndarray:
        # extract the quadrature components
        rx_wave_t = np.arange(len(segment)) / self._f_sample
        i_quad = segment * np.cos(self._w_carrier * rx_wave_t)
        q_quad = segment * np.sin(self._w_carrier * rx_wave_t) * (-1)

        # filter the quadrature signals
        from scipy.signal import lfilter
        i_quad = lfilter(self._lp_fir, 1, i_quad)
        q_quad = lfilter(self._lp_fir, 1, q_quad)

        # combine the signals back into complex quadrature representation
        recovered = i_quad + 1.j * q_quad

        # apply the second rrc filter for full raised cosine filter
        recovered_signal = np.convolve(recovered, self._rrc_fir)

        # discard prepended delay samples from filtering and sample remaining signal to recover original symbols
        recovered_signal = recovered_signal[self._filter_delay_samples::int(self._upsmple_factor)]

        # demodulate the symbols into bits modulating the signal
        bits = self._modem.demodulate(recovered_signal, demod_type='hard')
        logging.info('Demodulated signal with {} samples to a {}-bit message'.format(len(segment), len(bits)))
        return bits

    @property
    def bitrate(self):
        return self._modem.num_bits_symbol * self._f_symbol

    @property
    def sample_rate(self):
        return self._f_sample
