import json
import os
import subprocess
import sys
from typing import Dict
from config import Config
from transcode_protocols import apply_protocol

def get_preset(profile) -> Dict:
    preset_path = os.path.join(Config.ff_preset_dir, f"{profile}.json")
    with open(preset_path, 'r') as preset_file:
        return json.load(preset_file)

def make_cmdline(in_urls, out_url, profile):
    preset = get_preset(profile)
    if 'input_protocol' in preset:
        in_urls = apply_protocol(preset['input_protocol'], in_urls)
    
    cmdline = ['ffmpeg']
    cmdline.extend(Config.ff_general_options)
    for url in in_urls:
        cmdline.extend(['-i', url])
    cmdline.extend(preset['options'])
    cmdline.append(out_url)
    
    return cmdline

def transcode(profile, in_urls, out_url, stderr = None) -> int:
    cmdline = make_cmdline(in_urls, out_url, profile)
    print(f'cmdline = {cmdline}', file=sys.stderr)
    result = subprocess.run(cmdline, stderr=stderr)
    return result.returncode
