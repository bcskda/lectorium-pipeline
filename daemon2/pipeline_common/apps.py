from django.apps import AppConfig


class PipelineCommonConfig(AppConfig):
    name = 'pipeline_common'
    ffmpeg_path = 'D:\\Userdata\\Demul\\Soft\\ffmpeg\\bin\\ffmpeg.exe'
    ffprobe_path = 'D:\\Userdata\\Demul\\Soft\\ffmpeg\\bin\\ffprobe.exe'
