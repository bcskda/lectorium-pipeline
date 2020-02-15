from django.db import models

# Create your models here.

class ImportRequest(models.Model):
    sdroot_path = models.CharField(max_length=200)
    start_dttm = models.DateTimeField()
    finish_dttm = models.DateTimeField()

class TranscodeRequest(models.Model):
    import_request = models.ForeignKey(ImportRequest, on_delete=models.SET_NULL)
