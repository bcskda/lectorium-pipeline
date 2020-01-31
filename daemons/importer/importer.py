import json
import os
import socket
import socketserver
from concat_ng.tasks import into_tasks
from config import Config
from daemons.abc import JobQueueDaemon, BaseQueueExecutor


class ImportRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        _daemon = self.server.daemon
        
        try:
            sd_root = self.rfile.read().decode("utf-8").strip()
            _daemon.job_queue.put(sd_root)
        except Exception as e:
            print(f"Unhandled exception: {e}")

class ImportExecutor(BaseQueueExecutor):
    def __init__(self, job_queue, output_dir, transcoder_address):
        super(ImportExecutor, self).__init__(job_queue)
        self.output_dir = output_dir
        self.transcoder_addr = transcoder_address

    def handle_job(self, sd_root: str):
        concat_tasks = into_tasks(sd_root, self.output_dir)
        transcode_request = []
        for task in concat_tasks:
            os.makedirs(os.path.dirname(task.destination), exist_ok=True)
            transcode_request.append({
                "inputs": [[f.path for f in task.sources]],
                "outputs": [task.destination],
                "profile": Config.ff_default_profile
            })

        with socket.create_connection(self.transcoder_addr) as sock:
            with sock.makefile(mode="w") as sock_w:
                json.dump(transcode_request, sock_w)
            sock.shutdown(socket.SHUT_WR)
            with sock.makefile(mode="r") as sock_r:
                try:
                    response = json.load(sock_r)
                    print(f"Transcoder response: {response}")
                except Exception as e:
                    print(f"Unhandled exception: {e}")
