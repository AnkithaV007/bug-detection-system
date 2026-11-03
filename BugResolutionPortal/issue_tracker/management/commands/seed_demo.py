"""Fill the database with demo accounts and realistic sample bugs.

Run it with:

    python manage.py seed_demo

The command is safe to run more than once: existing users and issues are
reused instead of duplicated.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from issue_tracker.models import Comment, Issue

DEMO_USERS = [
    # username, password, first name, last name, is_staff, is_superuser
    ("admin", "admin123", "Project", "Admin", True, True),
    ("developer", "developer123", "Dev", "Kumar", True, False),
    ("tester", "tester123", "QA", "Sharma", False, False),
]

DEMO_ISSUES = [
    {
        "title": "Login page accepts an empty password",
        "description": (
            "On the login form the Sign in button submits even when the "
            "password box is blank. The server then returns a 500 error "
            "instead of a friendly validation message."
        ),
        "steps_to_reproduce": (
            "1. Open /login/\n"
            "2. Type a valid username\n"
            "3. Leave the password field empty\n"
            "4. Click Sign in"
        ),
        "priority": Issue.PRIORITY_CRITICAL,
        "status": Issue.STATUS_OPEN,
        "reporter": "tester",
        "assigned_to": None,
    },
    {
        "title": "Dashboard totals do not match the issue list",
        "description": (
            "The Open counter on the dashboard shows 12 while the All "
            "Issues page lists only 9 open bugs. Closed issues seem to be "
            "counted twice."
        ),
        "steps_to_reproduce": (
            "1. Sign in as any user\n"
            "2. Note the Open number on the dashboard\n"
            "3. Open All Issues and filter by status Open\n"
            "4. Compare the two numbers"
        ),
        "priority": Issue.PRIORITY_HIGH,
        "status": Issue.STATUS_IN_PROGRESS,
        "reporter": "tester",
        "assigned_to": "developer",
    },
    {
        "title": "Search box ignores the issue reference number",
        "description": (
            "Searching for BUG-0003 returns no results even though that "
            "issue exists. Searching by title works, so the query is only "
            "looking at the title and description columns."
        ),
        "steps_to_reproduce": (
            "1. Open All Issues\n"
            "2. Type BUG-0003 in the search box\n"
            "3. Press Enter"
        ),
        "priority": Issue.PRIORITY_MEDIUM,
        "status": Issue.STATUS_RESOLVED,
        "reporter": "developer",
        "assigned_to": "developer",
    },
    {
        "title": "Priority badge colour is unreadable on small screens",
        "description": (
            "Below 480px wide the Critical badge text wraps onto two lines "
            "and the light text on the light background fails contrast "
            "checks."
        ),
        "steps_to_reproduce": (
            "1. Open All Issues on a phone or a narrow browser window\n"
            "2. Look at any Critical row"
        ),
        "priority": Issue.PRIORITY_LOW,
        "status": Issue.STATUS_OPEN,
        "reporter": "tester",
        "assigned_to": "developer",
    },
    {
        "title": "Comments are saved without the author name",
        "description": (
            "Comments posted from the issue detail page are stored with an "
            "empty author, so the timeline shows 'None wrote'. The author "
            "is not being taken from the logged in session."
        ),
        "steps_to_reproduce": (
            "1. Open any issue\n"
            "2. Add a comment\n"
            "3. Reload the page and look at the comment header"
        ),
        "priority": Issue.PRIORITY_HIGH,
        "status": Issue.STATUS_CLOSED,
        "reporter": "admin",
        "assigned_to": "developer",
    },
    {
        "title": "Report Issue form loses text after a validation error",
        "description": (
            "If the title is left blank the page reloads with an error but "
            "the description and steps the user already typed are wiped, so "
            "everything has to be entered again."
        ),
        "steps_to_reproduce": (
            "1. Open Report Issue\n"
            "2. Fill in the description and steps but leave the title empty\n"
            "3. Submit the form"
        ),
        "priority": Issue.PRIORITY_MEDIUM,
        "status": Issue.STATUS_IN_PROGRESS,
        "reporter": "tester",
        "assigned_to": "developer",
    },
]

DEMO_COMMENTS = [
    (
        "Login page accepts an empty password",
        "tester",
        "Reproduced on Chrome and Firefox. The 500 page appears every time.",
    ),
    (
        "Dashboard totals do not match the issue list",
        "developer",
        "Found it: the counter query is missing the exclude() for closed "
        "issues. Writing a fix now.",
    ),
    (
        "Dashboard totals do not match the issue list",
        "admin",
        "Please add a small test for the counter so this does not come back.",
    ),
    (
        "Search box ignores the issue reference number",
        "developer",
        "Fixed by adding issue_id to the search filter. Ready for retest.",
    ),
    (
        "Comments are saved without the author name",
        "developer",
        "The author is now taken from request.user before saving. Verified "
        "and closing this one.",
    ),
]


class Command(BaseCommand):
    help = "Create demo users, sample bug reports and comments."

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._create_users()
        issues = self._create_issues(users)
        self._create_comments(issues, users)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("  admin     / admin123      (superuser, full admin access)")
        self.stdout.write("  developer / developer123  (staff, can assign issues)")
        self.stdout.write("  tester    / tester123     (normal user, reports issues)")

    # ------------------------------------------------------------------
    def _create_users(self):
        users = {}
        for username, password, first, last, is_staff, is_superuser in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@bugportal.local",
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            # Always reset the password so the demo logins are predictable.
            user.first_name = first
            user.last_name = last
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.set_password(password)
            user.save()

            users[username] = user
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} user: {username}")
        return users

    def _create_issues(self, users):
        issues = {}
        for data in DEMO_ISSUES:
            issue, created = Issue.objects.get_or_create(
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "steps_to_reproduce": data["steps_to_reproduce"],
                    "priority": data["priority"],
                    "status": data["status"],
                    "reporter": users[data["reporter"]],
                    "assigned_to": users.get(data["assigned_to"]),
                },
            )
            issues[data["title"]] = issue
            if created:
                self.stdout.write(f"Created issue: {issue.issue_id} {issue.title}")
        return issues

    def _create_comments(self, issues, users):
        for title, username, body in DEMO_COMMENTS:
            issue = issues.get(title)
            if issue is None:
                continue
            _, created = Comment.objects.get_or_create(
                issue=issue,
                author=users[username],
                body=body,
            )
            if created:
                self.stdout.write(f"Created comment on {issue.issue_id}")
