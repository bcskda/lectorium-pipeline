import json
import socketserver
import threading
from queue import Queue
from config import Config
from transcode_v2 import validate_args, TranscodeError
from daemons.transcoder.transcoder_thread import TranscodeJob, transcoder_loop


class Server(socketserver.TCPServer):
    def __init__(self, transcode_queue, *args, **kwargs):
        super(Server, self).__init__(*args, **kwargs)
        self.transcode_queue = transcode_queue

class RequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
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
                    self.server.transcode_queue.put(TranscodeJob(job))
                    response["result"]["accept"].append(idx)
                except TranscodeError as e:
                    response["result"]["discard"].append({"index": idx, "desc": f"{e}"})

        except Exception as e:
            response["error"] = 1
            response["error_desc"] = f"Unhandled exception: {e}"
        finally:
            self.wfile.write(json.dumps(response).encode("utf-8"))

def main(server_address):
    transcode_queue = Queue()

    worker = threading.Thread(group=None, target=transcoder_loop, args=(transcode_queue,))
    worker.start()
    
    with Server(transcode_queue, server_address, RequestHandler) as server:
        server.serve_forever()
        # TODO graceful shutdown by signal

if __name__ == '__main__':
    Config.update("config.json")
    main(('127.0.0.1', 1337))
