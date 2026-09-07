from django.urls import path

from . import views

urlpatterns = [
    path("stats/", views.StatsView.as_view(), name="admin-stats"),
    path("materials/", views.MaterialListView.as_view(), name="admin-materials"),
    path("materials/<int:pk>/", views.MaterialDetailView.as_view(), name="admin-material-detail"),
    path("users/", views.UserListView.as_view(), name="admin-users"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="admin-user-detail"),
]