#!/usr/bin/env python3

import numpy
import sys
import pathlib
import unittest
import wave

sys.path.append("../python")
import reference_cffi

SAMPLES = (pathlib.Path(__file__)/"../../samples/").resolve()

class DecodeTest(unittest.TestCase):
	def test_decode_against_reference(self, audio_name="allegaeon-beasts-and-worms"):
		w = wave.open(str(SAMPLES/(audio_name+".decoded.wav")))
		w_bytes = w.readframes(w.getnframes())
		w_np = numpy.frombuffer(w_bytes, dtype=numpy.int16).reshape(w.getnchannels(), w.getnframes(), order='F')

		d = reference_cffi.Decode((SAMPLES/(audio_name+".qoa")).open("br").read())
		assert d.desc.samples == w.getnframes()
		assert d.desc.channels == w.getnchannels()
		assert d.desc.samplerate == w.getframerate()

		decoded_samples = d.decode()

		np_samples = numpy.frombuffer(
			reference_cffi.ffi.buffer(decoded_samples),
			dtype=numpy.int16
		).reshape(d.desc.channels, d.desc.samples, order='F')

		assert (np_samples==w_np[:,:np_samples.shape[1]]).all()
		assert np_samples.shape == w_np.shape

if __name__ == "__main__":
    unittest.main()
