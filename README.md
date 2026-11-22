# Course Catalog DaaS (CSE540 Lab 8)

A small Data-as-a-Service application: a SQLite course-catalog database exposed
through a read-only REST/JSON API built with Flask.

## Files
| File | Purpose |
|---|---|
| `seed_db.py` | Creates `courses.db` (30 synthetic courses, fixed random seed) |
| `app.py` | Flask API (retrieve / search / aggregate endpoints) |
| `test_clients.py` | Concurrent multi-client test and latency summary |
| `Dockerfile`, `Procfile`, `render.yaml` | Deployment options |
| `report_template.md` | Report skeleton matching Lab 8 items 4(a)-(e) |

## Run locally
```bash
pip install -r requirements.txt
python seed_db.py
python app.py                      # http://127.0.0.1:5000
# or: gunicorn app:app
```

## API
| Endpoint | Description |
|---|---|
| `GET /health` | Liveness + row count |
| `GET /api/courses` | List/search. Params: `q`, `department`, `level`, `semester`, `instructor`, `min_credits`, `max_credits`, `available=true`, `sort`, `order`, `limit` (max 100), `offset` |
| `GET /api/courses/<code>` | One course by code |
| `GET /api/departments` | Course count and average credits per department |
| `GET /api/stats` | Totals plus breakdown by semester and level |

Examples:
```bash
curl "http://127.0.0.1:5000/api/courses?q=cloud"
curl "http://127.0.0.1:5000/api/courses?department=CSE&level=300&sort=title"
curl "http://127.0.0.1:5000/api/courses/CSE168"
```
Errors return JSON: `400` bad parameter, `404` unknown course, `405` non-GET method.

## Deploy
**Render (no card needed for free tier):** push this folder to a GitHub repo, create a
*New Web Service* from it, and Render reads `render.yaml`. Public URL appears when the build finishes.

**Docker (any host):**
```bash
docker build -t course-daas .
docker run -p 8000:8000 course-daas
```

## Test from multiple clients
```bash
python test_clients.py https://<your-url> --clients 10 --rounds 5
```
Also open the URL from a browser, from `curl`, and from your phone to show different clients.
