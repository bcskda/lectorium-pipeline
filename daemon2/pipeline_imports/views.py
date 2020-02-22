from django.urls import reverse_lazy
from django.views import generic
from .models import ImportRequest


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
    success_url = reverse_lazy('pipeline_imports:index')
    template_name = 'pipeline_imports/create_form.html'
