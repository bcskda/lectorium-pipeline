from django import forms
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import generic
from pipeline_common.utils import into_tasks
from .apps import PipelineImportsConfig
from .models import ImportRequest, MediaFile, MediaFileRole, TranscodeRequest
from .utils import guess_content

# ImportRequest


class ImportRequestIndexView(generic.ListView):
    template_name = 'pipeline_imports/index.html'
    context_object_name = 'latest_imports'

    def get_queryset(self):
        return ImportRequest.objects.order_by('-create_dttm')[:5]


class ImportRequestDetailView(generic.DetailView):
    model = ImportRequest


class ImportRequestCreateView(generic.CreateView):
    model = ImportRequest
    fields = ['sdroot_path_txt']

    def get_success_url(self):
        self.on_create()
        return reverse_lazy('pipeline_imports:import_approve', args=[self.object.id])

    def on_create(self):
        imp = ImportRequest.objects.get(id=self.object.id)
        content_type = guess_content(imp.sdroot_path_txt)
        response = f'Content type: {content_type}'
        if content_type != 'video_sony':
            return
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


class TranscodeRequestMultipleChoiseField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if isinstance(obj, TranscodeRequest):
            # Pls fix this
            return render_to_string('pipeline_common/TranscodeRequest_detail.html',
                                    {'transcoderequest': obj})
        else:
            super().label_from_instance(obj)


class ImportRequestApproveForm(forms.Form):
    def __init__(self, *args, **kwargs):
        import_id = kwargs.pop('import_id')
        super().__init__(*args, **kwargs)
        # Select related transcode requests:
        transcoderequest_set = TranscodeRequest.objects.filter(import_request_id=import_id)
        self.fields['approved_ids'] = TranscodeRequestMultipleChoiseField(queryset=transcoderequest_set,
                                                                          widget=forms.CheckboxSelectMultiple)


class ImportRequestApproveView(generic.edit.FormView):
    form_class = ImportRequestApproveForm
    fields = ['approved_ids']
    template_name = 'pipeline_imports/ImportRequestApprove_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['import_id'] = self.kwargs['import_id']
        return kwargs

# TranscodeRequest


class TranscodeRequestApproveForm(forms.ModelForm):
    model = TranscodeRequest
    fields = ['transcode_profile', 'is_approved']


def transcoderequest_on_create(import_id):
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


# MediaFile


class MediaFileDetailView(generic.DetailView):
    model = MediaFile

