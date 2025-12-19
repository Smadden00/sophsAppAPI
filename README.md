# sophsAppAPI

A Flask-based REST API built with Gunicorn and PostgreSQL, designed for production deployment with systemd service management.

---

## 🚀 Quick Reference

**systemd Service Location:** `/etc/systemd/system/sophsAppApi.service`

**Health Check Endpoint:** `GET /api/health`

**Local Binding:** `http://127.0.0.1:5000`

---

## 📋 Table of Contents

- [Overview](#overview)
- [Installation & Setup](#installation--setup)
- [Service Management](#service-management)
- [Monitoring & Logs](#monitoring--logs)
- [Health Checks](#health-checks)
- [Security](#security)

---

## Overview

### Architecture

This project uses **Gunicorn** as the production WSGI server for the Flask API. Gunicorn sits between the web server (Nginx, to be added) and the Flask application, managing multiple worker processes and handling incoming HTTP requests efficiently.

### Application Factory Pattern

The Flask app follows the application factory pattern with `create_app()` defined in `app/__init__.py`. The WSGI entrypoint is exposed in `run.py`:

```python
from app import create_app
app = create_app()
```

This allows Gunicorn to load the application using the module reference:

```
run:app
```

### Service Benefits

Gunicorn runs as a **systemd-managed service**, ensuring the API:
- ✅ Starts automatically on server boot
- ✅ Restarts automatically if it crashes
- ✅ Runs independently of any user shell session
- ✅ Provides robust logging and monitoring

---

## Installation & Setup

### 1. Virtual Environment & Dependencies

Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install Gunicorn and all dependencies:

```bash
pip install gunicorn
pip install -r requirements.txt
```

All runtime dependencies (Flask, SQLAlchemy, psycopg2, python-dotenv, etc.) are installed into the same environment.

### 2. Gunicorn Configuration

Gunicorn is configured with the following settings:

- **Workers:** 3 worker processes
- **Binding:** `127.0.0.1:5000` (localhost only)
- **Environment:** Variables loaded from `.env` file
- **Command:** `gunicorn --workers 3 --bind 127.0.0.1:5000 run:app`

> **Note:** Nginx will act as the public-facing reverse proxy. Gunicorn is not directly exposed to the internet.

### 3. systemd Service Configuration

The service is managed by systemd at:

```
/etc/systemd/system/sophsAppApi.service
```

**Key characteristics:**
- Runs as a non-root user
- Sets working directory to project root
- Loads environment variables from `.env` file
- Automatically restarts on failure
- Production-safe and resilient

---

## Service Management

### Basic Commands

**Start the API:**
```bash
sudo systemctl start sophsAppApi
```

**Stop the API:**
```bash
sudo systemctl stop sophsAppApi
```

**Restart the API:**
```bash
sudo systemctl restart sophsAppApi
```

**Check service status:**
```bash
sudo systemctl status sophsAppApi
```

**Enable auto-start on boot:**
```bash
sudo systemctl enable sophsAppApi
```

### When to Restart

Restart the service after making changes to:

- ✏️ Flask application code
- 🔧 Environment variables (`.env` file)
- 📦 Dependencies (`requirements.txt`)
- ⚙️ Configuration files (database, uploads, etc.)

**Example workflow:**
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sophsAppApi
```

---

## Monitoring & Logs

### Viewing Logs

Gunicorn logs (stdout/stderr) are captured by systemd and can be viewed with:

**View recent logs (last 200 lines):**
```bash
sudo journalctl -u sophsAppApi -n 200
```

**Follow logs in real time:**
```bash
sudo journalctl -u sophsAppApi -f
```

**View logs for a specific time range:**
```bash
sudo journalctl -u sophsAppApi --since "1 hour ago"
```

---

## Health Checks

The API exposes a health endpoint to verify service and database connectivity.

**Endpoint:**
```
GET /api/health
```

**Test locally:**
```bash
curl http://127.0.0.1:5000/api/health
```

**A successful response confirms:**
- ✅ Gunicorn is running
- ✅ Flask app loaded correctly
- ✅ Database connection is healthy

---

## Security

### Network Configuration

- 🔒 Gunicorn is **not exposed publicly**
- 🔒 Port 5000 is bound to `127.0.0.1` only
- 🔒 External traffic flows through **Nginx over HTTPS**
- 🔒 Database credentials are **never exposed** to the frontend

### Environment Variables

Sensitive configuration is stored in a `.env` file:
- Database connection strings
- API keys and secrets
- Application configuration

**Never commit `.env` files to version control.**

---

## 📝 Notes

- The production server uses PostgreSQL as the database backend
- This API is designed to be used with a separate frontend application
- Nginx reverse proxy configuration will be added for public HTTPS access