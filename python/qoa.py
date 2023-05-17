#!/usr/bin/env python3

import collections
import logging
import math
import numpy
import struct

FILE_HEADER_STRUCT = struct.Struct(">4sI")
FRAME_HEADER_STRUCT = struct.Struct(">B3sHH")
SLICE_STRUCT = struct.Struct(">Q")
QOA_SLICE_LEN = 20

FIRST_FRAME_OFFSET = FILE_HEADER_STRUCT.size

def dequant_sf(sf_quant): # in spec [1]
    return round(pow(sf_quant + 1, 2.75))

def dequant_r(qr, sf): # in spec [3]
    DEQUANT_TAB = [0.75, -0.75, 2.5, -2.5, 4.5, -4.5, 7, -7] # in spec [2]
    r = sf * DEQUANT_TAB[qr]
    if r < 0:
        return math.ceil(r - 0.5)
    else:
        return math.floor(r + 0.5)

# precompute dequant_r lookup table
DEQUANT_TAB = [
    [dequant_r(qr, dequant_sf(sf_quant))
            for qr in range(8)]
        for sf_quant in range(16)
]
# just like qoa_dequant_tab[16][8] from qoa.h:
assert DEQUANT_TAB == eval("""{
	{   1,    -1,    3,    -3,    5,    -5,     7,     -7},
	{   5,    -5,   18,   -18,   32,   -32,    49,    -49},
	{  16,   -16,   53,   -53,   95,   -95,   147,   -147},
	{  34,   -34,  113,  -113,  203,  -203,   315,   -315},
	{  63,   -63,  210,  -210,  378,  -378,   588,   -588},
	{ 104,  -104,  345,  -345,  621,  -621,   966,   -966},
	{ 158,  -158,  528,  -528,  950,  -950,  1477,  -1477},
	{ 228,  -228,  760,  -760, 1368, -1368,  2128,  -2128},
	{ 316,  -316, 1053, -1053, 1895, -1895,  2947,  -2947},
	{ 422,  -422, 1405, -1405, 2529, -2529,  3934,  -3934},
	{ 548,  -548, 1828, -1828, 3290, -3290,  5117,  -5117},
	{ 696,  -696, 2320, -2320, 4176, -4176,  6496,  -6496},
	{ 868,  -868, 2893, -2893, 5207, -5207,  8099,  -8099},
	{1064, -1064, 3548, -3548, 6386, -6386,  9933,  -9933},
	{1286, -1286, 4288, -4288, 7718, -7718, 12005, -12005},
	{1536, -1536, 5120, -5120, 9216, -9216, 14336, -14336},
}""".replace("{", "[").replace("}", "]"))

class Lms:
    """
    QOA predicts each audio sample based on the previously decoded ones
    using a “Sign-Sign Least Mean Squares Filter“ (LMS). This
    prediction plus the dequantized residual forms the final output
    sample.
    """

    STRUCT = struct.Struct(">4h4h")

    @classmethod
    def load(cls, buf, offset):
        lms_state = cls.STRUCT.unpack_from(buf, offset)

        self = cls()

        self.history = collections.deque(lms_state[0:4], maxlen=4)
        self.weights = list(lms_state[4:8])

        logging.info(f"LMS history={list(self.history)} weights={self.weights}")

        return self

    def predict(self): # in spec [4]
        prediction = sum((w*s) for (w, s) in zip(self.weights, self.history))
        assert int(prediction).to_bytes(4, signed=True)
        return prediction >> 13

    def update(self, sample, residual):
        assert residual.to_bytes(4, signed=True)
        delta = residual >> 4

        # logging.info(f"LMS history={list(self.history)} weights={self.weights} {delta=}")

        for i in range(4): # in spec [6]
            self.weights[i] = self.weights[i] + (-delta if self.history[i] < 0 else delta)
            assert self.weights[i].to_bytes(4, signed=True)
            # https://phoboslab.org/log/2023/02/qoa-time-domain-audio-compression#:~:text=i%20have%20not%20proven%20that%20they%20do
            # BUG(https://github.com/phoboslab/qoa/issues/25)

        self.history.append(sample) # in spec [7]

