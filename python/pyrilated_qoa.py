#!/usr/bin/env python3

"""
pyrilated wrapper for the verilog implementation of QOA.

This wrapper provides the same interface as the pure python implementation,
allowing it to be used in the same test, or even mix and match parts with
the python implementation.
"""

from pathlib import Path
import logging
import struct
import sys

# TODO: split off pyrilator in a separate project
sys.path.append(str((Path(__file__)/"../../pyrilator").resolve()))
from pyrilator import pyrilate, cast_to_unsigned, cast_to_signed, MAX_INT32
BUILD_DIR = Path(__file__)/"../../build/"

class Lms:
    VERILOG_PATH = (Path(__file__)/"../../verilog/lms.sv").resolve()
    LmsDut = pyrilate(VERILOG_PATH, build_dir=BUILD_DIR)

    STRUCT = struct.Struct(">4h4h")

    def _clock(self):
        self.dut.clk = 0
        self.dut.eval()
        self.dut.clk = 1
        self.dut.eval()

    def __init__(self):
        self.dut = self.LmsDut()
        self.dut.rst = 1
        self._clock()
        self.dut.rst = 0

    @property
    def weights(self):
        return [cast_to_signed(x, 2) for x in self.dut.save_weights]
    @property
    def history(self):
        return [cast_to_signed(x, 2) for x in self.dut.save_history]

    @classmethod
    def load(cls, buf:bytes=None, history:list=None, weights:list=None):
        if buf:
            lms_state = cls.STRUCT.unpack_from(buf)
            history = lms_state[0:4]
            weights = lms_state[4:8]

        self = cls()

        self.dut.load = 1
        self.dut.load_history = [cast_to_unsigned(x, 2) for x in history]
        self.dut.load_weights = [cast_to_unsigned(x, 2) for x in weights]
        self._clock()
        self.dut.load = 0

        logging.info(self)
        return self

    PREDICT_MASK = MAX_INT32 ^ (MAX_INT32 >> 13)
    def predict(self):
        prediction = self.dut.prediction
        if prediction & (1<<14):
            # sign extent
            prediction |= self.PREDICT_MASK
        return cast_to_signed(prediction, 4)

    def update(self, sample, residual):
        self.dut.update = 1
        self.dut.sample = cast_to_unsigned(sample, 2)
        self.dut.delta = cast_to_unsigned(residual >> 4, 2)
        self._clock()
        self.dut.update = 0

        # logging.info(f"{self!r} delta={self.dut.delta}")

    def __repr__(self):
        return f"LMS history={list(self.dut.save_history)} weights={self.dut.save_weights}"

if __name__=="__main__":
    ORIGINAL_WEIGHTS = [0,0,-100,200]

    l = Lms.load(
        history=[0,0,0,100],
        weights=ORIGINAL_WEIGHTS.copy(),
    )
    assert l.predict() == 2

    l.update(-30000, 100)
    assert l.history[-1] == -30000
    assert l.weights != ORIGINAL_WEIGHTS
    assert l.predict() == -756
