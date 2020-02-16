from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(ExportProto)
admin.site.register(ExportDestination)
admin.site.register(ImportRequest)
admin.site.register(TranscodeProfile)
admin.site.register(TranscodeRequest)
admin.site.register(MediaFileRole)
admin.site.register(MediaFile)
admin.site.register(ExportRequest)
