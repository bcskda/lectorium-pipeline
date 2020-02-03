"""Based on https://developers.google.com/drive/api/v3/manage-uploads"""

import mimetypes
import os.path
import pathlib
import pickle
from collections import namedtuple
from typing import Callable
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


GDRIVE_MIMETYPES = {
    'folder': 'application/vnd.google-apps.folder'
}

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
            print(f'Exception during upload: {e}')

    def upload_files(self, local_paths, remote_folder, on_each = None, on_progress = None):
        for path in local_paths:
            name = os.path.basename(path)
            self.upload_file(path, GDriveClient.RemoteNode(name, remote_folder), on_progress)
            on_each(path)

    def mkdir(self, name: str, parent_id: str) -> str:
        """Implies exist_ok=True. Return value: folder id."""
        metadata = {
            'name': name,
            'parents': [parent_id],
            'mimeType': GDRIVE_MIMETYPES['folder']
        }
        request = self.service.files().create(body=metadata, fields='id')
        folder = request.execute()
        return folder.get('id')

    def makedirs(self, path: str, local_root: str, remote_root_id: str) -> str:
        """Implies exist_ok=True. Return value: folder id."""
        path_r, local_root_r = map(os.path.realpath, (path, local_root))
        common = os.path.commonpath((path_r, local_root_r))
        if not os.path.samefile(common, local_root):
            raise ValueError('path outside local_root')
        
        rel = os.path.relpath(path, start=local_root)
        parts = pathlib.PurePath(rel).parts
        parent = remote_root_id
        for dirname in parts:
            parent = self.mkdir(dirname, parent)
        return parent

if __name__ == '__main__':
    from config import Config
    Config.update('config.json')
    client = GDriveClient(Config)
    
    remote_root_id = client.mkdir('pipeline_test_root', 'root')
    print(f'root: {remote_root_id}')
    local_root = 'input_dir'
    
    subdir_id = client.makedirs(
        './input_dir/PRIVATE/AVCHD/BDMV/STREAM/', local_root, remote_root_id
    )
    print(f'subdir: {subdir_id}')
    
    try:
        path = 'input_dir/../../../../../etc/passwd'
        other_subdir_id = client.makedirs(path, local_root, remote_root_id)
    except ValueError as e:
        print(f'makedirs{(path, local_root, remote_root_id)} raised exception: {e}')
    else:
        raise RuntimeError('Should raise')
