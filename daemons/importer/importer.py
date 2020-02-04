import json
import os
import socket
import socketserver
from concat_ng.tasks import into_tasks
from config import Config
import daemons.abc

class ImportRequestHandler(daemons.abc.JsonRequestHandler):
    mesg_type_dispatcher = daemons.abc.HandlerDispatcher()

    def error(self, desc):
        self.response_obj["error"] = 1
        self.response_obj["error_desc"] = desc

    def validate_request(self):
        if self.request_obj is None:
            self.error("Invalid JSON")
        else:
            try:
                mesg_type = self.request_obj["message_type"]
                return self.mesg_type_dispatcher.get_handler(mesg_type)
            except KeyError:
                self.error("Invalid message type")

    def handle(self):
        handler_method = self.validate_request()
        if "error" not in self.response_obj:
            try:
                handler_method(self)
                self.response_obj["error"] = 0
            except Exception as e:
                print(f"Unhandled exception in handler {handler_method}: {type(e)}: {e}")
                self.error("Unhandled exception")

    @mesg_type_dispatcher.add_handler("import_request")
    def handle_import_request(self):
        sd_root = self.request_obj["message"]["path"]
        self.server.daemon.job_queues["q_import"].put(sd_root)
    
    @mesg_type_dispatcher.add_handler("transcode_result")
    def handle_transcode_result(self):
        output_paths = self.request_obj["message"]["outputs"]
        for path in output_paths:
            print(f"Transcode finished: {path}")
            self.server.daemon.job_queues["q_upload"].put(path)

class ImportExecutor(daemons.abc.BaseQueueExecutor):
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

class UploadExecutor(daemons.abc.BaseQueueExecutor):
    def __init__(self, job_queue, gdrive_client, remote_root_id, sources_root):
        super(UploadExecutor, self).__init__(job_queue)
        self.gdrive_client = gdrive_client
        self.remote_root_id = remote_root_id
        self.sources_root = sources_root

    def handle_job(self, local_path: str):
        local_dir = os.path.dirname(local_path)
        folder_id = self.gdrive_client.makedirs(
            local_dir, self.sources_root, self.remote_root_id, exist_ok=True
        )
        print(f'Remote folder: {folder_id}')
        self.gdrive_client.upload_files(
            [local_path], folder_id,
            on_each=lambda x: print(f"on_each {x}"),
            on_progress=lambda x: print(f"on_progress {x}")
        )
