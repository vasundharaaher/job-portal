# Job Portal — Django REST Framework Backend

A production-ready, clean, and secure RESTful backend API for an online Job Portal platform. Built with **Django 5**, **Django REST Framework (DRF)**, and **SimpleJWT**.

---

## 🚀 Features

- **JWT Authentication:** Secure user authentication using Bearer tokens (access + refresh) with automatic role extraction (`Candidate`, `Company`, `Admin`).
- **Password Security:** All passwords hashed with PBKDF2 (`make_password`).
- **Zero-IDOR Design:** Candidate and Company actions are strictly bound to `request.user` extracted from verified JWT tokens.
- **Search, Filtering & Pagination:** Full keyword search, category, location, and experience filtering with customizable page sizes.
- **File Upload Validation:** Validation for resumes (PDF, DOC, DOCX up to 5MB) and profile/logo images (JPG, PNG, WEBP up to 3MB).
- **Dual Database Support:** Instant local development with **SQLite** (zero installation), and seamless 1-variable switch to **MySQL** for deployment.
- **Django Admin:** Fully registered admin panel with search, filters, and list displays.
- **Comprehensive Unit Tests:** 100% passing test suite.

---

## 🛠️ Quickstart

### 1. Configure Environment
Copy `.env.example` to `.env` (already pre-configured for SQLite development):
```bash
cp .env.example .env
```

### 2. Run Database Migrations
```bash
python manage.py migrate
```

### 3. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 4. Run the Development Server
```bash
python manage.py runserver
```
The server will start at: `http://127.0.0.1:8000`

---

## 🗄️ Switching to MySQL for Deployment

To switch from SQLite to MySQL, simply update your `.env` file:
```dotenv
DB_ENGINE=mysql
DB_NAME=jobportal_db_final
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```
Then run:
```bash
python manage.py migrate
```

---

## 📚 API Endpoints Reference

### 🔐 Authentication (`/api/auth/`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/register/` | Register Candidate or Company | None |
| `POST` | `/api/auth/otp-verify/` | Verify OTP & receive JWT tokens | None |
| `POST` | `/api/auth/login/` | Login with email/password & receive tokens | None |
| `POST` | `/api/auth/token/refresh/` | Refresh access token using refresh token | None |

### 💼 Jobs (`/api/jobs/`)
| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `GET` | `/api/jobs/` | List all jobs (paginated) | `search`, `category`, `job_type`, `location`, `min_experience`, `max_experience`, `page`, `page_size` |
| `GET` | `/api/jobs/categories/` | List all categories with counts | None |
| `GET` | `/api/jobs/<id>/` | Get detailed job information | None |

### 👤 Candidate (`/api/candidate/`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/candidate/profile/` | Get current candidate profile | Candidate Token |
| `PATCH` | `/api/candidate/profile/update/` | Update profile / upload avatar | Candidate Token |
| `POST` | `/api/jobs/<job_id>/apply/` | Apply to job (with resume file) | Candidate Token |
| `GET` | `/api/candidate/applied-jobs/` | List applied jobs | Candidate Token |

### 🏢 Company (`/api/company/`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/company/profile/` | Get current company profile | Company Token |
| `PATCH` | `/api/company/profile/update/` | Update company profile & logo | Company Token |
| `POST` | `/api/company/jobs/post/` | Post a new job | Company Token |
| `GET` | `/api/company/jobs/` | List jobs posted by company | Company Token |
| `GET` | `/api/company/applicants/` | View applicants for company's jobs | Company Token |
| `POST` | `/api/bookmarks/add/` | Bookmark candidate (`candidate_id`) | Company Token |
| `GET` | `/api/company/bookmarks/` | List bookmarked candidates | Company Token |
| `DELETE` | `/api/bookmarks/<id>/remove/` | Remove candidate bookmark | Company Token |

### ✉️ Contact & Admin (`/api/admin/`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/contact/` | Submit contact inquiry | None |
| `POST` | `/api/admin/login/` | Admin login | None |
| `GET` | `/api/admin/candidates/` | List all candidate users | Admin Token |
| `GET` | `/api/admin/companies/` | List all company users | Admin Token |
| `GET` | `/api/admin/contact-messages/` | View contact messages | Admin Token |
| `PATCH` | `/api/admin/companies/<id>/verify/` | Mark company as verified | Admin Token |
| `DELETE` | `/api/admin/users/<id>/delete/` | Delete user account | Admin Token |

---

## 🧪 Running Unit Tests
```bash
python manage.py test
```
All unit tests run inside an isolated test database and verify authentication, permissions, file validation, filtering, and job applications.
