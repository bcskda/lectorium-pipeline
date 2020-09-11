"""Credits: Lectorium team 2018-2019"""

import argparse
import functools
import logging
import os.path
import sys
import progressbar
import concat_ng.tasks
from config import Config
from transcode_v2 import transcode
from gdrive_client import GDriveClient

def parse_cmdline():
    parser = argparse.ArgumentParser(description="Merge raw Sony AVCHD videos to lectorium folder")
    parser.add_argument("-i", "--input", required=True, help="Path to sd card root")
    parser.add_argument("-o", "--output", required=True, help="Path to lectorium folder root")
    parser.add_argument("-p", "--profile", required=False, help="Trancoding profile to use")
    parser.add_argument("-c", "--config", required=False, default="config_default.json", help="Path to configuration")
    parser.add_argument("-u", "--upload", required=False, action='store_true', help="Upload output to Google Drive")
    parser.add_argument("--folder-id", required=False, dest="gdrive_parent", help="ID of Google Drive destination folder")
    
    return parser.parse_args()

class GDriveProgressSentry:
    def __init__(self, files):
        self.files = functools.reduce(lambda flat, x: flat + x, files.values())
        self.index = 0
        self.next_file()
    
    def next_file(self):
        logging.info("Uploading {}".format(self.files[self.index]))
        self.bar = progressbar.ProgressBar(widgets=[progressbar.Percentage()], max_value=100.0).start()
        self.bar.update(0)
    
    def on_progress(self, upload_progress):
        self.bar.update(int(100 * upload_progress.progress()))
    
    def on_each(self, finished_file):
        self.bar.finish()
        logging.info(f"Upload finished: {finished_file}")
        self.index += 1
        if self.index < len(self.files):
            self.next_file()

class Uploader:
    def __init__(self, cmdline):
        self.gdrive_client = GDriveClient(Config)
        root_id = args.gdrive_parent or Config.root_id

    def upload(self, outputs: Dict[str, List[str]]):
        progress_sentry = GDriveProgressSentry(outputs)
        for group_label, entries in outputs.items():
            local_dir = os.path.dirname(group_label)
            folder_id = self.gdrive_client.makedirs(
                local_dir, args.output, root_id, exist_ok=True
            )
            self.gdrive_client.upload_files(entries, folder_id,
                on_progress=progress_sentry.on_progress,
                on_each=progress_sentry.on_each
            )

def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_cmdline()
    Config.update(args.config)

    transcoder = functools.partial(transcode, args.profile or Config.ff_default_profile, stderr=sys.stderr)
    outputs = concat_ng.tasks.execute_from_v2(args, transcoder)
    if args.upload:
        uploader = Uploader(args)
        uploader.upload(outputs)

if __name__ == "__main__":
    main()
