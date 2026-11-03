"""Database models for the bug tracking system.

Two models only:
    Issue   - one reported bug
    Comment - a debugging note / progress update attached to an issue
"""

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class Issue(models.Model):
    """A single bug report."""

    # ----- choices -------------------------------------------------------
    PRIORITY_LOW = "LOW"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_CRITICAL = "CRITICAL"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_CRITICAL, "Critical"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]

    # ----- fields --------------------------------------------------------
    issue_id = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
        blank=True,
        help_text="Auto generated reference such as BUG-0001.",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="What is wrong and where does it happen?")
    steps_to_reproduce = models.TextField(
        blank=True,
        help_text="Numbered steps another person can follow to see the bug.",
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reported_issues",
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assigned_issues",
        null=True,
        blank=True,
        verbose_name="assigned developer",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.issue_id} - {self.title}"

    def save(self, *args, **kwargs):
        """Save normally, then fill in the human friendly issue id once."""
        super().save(*args, **kwargs)
        if not self.issue_id:
            self.issue_id = f"BUG-{self.pk:04d}"
            super().save(update_fields=["issue_id"])

    def get_absolute_url(self):
        return reverse("issue_tracker:issue_detail", args=[self.pk])

    # ----- small helpers used by the templates ---------------------------
    @property
    def status_css_class(self):
        """CSS modifier name for the status badge."""
        return "badge--" + self.status.lower().replace("_", "-")

    @property
    def priority_css_class(self):
        """CSS modifier name for the priority badge."""
        return "badge--" + self.priority.lower()

    @property
    def is_open(self):
        return self.status == self.STATUS_OPEN


class Comment(models.Model):
    """A note added to an issue: debugging findings, fix progress, questions."""

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body = models.TextField(verbose_name="comment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.issue.issue_id}"
