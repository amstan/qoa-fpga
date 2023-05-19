#!/usr/bin/env python3

"""Multi-target test system for qoa encoders and decoders."""

import argparse
import numpy
import pathlib
import sys
import unittest
import wave

class QoaTest(unittest.TestCase):
    def test_lms(self):
        ORIGINAL_WEIGHTS = [0,0,-100,200]

        l = module.Lms.load(
            history=[0,0,0,100],
            weights=ORIGINAL_WEIGHTS.copy(),
        )
        assert l.predict() == 2

        l.update(-30000, 100)
        assert l.history[-1] == -30000
        assert l.weights != ORIGINAL_WEIGHTS
        assert l.predict() == -756

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
    modules = (pathlib.Path(__file__)/"../../python").resolve()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--implementation",
                        choices=[m.stem for m in modules.glob("*.py")],
                        default="python_qoa",
    )
    args, unittest_args = parser.parse_known_args(sys.argv)
    if "--" in unittest_args: unittest_args.remove("--")

    sys.path.append(str(modules))
    module = __import__(args.implementation)

    SAMPLES = (pathlib.Path(__file__)/"../../samples/").resolve()

    unittest.main(argv=unittest_args, exit=(not sys.flags.interactive))
