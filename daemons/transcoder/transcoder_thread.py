import sys
from typing import Dict
from config import Config
from transcode_v2 import transcode, validate_args, TranscodeError


class TranscodeJob:
    def __init__(self, job: Dict):
        try:
            self.inputs = job["inputs"]
            self.outputs = job["outputs"]
            self.profile = job["profile"]
        except TypeError as e:
            raise TranscodeError(f"Bad arguments types: {e}") from e
        except KeyError as e:
            raise TranscodeError(f"Missing argument: {e}") from e
        
        validate_args(self.inputs, self.outputs, self.profile)
        

def transcoder_loop(transcode_queue):
    while True:
        try:
            # TODO graceful shutdown
            job = transcode_queue.get()
            with open(f"{job.outputs[0]}.transcode_log", "w") as stderr:
                transcode(job.profile, job.inputs, job.outputs, stderr=stderr)
                # TODO report progress
        except Exception as e:
            print(f"[transcoder_thread.transcoder_loop] Unhandled exception: {e}", file=sys.stderr)
