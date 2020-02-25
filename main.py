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
        self.files = files
        self.index = 0
        self.next_file()
    
    def next_file(self):
        print("Uploading {}".format(self.files[self.index]))
        self.bar = progressbar.ProgressBar(widgets=[progressbar.Percentage()], max_value=100.0).start()
        self.bar.update(0)
    
    def on_progress(self, upload_progress):
        self.bar.update(int(100 * upload_progress.progress()))
    
    def on_each(self, finished_file):
        self.bar.finish()
        print(f"Upload finished: {finished_file}")
        self.index += 1
        if self.index < len(self.files):
            self.next_file()

def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_cmdline()
    Config.update(args.config)

    transcoder = functools.partial(transcode, args.profile or Config.ff_default_profile, stderr=sys.stderr)
    outputs = concat_ng.tasks.execute_from(args, transcoder)
    
    if args.upload:
        gdrive_client = GDriveClient(Config)
        parent = args.gdrive_parent or Config.root_id
        
        progress_sentry = GDriveProgressSentry(outputs)
        gdrive_client.upload_files(outputs, parent,
            on_progress=progress_sentry.on_progress,
            on_each=progress_sentry.on_each
        )

if __name__ == "__main__":
    main()
