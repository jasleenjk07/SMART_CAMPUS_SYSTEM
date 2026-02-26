# LMS Smart Campus System

A Django-based campus management project focused on attendance workflows, scheduling support, and communication logs for educational institutions.

This repository contains the main application in `smart-attendance/`.

## Key Features

- Role-based dashboards for staff, faculty, and students
- Faculty and student registration/login flows
- Student management with section mapping and contact details
- Section-wise attendance marking with absentee auto-detection
- Simulated student/parent notification logging
- Campus resource planning (blocks, classrooms, schedules)
- Make-up class management with remedial code workflow
- Basic analytics (capacity utilization, workload, rush prediction)

## Tech Stack

- Python
- Django (see `smart-attendance/requirements.txt`)
- SQLite (default development database)
- Server-rendered templates (HTML/CSS + minimal JavaScript)

## Project Structure

```text
LMS-SMART-CAMPUS/
├── README.md
└── smart-attendance/
    ├── manage.py
    ├── requirements.txt
    ├── attendance/       # Core app (models, views, forms, templates)
    ├── notifications/    # Notification simulation/logging
    └── config/           # Django settings and URL configuration
```

## Quick Start

1. Move into the app directory:

```bash
cd smart-attendance
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run migrations:

```bash
python manage.py migrate
```

4. Seed sample data (optional but recommended):

```bash
python manage.py seed_data
```

5. Start the development server:

```bash
python manage.py runserver
```

6. Open:

```text
http://127.0.0.1:8000/
```

## Demo Credentials (Seed Data)

After running `python manage.py seed_data`:

- Username: `faculty1`
- Password: `testpass123`

## API Example

Simulate absentee notification:

```bash
curl -X POST http://127.0.0.1:8000/api/notifications/simulate/ \
  -H "Content-Type: application/json" \
  -d '{"student_id": 1}'
```

## Documentation

For complete architecture, flow diagrams, and detailed setup:

- `smart-attendance/README.md`
