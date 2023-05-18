#!/usr/bin/env python3

import numpy
import sys
import pathlib
import unittest
import wave

sys.path.append("../python")
import qoa as module

SAMPLES = (pathlib.Path(__file__)/"../../samples/").resolve()

class DecodeTest(unittest.TestCase):
	def test_decode_against_reference(self, audio_name="allegaeon-beasts-and-worms"):
		w = wave.open(str(SAMPLES/(audio_name+".decoded.wav")))
		w_bytes = w.readframes(w.getnframes())
		w_np = numpy.frombuffer(w_bytes, dtype=numpy.int16).reshape(w.getnframes(), w.getnchannels())

		d = module.Decoder.from_file(SAMPLES/(audio_name+".qoa"))
		d.decode_header()
		assert d.total_sample_count == w.getnframes()
		assert d.channels == w.getnchannels()
		assert d.samplerate == w.getframerate()

		decoded_samples = d.decode(_check_against=w_np)

		assert (decoded_samples==w_np[:len(decoded_samples)]).all()
		assert decoded_samples.shape == w_np.shape

if __name__ == "__main__":
    unittest.main()
