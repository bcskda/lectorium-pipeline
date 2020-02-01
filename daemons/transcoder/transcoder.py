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

from typing import Dict
from config import Config
from transcode_v2 import transcode, TranscodeError, validate_args
from daemons.abc import BaseQueueExecutor, JobQueueDaemon, JsonRequestHandler


class TranscodeRequestHandler(JsonRequestHandler):
    def handle(self):
        if self.request_obj is None:
            self.response_obj["error"] = 1
            self.response_obj["error_desc"] = "Invalid JSON"
            return

        self.response_obj["error"] = 0
        self.response_obj["result"] = {
            "accept": [],
            "discard": []
        }

        for idx, job in enumerate(self.request_obj):
            try:
                self.server.daemon.job_queue.put(TranscodeJob(job))
                self.response_obj["result"]["accept"].append(idx)
            except TranscodeError as e:
                response["result"]["discard"].append({
                    "index": idx, "type": f"{type(e)}", "desc": f"{e}"
                })

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

class TranscodeExecutor(BaseQueueExecutor):
    def handle_job(self, job):
        with open(f"{job.outputs[0]}.transcode_log", "w") as stderr:
            transcode(job.profile, job.inputs, job.outputs, stderr=stderr)
            # TODO report progress
