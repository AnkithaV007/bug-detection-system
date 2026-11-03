"""URL patterns for the issue tracker app."""

from django.urls import path

from . import views

app_name = "issue_tracker"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/issues/query/", views.natural_language_issue_search, name="natural_language_issue_search"),
    path("", views.dashboard, name="dashboard"),
    path("issues/", views.issue_list, name="issue_list"),
    path("issues/new/", views.issue_create, name="issue_create"),
    path("issues/<int:pk>/", views.issue_detail, name="issue_detail"),
    path("issues/<int:pk>/status/", views.issue_update_status, name="issue_update_status"),
    path("issues/<int:pk>/assign/", views.issue_assign, name="issue_assign"),
    path("issues/<int:pk>/comment/", views.comment_create, name="comment_create"),
]
