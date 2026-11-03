"""Forms used by the issue tracker."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Comment, Issue


class RegistrationForm(UserCreationForm):
    """Create a standard user account without staff privileges."""

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class IssueForm(forms.ModelForm):
    """Used on the 'Report an issue' page. Any logged in user may use this."""

    class Meta:
        model = Issue
        fields = ["title", "description", "steps_to_reproduce", "priority"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Short summary, e.g. Login button does nothing"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "What happened, what you expected, and where.",
                }
            ),
            "steps_to_reproduce": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "1. Open the login page\n2. Enter a valid password\n3. Click Sign in",
                }
            ),
        }


class IssueStatusForm(forms.ModelForm):
    """Small form on the detail page for moving an issue along."""

    class Meta:
        model = Issue
        fields = ["status"]


class IssueAssignForm(forms.ModelForm):
    """Assign a developer. Only staff members see this form."""

    class Meta:
        model = Issue
        fields = ["assigned_to"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            is_active=True
        ).order_by("username")
        self.fields["assigned_to"].empty_label = "Nobody yet"


class CommentForm(forms.ModelForm):
    """Add a debugging note or a progress update."""

    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Add a debugging note or fix update...",
                }
            ),
        }
        labels = {"body": ""}
