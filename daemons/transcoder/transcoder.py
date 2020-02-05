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
import logging
import socket
from typing import Dict
from config import Config
from transcode_v2 import transcode, TranscodeError, validate_args
from daemons.abc import BaseQueueExecutor, JobQueueDaemon, JsonRequestHandler


class TranscodeRequestHandler(JsonRequestHandler):
    def handle_obj(self):
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
                self.server.daemon.job_queues["q_transcode_accept"].put(TranscodeJob(job))
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
    def __init__(self, job_queue, report_queue):
        super(TranscodeExecutor, self).__init__(job_queue)
        self.report_queue = report_queue

    def handle_job(self, job):
        with open(f"{job.outputs[0]}.transcode_log", "w") as stderr:
            transcode(job.profile, job.inputs, job.outputs, stderr=stderr)
            # TODO report progress
            self.report_queue.put(job.outputs)

class ResultReporter(BaseQueueExecutor):
    def __init__(self, job_queue, report_addr):
        super(ResultReporter, self).__init__(job_queue)
        self.report_addr = report_addr

    def handle_job(self, job):
        logging.info("ResultReporter: finished {}", job)
        message = {
            "message_type": "transcode_result",
            "message": {"outputs": job}
        }
        with socket.create_connection(self.report_addr) as sock:
            with sock.makefile("w") as sock_w:
                json.dump(message, sock_w)
            sock.shutdown(socket.SHUT_WR)
            with sock.makefile("r") as sock_r:
                ans = json.load(sock_r)
            logging.info("ResultReporter: remote answer: {}", ans)
