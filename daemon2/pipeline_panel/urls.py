from django.urls import include, path

from . import views
from .imports.urls import urlpatterns as urlpatterns_imports

urlpatterns = [
    path('', views.index, name='index'),
    path('imports/', include(urlpatterns_imports)),
]
