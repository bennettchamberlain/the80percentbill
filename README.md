# The 80 Percent Bill

A Django website for The 80% Bill — 20 bills that 80%+ of Americans support. Sign the pledge, read the bill, and support the project.

Migrated from the Streamlit app at `/Users/bennett/Development/JS/the-80-percent-bill`.

## Architecture

The project lives at `python/the_80_percent_bill/`. All commands run from there.

```
python/the_80_percent_bill/        # Project root (run manage.py from here)
├── manage.py
├── requirements.txt
├── .env                           # Secrets (copy from .env.example)
├── .env.example
├── venv/
├── db.sqlite3
├── templates/                     # Shared base template
│   └── base.html
├── static/
│   └── css/
│       └── theme.css
├── the_80_percent_bill/           # Django project config
│   ├── settings.py
│   ├── urls.py                   # Root URL router (Django built-in)
│   ├── context_processors.py
│   └── ...
├── core/                          # Shared utilities
│   ├── geo.py                    # OSM + Geocodio address → district lookup
│   └── sheets.py                # Pledge storage (Supabase or SQLite)
├── home/                          # Feature: landing page
│   ├── views.py
│   ├── urls.py
│   └── templates/home/
├── bill/                          # Feature: read the 20 articles
│   ├── views.py
│   ├── articles.py               # Bill article data
│   ├── urls.py
│   └── templates/bill/
└── pledge/                        # Feature: sign the pledge (3-step flow)
    ├── views.py
    ├── urls.py
    └── templates/pledge/
```

### URLs (Django routing)

| Path | Feature |
|------|---------|
| `/` | Home — hero + CTAs |
| `/pledge/` | Sign the pledge (district lookup → name/email → success) |
| `/bill/` | Read the 20 bill articles |
| `/admin/` | Django admin |

---

## Dev: quick start

> All commands run from the project root: `cd python/the_80_percent_bill` (or wherever `manage.py` lives)

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate          # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env: add GEOCODIO_API_KEY (required). Add SUPABASE_* for Supabase, or leave out for SQLite.

# 4. Run migrations
python manage.py migrate

# 5. (Optional) Create admin user
python manage.py createsuperuser

# 6. Start the dev server
python manage.py runserver
# Or use another port if 8000 is in use: python manage.py runserver 8001

# 7. When done, exit the virtual environment
deactivate
```

Open **http://127.0.0.1:8000/** (or your chosen port) in your browser.

### Dev environment variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEOCODIO_API_KEY` | Yes | Address → congressional district lookup |
| `DEBUG` | No | Set `true` for dev — detailed error pages, auto-reload. Set `false` in production. |
| `SUPABASE_DB_PASSWORD` | No | If set, uses Supabase. Omit for local SQLite (`db.sqlite3`). |
| `SUPABASE_DB_HOST` | If using Supabase | Direct: `db.xxx.supabase.co` (local). Pooler: `aws-0-REGION.pooler.supabase.com` (Railway). |
| `SUPABASE_DB_USER` | If using Supabase | Direct: `postgres`. Pooler: `postgres.PROJECT_REF` |
| `SUPABASE_USE_POOLER` | No | Set `false` for local (direct/IPv6). Default `true` for Railway (pooler/IPv4). |

**Recommended `.env` for dev:**
```
GEOCODIO_API_KEY=your_key_here
DEBUG=true
# ... plus SUPABASE_* if using Supabase
```

---

## GitHub Actions (deploy check)

A workflow runs on push/PR to `main` to validate the app before Railway deploys. Add these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Required | Description |
|--------|----------|-------------|
| `SUPABASE_DB_PASSWORD` | Yes | Supabase database password |
| `GEOCODIO_API_KEY` | Yes | For address lookup |
| `DJANGO_SECRET_KEY` | Yes | Any random string (can match production) |
| `SUPABASE_DB_HOST` | No | Default: `aws-0-us-west-2.pooler.supabase.com` |
| `SUPABASE_DB_USER` | No | Default: `postgres.dugqtfasgcprvqpcktdl` |
| `SUPABASE_DB_NAME` | No | Default: `postgres` |
| `SUPABASE_DB_PORT` | No | Default: `5432` |

If the repo root is not the Django project (e.g. app is in `python/the_80_percent_bill`), add `working-directory` to the job in `.github/workflows/deploy-check.yml`.

---

## Railway deployment

1. **Create a Railway project** from your GitHub repo.

2. **Set environment variables** in Railway → your service → Variables:

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `SUPABASE_DB_PASSWORD` | Yes | Supabase database password |
   | `SUPABASE_DB_HOST` | Yes (Railway) | **Use pooler** (IPv4): `aws-0-us-west-2.pooler.supabase.com` — from Supabase → Connect → Session pooler. Direct `db.xxx.supabase.co` uses IPv6 and fails on Railway. |
   | `SUPABASE_DB_USER` | Yes (Railway) | **Use pooler user**: `postgres.<PROJECT_REF>` (e.g. `postgres.dugqtfasgcprvqpcktdl`) — from Supabase → Connect → Session pooler |
   | `SUPABASE_DB_NAME` | No | Default: `postgres` |
   | `SUPABASE_DB_PORT` | No | Default: `5432` (session pooler) |
   | `SUPABASE_USE_POOLER` | No | Default: `true` — keep true for Railway (IPv4) |
   | `GEOCODIO_API_KEY` | Yes | For address → district lookup |
   | `DJANGO_SECRET_KEY` | Yes (prod) | Random secret; generate a new one for production |
   | `DEBUG` | No | Set to `false` in production |

3. **Set Root Directory** (if your repo has the app in a subfolder): Railway → Settings → Root Directory → `python/the_80_percent_bill` or wherever `manage.py` lives.

4. **Generate Domain**: Railway → your service → Settings → Networking → Generate Domain.

5. **Create admin user** after first deploy: Railway → your service → Run Command → `python manage.py createsuperuser`.

6. **Custom domain?** If you add one, set `CSRF_TRUSTED_ORIGINS=https://yourdomain.com` so pledge forms work.

---

## Quick reference

| Command | Description |
|---------|-------------|
| `source venv/bin/activate` | Activate virtual environment (macOS/Linux) |
| `deactivate` | Exit virtual environment |
| `python manage.py runserver` | Start dev server (port 8000) |
| `python manage.py migrate` | Apply migrations |
| `python manage.py createsuperuser` | Create admin user |
