# OrbitPM — Modern Project & Workflow Management Platform

OrbitPM is a production-grade, highly scalable SaaS scaffolding designed for Digital Agencies to manage projects, tasks, workflows, teams, and billing. 

This repository implements a solid, state-of-the-art monorepo foundation including a custom decoupled **Django REST Framework (DRF)** backend and a gorgeous, highly responsive **React + Vite** frontend styled with **Ant Design (v5)**.

---

## 🏗️ Architectural Overview & Directory Map

The workspace is organized into two primary segments inside a unified repository structure:

```
OrbitPM/
├── backend/                  # Django REST Framework Backend
│   ├── config/               # Project-level configuration & split settings
│   │   └── settings/         # base.py, development.py, production.py
│   ├── accounts/             # UUID User models, Role-based auth (SimpleJWT)
│   ├── projects/             # Projects feature domain
│   ├── tasks/                # Tasks feature domain
│   ├── teams/                # Teams and member association models
│   ├── invoices/             # Invoices & billing systems
│   ├── notifications/        # Internal alert dispatcher
│   ├── analytics/            # Reporting and system analytics
│   ├── common/               # Global standard exception handlers & standard renderers
│   ├── manage.py             # Django runner script
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── .gitignore            # Git ignore patterns for Python/Django
│
├── orbitpm-frontend/         # React + Vite + Ant Design Frontend
│   ├── src/                  # React source tree
│   │   ├── api/              # Axios client configured with silent JWT auto-refresh
│   │   ├── components/       # Global UI primitives (ReusableTable, ReusableModal)
│   │   ├── context/          # State Engines (AuthContext, ThemeContext)
│   │   ├── features/         # Decoupled domain modules (auth, dashboard, tasks, projects)
│   │   ├── layouts/          # Dynamic Shell containers (AuthLayout, DashboardLayout)
│   │   ├── pages/            # View pages for routing
│   │   └── routes/           # Protected routes with role gating
│   ├── package.json          # Node dependencies list
│   ├── vite.config.js        # Vite compiler settings
│   ├── .env.example          # Frontend configuration variables
│   └── .gitignore            # Git ignore patterns for React/Vite/Node
│
└── README.md                 # System overview (this file)
```

---

## ⚡ Key Architectural Highlights

### 🛡️ Django Backend Principles

1. **Clean Decoupled Architecture**: 
   Every app module is split into dedicated structural layers to avoid bloated models or views:
   - `models.py`: Pure database model definitions and basic constraints.
   - `serializers/`: Handles request payload deserialization/validation and API representation.
   - `services/`: Houses modifying operations and business logic (write paths), ensuring controllers remain lightweight.
   - `selectors/`: Handles complex database queries, aggregations, and fetches (read paths).
   - `permissions/`: Granular endpoint access control policies.
   - `tests/`: Module-specific unit and integration test suites.

2. **Standardized API Envelope**:
   All HTTP responses are unified globally by a customized response renderer (`StandardJSONRenderer`). API clients always receive a consistent schema:
   ```json
   {
     "success": true,
     "data": { ... },
     "error": null,
     "message": "Operation completed successfully"
   }
   ```
   If an error occurs, the global exception handler automatically intercepts the exception (including DRF Validation Errors) and yields:
   ```json
   {
     "success": false,
     "data": null,
     "error": {
       "code": "validation_error",
       "detail": "Field is required.",
       "fields": { "email": ["Enter a valid email address."] }
     },
     "message": "A validation error occurred"
   }
   ```

3. **Robust Security & User Management**:
   - **UUID-based primary keys** are used throughout all database models to eliminate auto-incrementing ID exposure risks.
   - Custom `User` model supports four main system roles: `ADMIN`, `MANAGER`, `DEVELOPER`, and `CLIENT`.
   - Customized **SimpleJWT** returns access/refresh tokens alongside a full user profile payload in a single round-trip.

---

### 🎨 React Frontend Principles

1. **Theme State Engine & Ant Design ConfigProvider**:
   - Out-of-the-box support for both **Light and Dark mode** dynamic switching.
   - Leverages Ant Design's `ConfigProvider` styling algorithm to inject custom tokens dynamically (e.g. customized primary Indigo accent `#6366f1` and modern Outfit & Inter typography) without flashing unstyled layouts.
   
2. **Transparent Silent Token Refresh Interceptor**:
   - Customized Axios instance (`src/api/client.js`) intercepts 401 response statuses transparently.
   - If an access token expires, it silently issues a refresh token exchange request, saves the new key, updates local state, and retries the original request seamlessly.

3. **Layout Shells with Advanced Styling**:
   - **AuthLayout**: Dynamic background gradients with CSS glassmorphic floating panels (`glass-card` CSS templates).
   - **DashboardLayout**: Responsive, collapsible sidebar (Sider) and sticky header navigation with light/dark adaptive background surfaces.

---

## 🚀 Local Developer Setup Guide

### 🐍 Backend Setup

1. **Create and Activate a Virtual Environment**:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` into a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
   *Note: If no PostgreSQL configuration variables are specified in `.env`, the system automatically falls back to a local SQLite database (`db.sqlite3`), facilitating zero-configuration local runs.*

4. **Run Migrations & Create Superuser**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Execute Unit Tests**:
   To verify accounts and authentication:
   ```bash
   python manage.py test
   ```

6. **Start Dev Server**:
   ```bash
   python manage.py runserver
   ```
   The backend will be live at `http://127.0.0.1:8000/`.

---

### ⚛️ Frontend Setup

1. **Install Node Packages**:
   Make sure you have Node (v18+) and NPM (v10+) installed:
   ```bash
   cd orbitpm-frontend
   npm install
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *Default API Target: `http://localhost:8000/api/v1`*

3. **Start Development Server**:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173/`.

4. **Production Build**:
   ```bash
   npm run build
   ```

---

## 📑 Core API Routes Blueprint

All endpoints are prefixed with `/api/v1/`:

| App | Endpoint Path | HTTP Method | Auth Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Accounts** | `/auth/register/` | `POST` | No | Registers a new User profile. |
| | `/auth/login/` | `POST` | No | Submits email/password; returns JWT + User details. |
| | `/auth/refresh/` | `POST` | No | Exchanges a valid Refresh Token for an Access Token. |
| | `/auth/me/` | `GET` | Yes | Retrieves current user context. |
| **Projects** | `/projects/` | `GET` / `POST` | Yes | Lists or creates projects. |
| **Tasks** | `/tasks/` | `GET` / `POST` | Yes | Lists or spawns task boards. |
| **Teams** | `/teams/` | `GET` / `POST` | Yes | Lists or creates organization teams. |
| **Invoices** | `/invoices/` | `GET` / `POST` | Yes | Manages billing and financial sheets. |
| **Notifications** | `/notifications/` | `GET` | Yes | Pulls user notifications stream. |
| **Analytics** | `/analytics/` | `GET` | Yes | Compiles workflow status logs. |

---

## 🛡️ License

Developed under corporate-level production criteria. Custom-tailored for agency operations.
