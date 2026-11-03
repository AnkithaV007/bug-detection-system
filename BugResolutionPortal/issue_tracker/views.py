"""Views for the bug tracking system.

Every view is protected by @login_required, so an anonymous visitor can
only ever reach the login page. Assigning a developer additionally needs
@staff_required (see decorators.py).
"""

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from openai import OpenAI

from .decorators import staff_required
from .forms import (
    CommentForm,
    IssueAssignForm,
    IssueForm,
    IssueStatusForm,
    RegistrationForm,
)
from .models import Issue


def _issue_payload(issue):
    return {
        "id": issue.pk,
        "issue_id": issue.issue_id,
        "title": issue.title,
        "priority": issue.priority,
        "priority_label": issue.get_priority_display(),
        "status": issue.status,
        "status_label": issue.get_status_display(),
        "reporter": issue.reporter.username,
        "assigned_to": issue.assigned_to.username if issue.assigned_to else None,
        "created_at": issue.created_at.isoformat(),
    }


def dashboard_api(request):
    """Return dashboard data for the React frontend."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    issues = Issue.objects.select_related("reporter", "assigned_to")
    return JsonResponse(
        {
            "stats": {
                "open": issues.filter(status=Issue.STATUS_OPEN).count(),
                "in_progress": issues.filter(status=Issue.STATUS_IN_PROGRESS).count(),
                "resolved": issues.filter(status=Issue.STATUS_RESOLVED).count(),
                "critical": issues.filter(priority=Issue.PRIORITY_CRITICAL)
                .exclude(status=Issue.STATUS_CLOSED)
                .count(),
                "total": issues.count(),
            },
            "recent_issues": [_issue_payload(issue) for issue in issues[:8]],
            "my_issues": [
                _issue_payload(issue)
                for issue in issues.filter(assigned_to=request.user)
                .exclude(status=Issue.STATUS_CLOSED)[:8]
            ],
        }
    )


def natural_language_issue_search(request):
    """Translate a natural-language query into safe, read-only ORM filters."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"error": "A query is required."}, status=400)
    if not settings.OPENAI_API_KEY:
        return JsonResponse(
            {"error": "Natural-language search is not configured. Set OPENAI_API_KEY."},
            status=503,
        )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Convert the user's bug search request to JSON only. "
                    "Allowed keys: text, status, priority. status must be one of "
                    "OPEN, IN_PROGRESS, RESOLVED, CLOSED; priority must be one of "
                    "LOW, MEDIUM, HIGH, CRITICAL. Use null for unused filters."
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    try:
        filters = json.loads(response.output_text)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("The LLM returned an invalid search filter.") from exc

    allowed_statuses = {value for value, _ in Issue.STATUS_CHOICES}
    allowed_priorities = {value for value, _ in Issue.PRIORITY_CHOICES}
    issues = Issue.objects.select_related("reporter", "assigned_to")
    text = filters.get("text")
    if text:
        issues = issues.filter(
            Q(title__icontains=text)
            | Q(description__icontains=text)
            | Q(issue_id__icontains=text)
        )
    if filters.get("status") in allowed_statuses:
        issues = issues.filter(status=filters["status"])
    if filters.get("priority") in allowed_priorities:
        issues = issues.filter(priority=filters["priority"])

    return JsonResponse(
        {"query": query, "filters": filters, "issues": [_issue_payload(issue) for issue in issues[:50]]}
    )


def register(request):
    """Create a normal user account and send the user to the login page."""
    if request.user.is_authenticated:
        return redirect("issue_tracker:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. You can now sign in.")
            return redirect("login")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    """Landing page: counters plus the five newest bugs."""
    issues = Issue.objects.all()

    context = {
        "open_count": issues.filter(status=Issue.STATUS_OPEN).count(),
        "in_progress_count": issues.filter(status=Issue.STATUS_IN_PROGRESS).count(),
        "resolved_count": issues.filter(status=Issue.STATUS_RESOLVED).count(),
        "critical_count": issues.filter(priority=Issue.PRIORITY_CRITICAL)
        .exclude(status=Issue.STATUS_CLOSED)
        .count(),
        "total_count": issues.count(),
        "recent_issues": issues.select_related("reporter", "assigned_to")[:5],
        "my_issues": issues.filter(assigned_to=request.user).exclude(
            status=Issue.STATUS_CLOSED
        )[:5],
    }
    return render(request, "issue_tracker/dashboard.html", context)


@login_required
def issue_list(request):
    """All issues, with a keyword search and status / priority filters."""
    issues = Issue.objects.select_related("reporter", "assigned_to")

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")

    if query:
        issues = issues.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(issue_id__icontains=query)
        )
    if status:
        issues = issues.filter(status=status)
    if priority:
        issues = issues.filter(priority=priority)

    context = {
        "issues": issues,
        "query": query,
        "selected_status": status,
        "selected_priority": priority,
        "status_choices": Issue.STATUS_CHOICES,
        "priority_choices": Issue.PRIORITY_CHOICES,
    }
    return render(request, "issue_tracker/issue_list.html", context)


@login_required
def issue_create(request):
    """Report a new bug. Open to every logged in user, not just staff."""
    if request.method == "POST":
        form = IssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.reporter = request.user
            issue.save()
            messages.success(request, f"Reported {issue.issue_id}.")
            return redirect(issue.get_absolute_url())
    else:
        form = IssueForm()

    return render(request, "issue_tracker/issue_form.html", {"form": form})


@login_required
def issue_detail(request, pk):
    """Everything about one bug, plus the forms that act on it."""
    issue = get_object_or_404(
        Issue.objects.select_related("reporter", "assigned_to"), pk=pk
    )

    context = {
        "issue": issue,
        "comments": issue.comments.select_related("author"),
        "status_form": IssueStatusForm(instance=issue),
        "assign_form": IssueAssignForm(instance=issue),
        "comment_form": CommentForm(),
    }
    return render(request, "issue_tracker/issue_detail.html", context)


@login_required
def issue_update_status(request, pk):
    """Move an issue between Open / In Progress / Resolved / Closed."""
    issue = get_object_or_404(Issue, pk=pk)

    if request.method == "POST":
        form = IssueStatusForm(request.POST, instance=issue)
        if form.is_valid():
            form.save()
            messages.success(request, f"Status updated to {issue.get_status_display()}.")
        else:
            messages.error(request, "That status is not valid.")

    return redirect(issue.get_absolute_url())


@staff_required
def issue_assign(request, pk):
    """Assign a developer. Staff only - this is the decorator in action."""
    issue = get_object_or_404(Issue, pk=pk)

    if request.method == "POST":
        form = IssueAssignForm(request.POST, instance=issue)
        if form.is_valid():
            form.save()
            if issue.assigned_to:
                messages.success(request, f"Assigned to {issue.assigned_to.username}.")
            else:
                messages.success(request, "Assignment cleared.")
        else:
            messages.error(request, "Could not assign that user.")

    return redirect(issue.get_absolute_url())


@login_required
def comment_create(request, pk):
    """Attach a debugging note or fix update to an issue."""
    issue = get_object_or_404(Issue, pk=pk)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.issue = issue
            comment.author = request.user
            comment.save()
            messages.success(request, "Comment added.")
        else:
            messages.error(request, "Write something before posting a comment.")

    return redirect(issue.get_absolute_url())
