import json
import logging
import os
import socket
import socketserver
from concat_ng.tasks import into_tasks
from config import Config
import daemons.abc

class ImportRequestHandler(daemons.abc.DispatchedRequestHandler):
    mesg_dispatcher = daemons.abc.DispatchedRequestHandler.mesg_dispatcher

    @mesg_dispatcher.add_handler("import_request")
    def handle_import_request(self):
        sd_root = self.request_obj["message"]["path"]
        self.server.daemon.job_queues["q_import"].put(sd_root)

    @mesg_dispatcher.add_handler("transcode_result")
    def handle_transcode_result(self):
        base = self.request_obj["message"]["output_base"]
        outputs = self.request_obj["message"]["outputs"]
        logging.info("Transcode finished: %s", base)
        self.server.daemon.job_queues["q_upload"].put((base, outputs))

class ImportExecutor(daemons.abc.BaseQueueExecutor):
    def __init__(self, job_queue, output_dir, transcoder_address, daemon):
        super(ImportExecutor, self).__init__(job_queue)
        self.output_dir = output_dir
        self.transcoder_addr = transcoder_address
        self.active_imports = daemon.active_imports
        self.active_transcodes = daemon.active_transcodes

    def handle_job(self, sd_root: str):
        concat_tasks = into_tasks(sd_root, self.output_dir)
        if sd_root in self.active_imports:
            raise KeyError(f"import already in progress: from={sd_root}")
        self.active_imports[sd_root] = 0
        transcode_request = []
        for task in concat_tasks:
            old_from = self.active_transcodes.get(task.destination)
            if old_from:
                logging.warning(
                    "transcode already in progress: from=%s old_from=%s output_file=%s",
                    sd_root, old_from, task.destination)
                continue
            self.active_transcodes[task.destination] = sd_root
            self.active_imports[sd_root] += 1
            os.makedirs(os.path.dirname(task.destination), exist_ok=True)
            transcode_request.append({
                "inputs": [[f.path for f in task.sources]],
                "output": task.destination,
                "profile": Config.ff_default_profile
            })
        self._send_transcode_request(transcode_request)

    def _send_transcode_request(self, transcode_request):
        with socket.create_connection(self.transcoder_addr) as sock:
            with sock.makefile(mode="w") as sock_w:
                json.dump(transcode_request, sock_w)
            sock.shutdown(socket.SHUT_WR)
            with sock.makefile(mode="r") as sock_r:
                response = json.load(sock_r)

class UploadExecutor(daemons.abc.BaseQueueExecutor):
    def __init__(self, job_queue, gdrive_client, remote_root_id, sources_root, report_addr, daemon):
        super(UploadExecutor, self).__init__(job_queue)
        self.gdrive_client = gdrive_client
        self.remote_root_id = remote_root_id
        self.sources_root = sources_root
        self.report_addr = report_addr
        self.active_imports = daemon.active_imports
        self.active_transcodes = daemon.active_transcodes

    def handle_job(self, job):
        base_path, outputs = job
        local_dir = os.path.dirname(base_path)
        folder_id = self.gdrive_client.makedirs(
            local_dir, self.sources_root, self.remote_root_id, exist_ok=True
        )
        logging.info('upload: local=%s remote=%s', base_path, folder_id)
        self.gdrive_client.upload_files(
            outputs, folder_id,
            on_each=lambda path: logging.info("upload finished: local=%s", path),
            on_progress=lambda progress: logging.info("upload progress: %s%%", 100 * progress.progress())
        )
        self._unregister_transcode_job(base_path)

    def _unregister_transcode_job(self, base_path):
        sd_root = self.active_transcodes.pop(base_path)
        if self.active_imports[sd_root] == 1:
            del self.active_imports[sd_root]
            self._report_import_finish(sd_root)
        else:
            self.active_imports[sd_root] -= 1
        print('! ' + f'active_transcodes: {self.active_transcodes}')
        print('! ' + f'active_imports: {self.active_imports}')
    
    def _report_import_finish(self, sd_root):
        message = {
            "message_type": "import_result",
            "message": {"path": sd_root}
        }
        with socket.create_connection(self.report_addr) as sock:
            with sock.makefile("w") as sock_w:
                json.dump(message, sock_w)
            sock.shutdown(socket.SHUT_WR)
            with sock.makefile("r") as sock_r:
                ans = json.load(sock_r)
            logging.info("Devwatch response: %s", ans)
