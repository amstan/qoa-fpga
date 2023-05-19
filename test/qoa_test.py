#!/usr/bin/env python3

"""Multi-target test system for qoa encoders and decoders."""

import argparse
import numpy
import pathlib
import sys
import unittest
import wave

class QoaTest(unittest.TestCase):
    def test_lms_history(self, samples=[32767, -100, 100, -32768]):
        """LMS should update history properly."""
        l = module.Lms.load(
            history=[0, 0, 0, 0],
            weights=[0, 0, 0, 0]
        )

        for sample in samples:
            l.update(
                sample,
                residual=0, # not testing this
            )

        assert list(l.history) == samples

    def conduct_lms_predict_test(self, history, weights, update=None, post_predict=None, pre_predict=None):
        """LMS should predict properly and update weights correctly."""
        l = module.Lms.load(history=history, weights=weights)

        if pre_predict is not None:
            assert l.predict() == pre_predict

        if update is not None:
            sample, residual = update
            l.update(sample, residual)
            assert l.history[-1] == sample
            assert l.weights != weights
            if post_predict is not None:
                assert l.predict() == post_predict

    def test_lms_predict(self):
        tests = {
            "trivial": dict(
                history=[0, 0, 0, 100],
                weights=[0, 0, -100, 200],
                pre_predict=2,
                update=(-30000, 100),
                post_predict=-756,
            ),
            # TODO: more to follow
        }
        for name, test in tests.items():
            with self.subTest(name):
                self.conduct_lms_predict_test(**test)

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
