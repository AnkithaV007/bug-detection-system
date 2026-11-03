"""Tests for the issue tracker.

Run them with:  python manage.py test
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Comment, Issue


class IssueModelTests(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user("tester", password="pass12345")

    def test_issue_id_is_generated_automatically(self):
        issue = Issue.objects.create(
            title="Save button does nothing",
            description="Clicking Save has no effect.",
            reporter=self.reporter,
        )
        self.assertEqual(issue.issue_id, f"BUG-{issue.pk:04d}")

    def test_defaults_are_open_and_medium(self):
        issue = Issue.objects.create(
            title="Typo on the dashboard",
            description="'Resloved' should read 'Resolved'.",
            reporter=self.reporter,
        )
        self.assertEqual(issue.status, Issue.STATUS_OPEN)
        self.assertEqual(issue.priority, Issue.PRIORITY_MEDIUM)
        self.assertIn(issue.title, str(issue))


class AuthenticationTests(TestCase):
    def test_dashboard_api_returns_json_401_for_anonymous_visitor(self):
        response = self.client.get(reverse("issue_tracker:dashboard_api"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Authentication required."})

    def test_anonymous_visitor_can_open_registration_page(self):
        response = self.client.get(reverse("issue_tracker:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_registration_creates_standard_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse("issue_tracker:register"),
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@example.com",
                "password1": "A-strong-password-123",
                "password2": "A-strong-password-123",
            },
        )
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="newuser")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(self.client.login(username="newuser", password="A-strong-password-123"))

    def test_authenticated_user_is_redirected_from_registration(self):
        user = User.objects.create_user("tester", password="tester-pass-123")
        self.client.force_login(user)
        response = self.client.get(reverse("issue_tracker:register"))
        self.assertRedirects(response, reverse("issue_tracker:dashboard"))

    def test_dashboard_redirects_anonymous_visitor_to_login(self):
        response = self.client.get(reverse("issue_tracker:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_issue_list_redirects_anonymous_visitor_to_login(self):
        response = self.client.get(reverse("issue_tracker:issue_list"))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_open_the_dashboard(self):
        User.objects.create_user("tester", password="pass12345")
        self.client.login(username="tester", password="pass12345")
        response = self.client.get(reverse("issue_tracker:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")


class IssueViewTests(TestCase):
    def setUp(self):
        self.tester = User.objects.create_user("tester", password="pass12345")
        self.developer = User.objects.create_user(
            "developer", password="pass12345", is_staff=True
        )
        self.open_issue = Issue.objects.create(
            title="Login button is unresponsive",
            description="Nothing happens on click.",
            priority=Issue.PRIORITY_CRITICAL,
            reporter=self.tester,
        )
        self.done_issue = Issue.objects.create(
            title="Footer year is wrong",
            description="Shows last year.",
            priority=Issue.PRIORITY_LOW,
            status=Issue.STATUS_RESOLVED,
            reporter=self.tester,
        )

    def test_normal_user_can_report_an_issue(self):
        self.client.login(username="tester", password="pass12345")
        response = self.client.post(
            reverse("issue_tracker:issue_create"),
            {
                "title": "Search returns duplicates",
                "description": "Each result appears twice.",
                "steps_to_reproduce": "1. Search for anything",
                "priority": Issue.PRIORITY_HIGH,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_issue = Issue.objects.get(title="Search returns duplicates")
        self.assertEqual(new_issue.reporter, self.tester)
        self.assertEqual(new_issue.status, Issue.STATUS_OPEN)

    def test_status_filter_narrows_the_list(self):
        self.client.login(username="tester", password="pass12345")
        response = self.client.get(
            reverse("issue_tracker:issue_list"), {"status": Issue.STATUS_RESOLVED}
        )
        self.assertEqual(response.status_code, 200)
        titles = [issue.title for issue in response.context["issues"]]
        self.assertEqual(titles, ["Footer year is wrong"])

    def test_search_matches_the_issue_reference(self):
        self.client.login(username="tester", password="pass12345")
        response = self.client.get(
            reverse("issue_tracker:issue_list"), {"q": self.open_issue.issue_id}
        )
        self.assertEqual(len(response.context["issues"]), 1)

    def test_dashboard_counts_are_correct(self):
        self.client.login(username="tester", password="pass12345")
        response = self.client.get(reverse("issue_tracker:dashboard"))
        self.assertEqual(response.context["open_count"], 1)
        self.assertEqual(response.context["resolved_count"], 1)
        self.assertEqual(response.context["critical_count"], 1)

    def test_any_user_can_update_the_status(self):
        self.client.login(username="tester", password="pass12345")
        self.client.post(
            reverse("issue_tracker:issue_update_status", args=[self.open_issue.pk]),
            {"status": Issue.STATUS_IN_PROGRESS},
        )
        self.open_issue.refresh_from_db()
        self.assertEqual(self.open_issue.status, Issue.STATUS_IN_PROGRESS)

    def test_comment_is_saved_with_the_logged_in_author(self):
        self.client.login(username="tester", password="pass12345")
        self.client.post(
            reverse("issue_tracker:comment_create", args=[self.open_issue.pk]),
            {"body": "Also happens on mobile."},
        )
        comment = Comment.objects.get(issue=self.open_issue)
        self.assertEqual(comment.author, self.tester)


class StaffDecoratorTests(TestCase):
    def setUp(self):
        self.tester = User.objects.create_user("tester", password="pass12345")
        self.developer = User.objects.create_user(
            "developer", password="pass12345", is_staff=True
        )
        self.issue = Issue.objects.create(
            title="Cache is never cleared",
            description="Old data keeps showing.",
            reporter=self.tester,
        )

    def test_staff_member_can_assign_a_developer(self):
        self.client.login(username="developer", password="pass12345")
        self.client.post(
            reverse("issue_tracker:issue_assign", args=[self.issue.pk]),
            {"assigned_to": self.developer.pk},
        )
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.assigned_to, self.developer)

    def test_normal_user_cannot_assign_a_developer(self):
        self.client.login(username="tester", password="pass12345")
        response = self.client.post(
            reverse("issue_tracker:issue_assign", args=[self.issue.pk]),
            {"assigned_to": self.developer.pk},
        )
        self.assertRedirects(response, reverse("issue_tracker:dashboard"))
        self.issue.refresh_from_db()
        self.assertIsNone(self.issue.assigned_to)


class SeedDemoCommandTests(TestCase):
    def test_seed_demo_creates_users_issues_and_comments(self):
        call_command("seed_demo", stdout=StringIO())

        for username in ("admin", "developer", "tester"):
            self.assertTrue(User.objects.filter(username=username).exists())

        self.assertGreaterEqual(Issue.objects.count(), 5)
        self.assertGreaterEqual(Comment.objects.count(), 1)
        self.assertTrue(self.client.login(username="admin", password="admin123"))

    def test_seed_demo_can_run_twice_without_duplicating(self):
        call_command("seed_demo", stdout=StringIO())
        count_after_first_run = Issue.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Issue.objects.count(), count_after_first_run)