class Decoder():
    @classmethod
    def from_file(cls, filename):
        self = cls()
        self.buf = open(filename, "br").read()
        logging.info(f"Decoding {filename!r}, {len(self.buf)} bytes long...")
        return self

    def decode_header(self):
        magic, self.total_sample_count = FILE_HEADER_STRUCT.unpack_from(self.buf)
        assert magic == b'qoaf'
        self.decode_frame_header(FIRST_FRAME_OFFSET)

    def decode_frame_header(self, frame_offset, dynamic_ok=False):
        (
            frame_channels,
            frame_samplerate_s,
            self.fsamples,
            self.fsize,
        ) = FRAME_HEADER_STRUCT.unpack_from(self.buf, frame_offset)
        frame_samplerate = int.from_bytes(frame_samplerate_s, 'big')

        if hasattr(self, "samplerate"):
            assert (self.samplerate == frame_samplerate) or dynamic_ok
        self.samplerate = frame_samplerate
        if hasattr(self, "channels"):
            assert (self.channels == frame_channels) or dynamic_ok
        self.channels = frame_channels

        logging.info(f"fsize={self.fsize} @{frame_offset} => fsamples={self.fsamples}")

    def decode_slice(self, lms, offset):
        """Generator to decode one slice at offset, yield each samples"""
        s, = SLICE_STRUCT.unpack_from(self.buf, offset)
        scalefactor = s >> 60 # aka sf_quant
        qr = [(s >> (i*3)) & 0b111 for i in reversed(range(0, QOA_SLICE_LEN))]
        # logging.info(f"{scalefactor} {qr!r}")
        for quantized in qr:
            predicted = lms.predict()
            dequantized = DEQUANT_TAB[scalefactor][quantized]
            reconstructed = numpy.clip(predicted + dequantized, -32768, 32767)
            yield reconstructed # in spec [5]
            lms.update(sample=reconstructed, residual=dequantized)

    def decode_frame(self, frame_offset, dest):
        """Decode one frame at frame_offset into dest."""
        o = frame_offset
        self.decode_frame_header(o)
        o += FRAME_HEADER_STRUCT.size

        lms = [] # indexed by channel
        for ch in range(self.channels):
            lms.append(Lms.load(self.buf, o))
            o += Lms.STRUCT.size

        for sample_index in range(0, self.fsamples, QOA_SLICE_LEN):
            for ch in range(self.channels):
                # logging.info(f"{ch=} {sample_index=}")
                slice_samples = tuple(self.decode_slice(lms[ch], o))
                try:
                    dest[ch][sample_index : sample_index + QOA_SLICE_LEN] = slice_samples
                except ValueError:
                    # "The last slice (for each channel) in the last
                    # frame may contain less than 20 samples"
                    # so let's crop slice_samples so it fits
                    slice_samples = slice_samples[:self.total_sample_count % 20]
                    dest[ch][sample_index : sample_index + QOA_SLICE_LEN] = slice_samples
                o += SLICE_STRUCT.size

        assert (o - frame_offset) == self.fsize, "we should have consumed the whole frame"
        return self.fsize

    def decode(self, _check_against=None):
        """Decode then return numpy array with whole file."""
        self.decode_header()
        samples = numpy.empty((self.channels, self.total_sample_count), numpy.int16)

        sample_index = 0
        frame_offset = FIRST_FRAME_OFFSET

        while sample_index < self.total_sample_count:
            frame_size = self.decode_frame(frame_offset, samples[:,sample_index:])
            logging.info(f"finished a {frame_size=} @{frame_offset} => samples @[{sample_index}: +{self.fsamples}] / {self.total_sample_count} total")

            if not frame_size:
                break

            if _check_against is not None:
                assert ((samples[:,sample_index:sample_index+self.fsamples] ==
                        _check_against[:,sample_index:sample_index+self.fsamples]).all())

            frame_offset += frame_size
            sample_index += self.fsamples
        return samples

logging.basicConfig(
    # style="{",
    format = "%(funcName)s() %(message)s",
    level = logging.DEBUG
)
