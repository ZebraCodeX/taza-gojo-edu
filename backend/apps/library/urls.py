from django.urls import path

from . import views

urlpatterns = [
    path("materials/", views.MaterialListView.as_view(), name="library-list"),
    path("materials/<int:id>/", views.MaterialDetailView.as_view(), name="library-detail"),
    path("materials/<int:id>/download/", views.MaterialDownloadView.as_view(), name="library-download"),
]