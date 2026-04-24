# CLAUDE.md - English Learning App

## Security Rules

- **NEVER bind to 0.0.0.0** — always use `127.0.0.1` (localhost only)
- When starting any dev server, ALWAYS use `--host 127.0.0.1`
- Do NOT expose any port to the network; local access only
- If the user or any workflow needs a server, use: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8443 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem`
- Never use `--host 0.0.0.0` under any circumstances — this triggers security alerts

## Dev Server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8443 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

Access at: https://localhost:8443

## Test Commands

```bash
python -m pytest tests/ -v
```

## Import Lessons

```bash
PYTHONPATH=. python tools/import_lessons.py
```
