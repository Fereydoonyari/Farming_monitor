# Farming Monitor (Course Project)

Simple farming management web app built step-by-step.

## Tech
- Backend: Python (Flask) + MySQL
- Frontend: HTML/CSS/JavaScript

## v1 (current)
- Register / login / logout
- MySQL-backed `users` table
- API endpoints: `/api/register`, `/api/login`, `/api/logout`, `/api/me`
- Admin vs farmer is controlled by the `users.role` column (set admins in MySQL)

## Setup

### 1) Create database + table
Create a MySQL database named `farming_monitor`, then run:
- `backend/schema.sql`

### 2) Backend env vars
Copy `backend/.env.example` to `backend/.env` and set your MySQL credentials.

### 3) Install backend dependencies
From `backend/`:
- `python -m venv .venv`
- Activate venv
- `pip install -r requirements.txt`

### 4) Run backend
From `backend/`:
- `python app.py`

Backend runs on `http://127.0.0.1:5000`.

## Next steps (planned)
- Add farms/fields/crops tables + CRUD APIs
- Add simple dashboard page after login
- Add tasks & reminders
