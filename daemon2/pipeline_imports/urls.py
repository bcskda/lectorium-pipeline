from django.urls import path

from . import views

app_name = 'pipeline_imports'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<int:pk>/', views.DetailView.as_view(), name='detail'),
    path('<int:import_id>/on_create/', views.on_create, name='on_create'),
    path('create/', views.CreateView.as_view(), name='create'),
]
