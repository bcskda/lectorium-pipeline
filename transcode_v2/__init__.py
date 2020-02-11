import json
import logging
import os
import subprocess
import sys
from typing import Dict
from config import Config
from transcode_v2.protocols import apply_protocol

class TranscodeError(Exception):
    pass

def get_preset(profile) -> Dict:
    preset_path = os.path.join(Config.ff_preset_dir, f"{profile}.json")
    try:
        with open(preset_path, "r") as preset_file:
            return json.load(preset_file)
    except FileNotFoundError as e:
        raise TranscodeError(f"Bad profile: {profile}") from e

def make_cmdline(inputs, outputs, profile_name):
    profile = get_preset(profile_name)
    
    cmdline = ["ffmpeg"]
    cmdline.extend(Config.ff_general_options)
    
    for source, options in zip(inputs, profile["inputs"]):
        if "proto" in options:
            source = apply_protocol(options["proto"], source)
        cmdline.extend(["-i", source])
    
    if profile.get("filtergraph"):
        cmdline.extend(["-filter_complex", profile["filtergraph"]])
    
    for sink, options in zip(outputs, profile["outputs"]):
        for input_node in options["input_nodes"]:
            cmdline.extend(["-map", input_node])
        cmdline.extend(options["codec_options"])
        cmdline.append(sink)
    
    return cmdline

def transcode(profile, inputs, outputs, stderr=None) -> int:
    cmdline = make_cmdline(inputs, outputs, profile)
    logging.debug("cmdline = %s", cmdline)
    result = subprocess.run(cmdline, stderr=stderr)
    return result.returncode

def validate_args(inputs, outputs, profile_name):
    profile = get_preset(profile_name)
    if len(inputs) != len(profile["inputs"]):
        raise TranscodeError("Expected {} inputs, got {}".format(len(profile["inputs"]), len(inputs)))
    if len(outputs) != len(profile["outputs"]):
        raise TranscodeError("Expected {} outputs, got {}".format(len(profile["outputs"]), len(outputs)))
