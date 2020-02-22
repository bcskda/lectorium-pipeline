from django.db import models
from .utils.probe import VideoFile


class ExportProto(models.Model):
    proto_nm = models.CharField(max_length=20)


class ExportDestination(models.Model):
    export_proto = models.ForeignKey(ExportProto, on_delete=models.CASCADE)
    destination_nm = models.CharField(max_length=50)
    destination_params_txt = models.CharField(max_length=200)


class BaseRequest(models.Model):
    create_dttm = models.DateTimeField(auto_now_add=True)
    start_dttm = models.DateTimeField(null=True)
    finish_dttm = models.DateTimeField(null=True)
    is_initialized = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_finish_confirmed = models.BooleanField(default=False)


class ImportRequest(BaseRequest):
    sdroot_path_txt = models.CharField(max_length=200)


class TranscodeProfile(models.Model):
    profile_nm = models.CharField(max_length=20)


class TranscodeRequest(BaseRequest):
    import_request = models.ForeignKey(ImportRequest, null=True, on_delete=models.SET_NULL)
    transcode_profile = models.ForeignKey(TranscodeProfile, null=True, on_delete=models.SET_NULL)


class MediaFileRole(models.Model):
    role_nm = models.CharField(max_length=20)


class MediaFile(models.Model):
    transcode_request = models.ForeignKey(TranscodeRequest, null=True, on_delete=models.SET_NULL)
    role = models.ForeignKey(MediaFileRole, null=True, on_delete=models.SET_NULL)
    path_txt = models.CharField(max_length=200)
    order_n = models.IntegerField(null=True)
    start_sec = models.FloatField(null=True)
    duration_sec = models.FloatField(null=True)
    modification_dttm = models.DateTimeField(null=True)

    @staticmethod
    def from_videofile(transcode_request: TranscodeRequest, role: MediaFileRole, video_file: VideoFile, order=None):
        media_file = MediaFile(transcode_request=transcode_request, role=role, order_n=order,
                               path_txt=video_file.path, start_sec=video_file.start, duration_sec=video_file.duration,
                               modification_dttm=video_file.modification_time)
        return media_file


class ExportRequest(BaseRequest):
    media_file = models.ForeignKey(MediaFile, null=True, on_delete=models.SET_NULL)
    export_destination = models.ForeignKey(ExportDestination, null=True, on_delete=models.SET_NULL)
    export_params_txt = models.CharField(max_length=200)
    progress_prc = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
