#!/usr/bin/env python3
"""Wraps the reference implementation (phoboslab/qoa) so it's "easily"
callable and introspectable from python. A little more clunky to use
than the pure python, but more accurate (since it includes the reference)
and way faster."""

import cffi
import pathlib
import numpy
import subprocess

ffi = cffi.FFI()

QOA_FILENAME = (pathlib.Path(__file__)/"../../qoa-reference/qoa.h").resolve()

# preprocess since cffi cannot do most # directives
pre = subprocess.check_output([
    "gcc", "-E", # preprocess only
    "-P", # inhibit linemarkers
    QOA_FILENAME,
], encoding="utf8")
ffi.cdef(pre)
ffi.cdef("void free(void *ptr);")

ffi.set_source(
    "cffi_qoa_impl",
    """
    #define QOA_IMPLEMENTATION
    #include "qoa.h"
    """,
    include_dirs = (QOA_FILENAME.parent,))
lib = ffi.dlopen(ffi.compile(tmpdir="../build/"))

def qoa_to_dict(desc):
    return{k:getattr(desc, k) for k in dir(desc)}

class Decoder():
    def __init__(self, encoded_bytes):
        self.b = encoded_bytes
        self.desc = ffi.new("qoa_desc *")
        assert self.decode_header() == 8

    @classmethod
    def from_file(cls, filename):
        with filename.open("br") as f:
            file_contents = f.read()
        return cls(file_contents)

    def decode_header(self):
        bytes_consumed = lib.qoa_decode_header(self.b, len(self.b), self.desc)
        self.total_sample_count = self.desc.samples
        self.channels = self.desc.channels
        self.samplerate = self.desc.samplerate
        return bytes_consumed

    def decode_frame(self, offset, dest_samples):
        b_slice = self.b[offset:]
        frame_len = ffi.new("unsigned int *") # samples decoded count for a single channel
        bytes_consumed = lib.qoa_decode_frame(b_slice, len(b_slice), self.desc, dest_samples, frame_len)
        return (bytes_consumed, frame_len[0])

    @property
    def max_frame_size(self):
        return lib.qoa_max_frame_size(self.desc)

    def c_decode(self, _check_against=None):
        ret = lib.qoa_decode(self.b, len(self.b), self.desc)
        # return ffi.gc(ret, lib.free, size=total_samples*ffi.sizeof("short"))
        total_samples = self.desc.channels * self.desc.samples
        buf = ffi.gc(ffi.cast(f"short[{total_samples}]", ret), lib.free)
        return numpy.frombuffer(
            ffi.buffer(buf),
            dtype=numpy.int16
        ).reshape(self.total_sample_count, self.channels)

    def py_decode(self):
        pass

    decode = c_decode

    def __repr__(self):
        return f"Decode(desc={qoa_to_dict(self.desc)})"

if __name__ == "__main__":
    d = Decode(open("../samples/allegaeon-beasts-and-worms.qoa", "br").read())
    buf = d.decode()
