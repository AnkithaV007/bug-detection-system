"""Django admin configuration.

Users and groups are already registered by django.contrib.auth, so an
admin can manage accounts out of the box. Here we register our two
models and make them comfortable to work with.
"""

from django.contrib import admin

from .models import Comment, Issue


class CommentInline(admin.TabularInline):
    """Read and add comments from inside the issue page."""

    model = Comment
    extra = 1
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = (
        "issue_id",
        "title",
        "priority",
        "status",
        "reporter",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "priority", "assigned_to", "created_at")
    list_editable = ("priority", "status", "assigned_to")
    search_fields = ("issue_id", "title", "description", "steps_to_reproduce")
    readonly_fields = ("issue_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = [CommentInline]
    fieldsets = (
        ("Bug report", {"fields": ("issue_id", "title", "description", "steps_to_reproduce")}),
        ("Triage", {"fields": ("priority", "status", "reporter", "assigned_to")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("issue", "author", "short_body", "created_at")
    list_filter = ("created_at", "author")
    search_fields = ("body", "issue__issue_id", "issue__title")
    readonly_fields = ("created_at",)

    @admin.display(description="comment")
    def short_body(self, obj):
        return obj.body[:60] + ("..." if len(obj.body) > 60 else "")


# Small branding touches for the admin site.
admin.site.site_header = "BugResolutionPortal administration"
admin.site.site_title = "BugResolutionPortal"
admin.site.index_title = "Manage users, issues and comments"
