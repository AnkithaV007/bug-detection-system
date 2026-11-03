# BugResolutionPortal

A Bug Detection and Fixing System built with Django and SQLite.

Testers report bugs, developers pick them up and record their debugging notes,
and staff members assign work and track everything from a dashboard.

The project also includes a React dashboard in `frontend/`. The backend keeps
its existing Django structure and exposes authenticated JSON endpoints for the
React app.

---

## 1. Setup (Windows PowerShell)

Open PowerShell inside the `BugResolutionPortal` folder (the one that contains
`manage.py`) and run these commands in order:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Then open <http://127.0.0.1:8000/> in your browser.

### PostgreSQL

Set `DATABASE_URL` before starting Django, for example:

```powershell
$env:DATABASE_URL = "postgresql://postgres:password@localhost:5432/bug_portal"
```

Without `DATABASE_URL`, the project continues to use the included SQLite
database for local development.

### React frontend

```powershell
cd frontend
npm install
npm run dev
```

Set `OPENAI_API_KEY` to enable the read-only natural-language issue search.
The key is used only by Django and must not be added to the React app.

> If PowerShell blocks `activate` with a script execution error, run
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` once in the
> same window and try again.

The Django admin site is at <http://127.0.0.1:8000/admin/>.

---

## 2. Verify the project

```powershell
python manage.py check
python manage.py test
```

`check` reports no issues and the test suite runs 15 tests covering the models,
the login protection, the search and filters, the dashboard counters, the staff
only assignment rule, and the `seed_demo` command.

---

## 3. What each file does

```
BugResolutionPortal/
├── manage.py                 Django's command line entry point
├── requirements.txt          Python packages needed (Django only)
├── db.sqlite3                The SQLite database file
│
├── bug_portal/               Project configuration package
│   ├── settings.py           Apps, templates folder, static folder, timezone, login URLs
│   ├── urls.py               Admin, login, logout, and the app's URLs
│   ├── asgi.py / wsgi.py     Server entry points
│
├── issue_tracker/            The application itself
│   ├── models.py             Issue and Comment tables
│   ├── forms.py              Report form, status form, assign form, comment form
│   ├── views.py              One function per page
│   ├── urls.py               Page addresses for this app
│   ├── decorators.py         staff_required access rule
│   ├── admin.py              Registers Issue and Comment in the admin site
│   ├── tests.py              Automated tests
│   ├── migrations/           Database change history
│   └── management/commands/seed_demo.py    Creates demo users, bugs and comments
│
├── templates/                All HTML pages
│   ├── base.html             Shared layout: navbar, messages, footer
│   ├── registration/login.html
│   └── issue_tracker/        dashboard, issue_list, issue_form, issue_detail
│
└── static/css/app.css        All styling, plain CSS (no Bootstrap, no Tailwind)
```

---

## 4. The data model

**Issue**

| Field                | Meaning                                              |
|----------------------|------------------------------------------------------|
| `issue_id`           | Auto generated reference such as `BUG-0001`          |
| `title`              | One line summary                                     |
| `description`        | What is wrong and where                              |
| `steps_to_reproduce` | Steps another person can follow to see the bug       |
| `priority`           | Low, Medium, High, Critical                          |
| `status`             | Open, In Progress, Resolved, Closed                  |
| `reporter`           | The user who reported it (Django's built-in `User`)  |
| `assigned_to`        | The developer working on it, may be empty            |
| `created_at`         | Set once when the report is saved                    |
| `updated_at`         | Refreshed on every save                              |

**Comment** — belongs to one issue, records the author, the note text and the
time. This is where debugging findings and fixing progress are written down.

---

## 5. Pages and who can use them

| Page             | Address              | Access                                  |
|------------------|----------------------|-----------------------------------------|
| Login            | `/login/`            | Everyone                                |
| Dashboard        | `/`                  | Logged in users                         |
| All issues       | `/issues/`           | Logged in users                         |
| Report an issue  | `/issues/new/`       | Logged in users, including normal users |
| Issue detail     | `/issues/<id>/`      | Logged in users                         |
| Assign developer | `/issues/<id>/assign/` | Staff members only (`@staff_required`) |

Every view carries `@login_required`, so an anonymous visitor is always sent to
the login page first.

---

## 6. Points to explain in the viva

- **Why two models?** An issue is the bug itself; comments are the running
  conversation about it. Splitting them keeps one row per bug and lets an issue
  have any number of notes, which is a standard one-to-many relationship.
- **Why `issue_id` as well as the primary key?** The primary key is a number the
  database chooses. `BUG-0001` is the label people actually say out loud and
  search for, so it is generated once in `Issue.save()` right after the row gets
  its primary key.
- **How does authentication work?** Django's built-in `User` model plus its
  `LoginView` and `LogoutView`. Only the templates are ours. `LOGIN_URL`,
  `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` in `settings.py` control where
  users land.
- **What does `decorators.py` add?** `login_required` answers "are you signed
  in?". `staff_required` adds "are you also a staff member?" and is used only on
  the assignment view, so reporting a bug stays open to everyone. If a normal
  user tries it, they get a clear message and go back to the dashboard.
- **How do search and filters work?** The list page reads `q`, `status` and
  `priority` from the query string and chains `.filter()` calls on the queryset.
  The keyword search uses `Q` objects so one term can match the title, the
  description or the reference number.
- **Why does the dashboard exclude closed bugs from the Critical count?** A
  closed critical bug needs no attention, so counting it would overstate the
  work left.
