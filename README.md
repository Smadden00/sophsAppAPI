# sophsAppAPI

A Flask-based REST API backed by PostgreSQL and deployed with **Gunicorn**, **systemd**, and **Nginx** in a production-ready configuration. Designed for security, resilience, and scalability.

---

## 🚀 Quick Reference

| Component | Details |
|-----------|---------|
| **systemd Service** | `/etc/systemd/system/sophsAppApi.service` |
| **Gunicorn Binding** | `http://127.0.0.1:5000` |
| **Public Entry** | `http://<host>/api/*` (via Nginx) |
| **Health Check** | `GET /api/health` |

---

## 📋 Table of Contents

- [Overview](#overview)
  - [Architecture](#architecture)
  - [Application Structure](#application-structure)
- [Installation & Setup](#installation--setup)
  - [1. Python Environment](#1-python-environment)
  - [2. Gunicorn Setup](#2-gunicorn-setup)
  - [3. systemd Service](#3-systemd-service)
  - [4. Nginx Reverse Proxy](#4-nginx-reverse-proxy)
- [Service Management](#service-management)
- [Monitoring & Logs](#monitoring--logs)
- [Health Checks](#health-checks)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Overview

This project exposes a Flask REST API using a production-grade server stack for reliable, secure operation.

**Technology Stack:**
- 🐍 **Flask** – Application framework
- 🦄 **Gunicorn** – WSGI application server
- ⚙️ **systemd** – Process supervision and lifecycle management
- 🌐 **Nginx** – Public-facing reverse proxy
- 🐘 **PostgreSQL** – Database backend

### Architecture

```
Client Request
      ↓
Nginx (Port 80/443)
      ↓
Gunicorn (127.0.0.1:5000)
      ↓
Flask Application
      ↓
PostgreSQL Database
```

**This layered design provides:**
- ✅ Reduced attack surface
- ✅ Improved stability under load
- ✅ Foundation for HTTPS, rate limiting, and logging
- ✅ Clean separation of concerns

### Application Structure

The Flask app uses the **application factory pattern**.

**Entry Point (`run.py`):**
```python
from app import create_app
app = create_app()
```

Gunicorn loads the application via: `run:app`

**Key Benefits:**
- Database and extensions initialized inside `create_app()`
- Blueprints registered during app creation
- Environment-specific configuration loaded at runtime
- Easy testing and multiple app instances

---

## Installation & Setup

### 1. Python Environment

**Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
pip install gunicorn
```

All runtime dependencies (Flask, SQLAlchemy, psycopg2, python-dotenv, etc.) are installed in the same environment.

### 2. Gunicorn Setup

Gunicorn serves as the production WSGI server, managing worker processes and handling HTTP requests.

**Configuration:**
| Setting | Value |
|---------|-------|
| Workers | 3 processes |
| Binding | `127.0.0.1:5000` |
| Environment | Loaded from `.env` file |
| Command | `gunicorn --workers 3 --bind 127.0.0.1:5000 run:app` |

**Manual test:**
```bash
gunicorn --workers 3 --bind 127.0.0.1:5000 run:app
```

> **Note:** Gunicorn binds only to localhost. Nginx acts as the public-facing proxy.

### 3. systemd Service

systemd manages Gunicorn as a persistent background service.

**Service File Location:**
```
/etc/systemd/system/sophsAppApi.service
```

**Service Benefits:**
- ✅ Starts automatically on server boot
- ✅ Restarts automatically if it crashes
- ✅ Runs independently of SSH sessions
- ✅ Centralizes logs via `journalctl`

**Key Configuration:**
- Runs as a non-root user
- Sets working directory to project root
- Loads environment variables from `.env` file
- Automatically restarts on failure

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable sophsAppApi
sudo systemctl start sophsAppApi
```

### 4. Nginx Reverse Proxy

Nginx serves as the public-facing web server, proxying requests to Gunicorn.

**Purpose:**
- 🌐 Terminates client connections
- 🔒 Shields Gunicorn from direct exposure
- 🚀 Enables HTTPS, rate limiting, and caching
- 📊 Provides request logging

**Installation:**
```bash
# Amazon Linux
sudo yum install nginx -y

# Ubuntu
sudo apt install nginx -y
```

**Configuration File Location:**
```
/etc/nginx/conf.d/api.conf
```

**Example Configuration:**
```nginx
server {
    listen 80;
    server_name _;

    # Match Flask MAX_CONTENT_LENGTH
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;

        # Preserve client information
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

**Validate and apply:**
```bash
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl start nginx
```

---

## Service Management

### Gunicorn Service Commands

| Action | Command |
|--------|---------|
| **Start** | `sudo systemctl start sophsAppApi` |
| **Stop** | `sudo systemctl stop sophsAppApi` |
| **Restart** | `sudo systemctl restart sophsAppApi` |
| **Status** | `sudo systemctl status sophsAppApi` |
| **Enable on boot** | `sudo systemctl enable sophsAppApi` |

### Nginx Service Commands

| Action | Command |
|--------|---------|
| **Start** | `sudo systemctl start nginx` |
| **Stop** | `sudo systemctl stop nginx` |
| **Restart** | `sudo systemctl restart nginx` |
| **Reload config** | `sudo systemctl reload nginx` |
| **Status** | `sudo systemctl status nginx` |
| **Test config** | `sudo nginx -t` |

### When to Restart Gunicorn

Restart the API service after changes to:

- ✏️ Flask application code
- 🔧 Environment variables (`.env` file)
- 📦 Python dependencies (`requirements.txt`)
- ⚙️ Configuration files (database, uploads, etc.)

**Typical deployment workflow:**
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sophsAppApi
```

### When to Reload/Restart Nginx

**Reload** (no downtime) after:
- Configuration file changes
- Certificate updates

**Restart** (brief downtime) after:
- Nginx installation or major updates
- Module changes

Always validate first:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Monitoring & Logs

### Gunicorn Logs (via systemd)

Gunicorn stdout/stderr is captured by systemd's journal.

**View recent logs:**
```bash
sudo journalctl -u sophsAppApi -n 200
```

**Follow logs in real-time:**
```bash
sudo journalctl -u sophsAppApi -f
```

**View logs from specific time:**
```bash
sudo journalctl -u sophsAppApi --since "1 hour ago"
sudo journalctl -u sophsAppApi --since "2024-12-01"
```

### Nginx Logs

Nginx maintains separate access and error logs.

**Access log (incoming requests):**
```bash
sudo tail -f /var/log/nginx/access.log
```

**Error log (proxy issues, config errors):**
```bash
sudo tail -f /var/log/nginx/error.log
```

> **Tip:** Check Nginx error logs first when experiencing 502 Bad Gateway errors.

---

## Health Checks

The API exposes a health endpoint to verify system status.

**Endpoint:**
```
GET /api/health
```

**Test via Gunicorn directly:**
```bash
curl http://127.0.0.1:5000/api/health
```

**Test via Nginx (public):**
```bash
curl http://<your-server-ip>/api/health
```

**Successful response confirms:**
- ✅ Gunicorn service is running
- ✅ Flask application loaded correctly
- ✅ Database connection is healthy
- ✅ Nginx proxy is working (when testing via public endpoint)

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

**⚠️ Critical:** Never commit `.env` files to version control. Add to `.gitignore`.

### Best Practices

- 🔒 Run services as non-root users
- 🔒 Keep dependencies updated (`pip list --outdated`)
- 🔒 Use HTTPS in production (Let's Encrypt / Certbot)
- 🔒 Implement rate limiting at Nginx level
- 🔒 Regular security audits and log monitoring
- 🔒 Restrict EC2 security group rules to necessary ports only

---

## Troubleshooting

### 🔴 502 Bad Gateway (Nginx → Gunicorn)

**Symptoms:** Nginx returns 502 error

**Checklist:**
1. Confirm Gunicorn is running:
   ```bash
   sudo systemctl status sophsAppApi
   ```

2. Verify Gunicorn binding:
   ```bash
   sudo ss -tulpn | grep 5000
   ```
   Should show `127.0.0.1:5000`

3. Check Nginx configuration:
   ```bash
   sudo nginx -t
   ```
   Ensure `proxy_pass` matches `http://127.0.0.1:5000`

4. Review Nginx error logs:
   ```bash
   sudo tail -50 /var/log/nginx/error.log
   ```

### 🔴 Nginx Configuration Errors

**Symptoms:** Nginx won't start or reload

**Solution:**
```bash
sudo nginx -t
```

Fix any reported syntax errors, then:
```bash
sudo systemctl restart nginx
```

### 🔴 API Works Locally but Not Publicly

**Checklist:**
1. Verify EC2 security group allows inbound traffic on port 80
2. Confirm Nginx is listening:
   ```bash
   sudo ss -tulpn | grep nginx
   ```
3. Check Nginx access log for incoming requests:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```
4. Test Nginx → Gunicorn connection:
   ```bash
   curl http://127.0.0.1:5000/api/health
   ```

### 🔴 Environment Variable Issues

**Symptoms:** App fails with missing configuration

**Solution:**
1. Verify `.env` file exists in project root
2. Check systemd service file loads `.env`:
   ```bash
   sudo systemctl cat sophsAppApi
   ```
   Should have `EnvironmentFile=` directive
3. Restart service:
   ```bash
   sudo systemctl restart sophsAppApi
   ```

### 🔴 Database Connection Failures

**Checklist:**
1. Verify PostgreSQL is running
2. Check database credentials in `.env`
3. Test connection from application server
4. Review Gunicorn logs:
   ```bash
   sudo journalctl -u sophsAppApi -n 100
   ```

---

## Next Steps

### Planned Enhancements

- 🔐 **HTTPS Setup** – Configure SSL/TLS with Let's Encrypt (Certbot)
- 🔁 **HTTP → HTTPS Redirect** – Enforce secure connections
- 🚦 **Rate Limiting** – Protect against abuse at Nginx level
- 📊 **Enhanced Monitoring** – Integration with monitoring tools
- 🧱 **WAF Integration** – Web Application Firewall for additional security
- ⚡ **CDN Integration** – Content delivery optimization
- 🔄 **Auto-scaling** – Load balancer and multiple instances

---

## 📝 Notes

- Production server runs on Amazon Linux 2 / Ubuntu
- Database: PostgreSQL with connection pooling
- Frontend: Separate application consuming this API
- All times in logs are UTC
- API is RESTful and returns JSON responses

---

## HTTPS & Domain Setup

### Overview

HTTPS was configured using **Let's Encrypt**, a free and trusted Certificate Authority. Since HTTPS requires a hostname (not an IP address), a free DNS subdomain was configured to point to the EC2 instance.

**Request Flow with HTTPS:**
```
Client (Browser)
      ↓
HTTPS (Port 443)
      ↓
Nginx (TLS Termination)
      ↓
Gunicorn (127.0.0.1:5000)
      ↓
Flask API
      ↓
PostgreSQL
```

> **Note:** Gunicorn remains private and inaccessible from the internet. All public traffic enters through Nginx over HTTPS.

---

### Domain & DNS Configuration

#### Free Domain Provider

A free **DuckDNS** subdomain is used (e.g., `example.duckdns.org`).

**DuckDNS Benefits:**
- 🆓 Free subdomains
- 🌐 Valid DNS records
- 🔒 Compatible with Let's Encrypt
- ⚡ Quick setup and updates

**Configuration:**
1. DuckDNS hostname points to EC2 instance's public IP
2. DNS records propagate globally within minutes

> ⚠️ **Important:** If the EC2 instance is stopped/restarted without an Elastic IP, the public IP will change and DNS must be updated in the DuckDNS dashboard.

#### Nginx HTTPS Configuration

Nginx listens on both HTTP (80) and HTTPS (443) ports.

**Key Configuration Points:**
- `server_name` set to DuckDNS hostname
- Requests proxied to Gunicorn on `127.0.0.1:5000`
- Client headers preserved (`Host`, `X-Forwarded-*`)
- Request body size matches Flask `MAX_CONTENT_LENGTH`
- HTTP automatically redirects to HTTPS

---

### HTTPS Certificates (Let's Encrypt + Certbot)

**Certbot** automates certificate management from Let's Encrypt.

**Certbot Functions:**
- 📜 Requests TLS certificates from Let's Encrypt
- ⚙️ Automatically configures Nginx
- 🔁 Enables HTTP → HTTPS redirects
- 🔄 Sets up automatic certificate renewal

**Certificate Details:**
- Valid for 90 days
- Automatically renewed via systemd timers
- Trusted by all major browsers

**Test the API:**
```bash
https://<hostname>/api/health
```

---

## Debugging HTTPS & DNS Issues

When HTTPS stops working, the issue is typically one of two things:
1. DNS pointing to wrong EC2 instance
2. Expired or invalid HTTPS certificate

### 🔍 Debugging DNS (DuckDNS → EC2)

**Goal:** Confirm hostname resolves to correct EC2 public IP.

**Check DNS resolution:**
```bash
nslookup example.duckdns.org
# or
dig example.duckdns.org
```

**Expected Result:** Returned IP matches your EC2 public IP

**If IP does NOT match:**
1. DuckDNS record points to wrong IP
2. Update DuckDNS dashboard with correct EC2 public IP
3. Wait 1-5 minutes for propagation
4. Retry DNS lookup

**Test connectivity:**
```bash
curl http://example.duckdns.org
```

**If DNS is incorrect, requests will:**
- ⏱️ Hang or timeout
- ❌ Hit wrong server
- 🚫 Fail entirely

---

### 🔐 Debugging HTTPS Certificate Issues

If DNS is correct but HTTPS fails, check the certificate.

#### Check Certificate Status
```bash
sudo certbot certificates
```

**Look for:**
- Certificate name
- Expiry date
- Domains covered

> If certificate is expired or missing, HTTPS will fail.

#### Test Auto-Renewal
```bash
sudo certbot renew --dry-run
```

**If this fails, check:**
- ❌ Certbot cannot reach server on port 80
- ❌ Nginx is not running
- ❌ Security group blocking port 80

#### Check Nginx Status
```bash
sudo systemctl status nginx
sudo nginx -t
```

**View error logs:**
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

> Certificate-related errors typically appear clearly in the error log.

---

### 🛠️ Quick Diagnostic Reference

| Symptom | Likely Cause |
|---------|-------------|
| `nslookup` returns wrong IP | DNS misconfigured |
| HTTP works, HTTPS fails | Certificate issue |
| Browser: "certificate expired" | Certbot renewal failed |
| `certbot renew --dry-run` fails | Port 80 blocked or Nginx misconfigured |
| `curl https://...` times out | DNS or security group issue |

---

### Useful Commands

**Reload Nginx (no downtime):**
```bash
sudo systemctl reload nginx
```

**Restart Nginx:**
```bash
sudo systemctl restart nginx
```

**Check Certbot renewal timers:**
```bash
sudo systemctl list-timers | grep certbot
```

**Force certificate renewal:**
```bash
sudo certbot renew --force-renewal
```

---

### Security Notes

- 🔒 Gunicorn bound to `127.0.0.1` (not publicly accessible)
- 🔒 Only ports 80 and 443 exposed publicly
- 🔒 TLS termination occurs at Nginx layer
- 🔒 Certificates trusted by all major browsers
- 🔒 Automatic HTTPS redirects enforce secure connections


