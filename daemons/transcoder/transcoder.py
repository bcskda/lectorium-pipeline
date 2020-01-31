"""Transcoder daemon

Example:
(venv) $ python -m daemons.transcoder 2>/dev/null &
(venv) $ nc -N localhost 1337 | jq << _DOC
[{
    "inputs": [
        ["input_dir/PRIVATE/AVCHD/BDMV/STREAM/00000.MTS"]
    ],
    "outputs": [
        "output_dir/00000.mp4"
    ],
    "profile": "concat_copy"
}]
_DOC

Output:
{"error": 0, "result": {"accept": [0], "discard": []}}
"""

import json
import queue
import socketserver
import sys
import time
from threading import Thread
from typing import Dict
from config import Config
from transcode_v2 import transcode, TranscodeError, validate_args
from daemons.abc import JobQueueDaemon


class TranscodeRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        _daemon = self.server.daemon
        response = {}
        response["error"] = 0
        response["result"] = {"accept": [], "discard": []}
        
        try:
            try:
                jobs = json.load(self.rfile) # Probably expect clients to indicate shutdown
            except json.JSONDecodeError as e:
                response["error"] = 1
                response["error_desc"] = f"JSONDecodeError: {e}"
                raise
            
            for idx, job in enumerate(jobs):
                try:
                    _daemon.job_queue.put(TranscodeJob(job))
                    response["result"]["accept"].append(idx)
                except TranscodeError as e:
                    response["result"]["discard"].append({"index": idx, "desc": f"{e}"})

        except Exception as e:
            response["error"] = 1
            response["error_desc"] = f"Unhandled exception: {e}"
        finally:
            self.wfile.write(json.dumps(response).encode("utf-8"))

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

class TranscodeExecutor:
    def __init__(self, transcode_queue: queue.Queue, poll_interval=0.5):
        self._running = False
        self._shutdown_requested = False
        self._poll_interval = poll_interval
        self.transcode_queue = transcode_queue

    def run(self):
        self._running = True # thread-safety left
        while not self._shutdown_requested:
            try:
                try:
                    job = self.transcode_queue.get(timeout=self._poll_interval)
                except queue.Empty:
                    continue
                with open(f"{job.outputs[0]}.transcode_log", "w") as stderr:
                    transcode(job.profile, job.inputs, job.outputs, stderr=stderr)
                    # TODO report progress
            except Exception as e:
                print(f"[TranscodeExecutor] Unhandled exception: {e}", file=sys.stderr)
        self._running = False

    def shutdown(self):
        self._shutdown_requested = True
        while self._running:
            time.sleep(self._poll_interval)
        self._shutdown_requested = False
        print("TranscodeExecutor shutdown finished")
