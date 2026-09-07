from django.urls import path
from .views import ManifestView, SyncView

urlpatterns = [
    path("manifest/", ManifestView.as_view()),
    path("sync/", SyncView.as_view()),
]