# Database setup

Imboni works without a database (statistics are served from `data/processed`). The database stores **saved
scenarios** and a **mirror of the reference data** (`sources`, `indicators`, `observations`) for SQL users.

## Configuration

`.env` (never committed):

```
DATABASE_URL=mysql+pymysql://nisr_app:<password>@localhost:3306/nisr-hachathon
DB_CREATE_DATABASE=true
DB_FALLBACK_ENABLED=true
DB_FALLBACK_URL=sqlite:///./data/imboni.db
```

* The database name `nisr-hachathon` contains a hyphen. It is valid in the URL path; when Imboni creates it, the
  name is validated (`[A-Za-z0-9_-]`, ≤ 64 chars) and backtick-quoted: ``CREATE DATABASE IF NOT EXISTS `nisr-hachathon` ``.
* URL-encode special characters in passwords (`@` → `%40`, `:` → `%3A`, `/` → `%2F`).
* The app **never** creates users, grants privileges, changes passwords or drops anything. Tables are created
  additively (`CREATE TABLE IF NOT EXISTS` semantics via SQLAlchemy `create_all`).

## One-time MySQL setup (to be run by whoever administers the MySQL server)

Status on the development machine (2026-10-11): MySQL 8.0 service is running on port 3306, but the configured
user `nisr_app` does not exist / was rejected (`ERROR 1045 Access denied`). Imboni therefore ran on its SQLite
fallback. To enable MySQL, an administrator runs (choose your own strong password and put it only in `.env`):

```sql
CREATE DATABASE IF NOT EXISTS `nisr-hachathon` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'nisr_app'@'localhost' IDENTIFIED BY '<password from .env>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON `nisr-hachathon`.* TO 'nisr_app'@'localhost';
FLUSH PRIVILEGES;
```

Then: `python scripts/init_db.py` → should print `Database backend : mysql`.
If your MySQL account already has rights, simply set its credentials in `DATABASE_URL` instead.

## Migrations

The schema is small and created by `Base.metadata.create_all` (`backend/app/models.py`). For future schema
changes add Alembic (`alembic init`, autogenerate against `Base.metadata`). Reference tables are re-seeded
automatically when the processed observation count changes (only Imboni's own `observations`, `indicators` and
`sources` tables are refreshed; `scenarios` are never touched).

## Checking status

`GET /api/health` → `database.backend` is `mysql`, `sqlite` or `sqlite-fallback` (with a reason in development;
redacted in production).
