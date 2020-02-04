import io
import struct
from typing import List


BUFFER_SIZE = 0x1000

class StreamPackWriter:
    """Sequentially writes several streams into one.
    Input streams should be seekable.
    Output format: number of stream and concatenation of (size, chunk) pairs
    for each input stream, where size is stream length and chunk is stream content.
    All inetegers are 8-byte unsigned big-endian.
    """
    
    def __init__(self, dest: io.BufferedWriter):
        self.inputs = []
        self.output = dest
    
    def add_input(self, stream: io.BufferedReader):
        self.inputs.append(stream)
    
    def transmit(self):
        self.output.write(struct.pack(">Q", len(self.inputs)))
        for stream in self.inputs:
            cpos = stream.tell()
            stream.seek(0, io.SEEK_END)
            size = stream.tell() - cpos
            stream.seek(cpos)
            self._transmit_stream(stream, size)
    
    def _transmit_stream(self, stream, size):
        buf = struct.pack(">Q", size)
        while buf:
            print(f"{buf}")
            self.output.write(buf)
            buf = stream.read(BUFFER_SIZE)

class StreamPackReader:
    """Decodes stream pack into original streams. """
    
    def __init__(self, source: io.BufferedReader):
        self.source = source
        stream_count_enc = source.read(8)
        self.stream_count = struct.unpack(">Q", stream_count_enc)[0]
        self.outputs = None
    
    def set_outputs(self, outputs: List[io.BufferedWriter]):
        self.outputs = outputs
    
    def receive(self, outputs):
        if len(outputs) != self.stream_count:
            raise ValueError("Output count mismatch")
        for stream in outputs:
            self._receive_stream(stream)
    
    def _receive_stream(self, output):
        stream_size_enc = self.source.read(8)
        stream_size = struct.unpack(">Q", stream_size_enc)[0]
        recv_size = 0
        while recv_size < stream_size:
            buf = self.source.read(min(BUFFER_SIZE, stream_size - recv_size))
            recv_size += len(buf)
            output.write(buf)

if __name__ == "__main__":
    lines = ["qwerty", "1337"]
    inputs = [io.BytesIO(ln.encode()) for ln in lines]
    
    dest = io.BytesIO()
    pack_writer = StreamPackWriter(dest)
    for istream in inputs:
        pack_writer.add_input(istream)
    pack_writer.transmit()
    dest.seek(0)
    
    pack_reader = StreamPackReader(dest)
    outputs = [io.BytesIO() for i in range(pack_reader.stream_count)]
    print(f"Outputs: {outputs}")
    pack_reader.receive(outputs)
    for idx, stream in enumerate(outputs):
        print(f"Stream {idx}: {stream.getvalue()}")
