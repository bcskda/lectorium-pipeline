"""Based on https://developers.google.com/drive/api/v3/manage-uploads"""

import mimetypes
import os.path
import pickle
from collections import namedtuple
from typing import Callable
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class GDriveClient:
    def __init__(self, config):
        self.creds = GDriveClient.get_creds(config)
        self.service = build('drive', 'v3', credentials=self.creds)
    
    @staticmethod
    def get_creds(config):
        creds = None

        if os.path.exists(config.token_path):
            with open(config.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.credentials_path, config.scopes
                )
                creds = flow.run_console()
            
            with open(config.token_path, 'wb') as token_file:
                pickle.dump(creds, token_file)
        
        return creds
    
    RemoteNode = namedtuple('RemoteNode', ('name',  'parent'))
    
    def upload_file(self, local_path, remote: RemoteNode, on_progress: Callable = None):
        mimetype = mimetypes.guess_type(local_path)[0]
        media = MediaFileUpload(
            local_path,
            mimetype=mimetype,
            resumable=True
        )
        
        try:
            request = self.service.files().create(
                body={'name': remote.name, 'parents': [remote.parent]},
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and on_progress:
                    on_progress(status)
            return response
        
        except Exception as e:
            print(f"Exception during upload: {e}")

    def upload_files(self, local_paths, remote_folder, on_each = None, on_progress = None):
        for path in local_paths:
            name = os.path.basename(path)
            self.upload_file(path, GDriveClient.RemoteNode(name, remote_folder), on_progress)
            on_each(path)
