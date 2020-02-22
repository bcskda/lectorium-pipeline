from django.urls import include, path

from . import views

urlpatterns_imports = [
    path('', views.ImportRequestIndexView.as_view(), name='import_index'),
    path('<int:pk>/', views.ImportRequestDetailView.as_view(), name='import_detail'),
    path('<int:import_id>/approve/', views.ImportRequestApproveView.as_view(), name='import_approve'),
    path('create/', views.ImportRequestCreateView.as_view(), name='import_create'),
]

urlpatterns_mediafiles = [
    path('<int:pk>/', views.MediaFileDetailView.as_view(), name='mediafile_detail'),
]

app_name = 'pipeline_imports'
urlpatterns = [
    path('imports/', include(urlpatterns_imports)),
    path('mediafiles/', include(urlpatterns_mediafiles)),
]
