from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from pipeline_common.utils import into_tasks
from .apps import PipelineImportsConfig
from .models import ImportRequest, MediaFile, MediaFileRole, TranscodeProfile, TranscodeRequest
from .utils import guess_content


class IndexView(generic.ListView):
    template_name = 'pipeline_imports/index.html'
    context_object_name = 'latest_imports'

    def get_queryset(self):
        return ImportRequest.objects.order_by('-create_dttm')[:5]


class DetailView(generic.DetailView):
    model = ImportRequest
    template_name = 'pipeline_imports/detail.html'


class CreateView(generic.CreateView):
    model = ImportRequest
    fields = ['sdroot_path_txt']
    template_name = 'pipeline_imports/create_form.html'

    def get_success_url(self):
        return reverse_lazy('pipeline_imports:on_create', args=[self.object.id])


def on_create(request, import_id):
    imp = ImportRequest.objects.get(id=import_id)
    content_type = guess_content(imp.sdroot_path_txt)
    response = f'Content type: {content_type}'
    if content_type == 'video_sony':
        tasks = into_tasks(imp.sdroot_path_txt, PipelineImportsConfig.storage_root)
        for sources, destination in tasks:
            treq = TranscodeRequest(import_request=imp)
            treq.save()
            role_src = MediaFileRole.objects.get(role_nm='src_video_concat')
            role_res = MediaFileRole.objects.get(role_nm='result')
            for idx, source in enumerate(sources):
                src_file = MediaFile.from_videofile(transcode_request=treq, role=role_src, video_file=source, order=idx)
                src_file.save()
            res_file = MediaFile(transcode_request=treq, role=role_res, path_txt=destination)
            res_file.save()
            # response += f'<br><li><samp>{destination}</samp> &lt;-- <samp>{tasks}</samp>'
    elif content_type:
        response += ' (Import unsupported)'
    else:
        response += ' (Unknown content type)'
    return HttpResponse(response)
