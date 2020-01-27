import json
import os.path
import sys

class Config:
    @staticmethod
    def update(config_path):
        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
        
            Config.scopes = config['gdrive']['scopes']
            Config.root_id = config['gdrive']['root_id']
            
            secrets_path = config['secrets_path']
            Config.token_path = os.path.join(
                secrets_path, config['gdrive']['token_file']
            )
            Config.credentials_path = os.path.join(
                secrets_path, config['gdrive']['credentials_file']
            )
            
            Config.ff_general_options = config['ffmpeg']['general_options']
            Config.ff_default_profile = config['ffmpeg']['default_profile']
            Config.ff_preset_dir = config['ffmpeg']['preset_dir']
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error reading config file: {e}", file=sys.stderr)
