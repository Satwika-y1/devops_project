# 🍴 FoodieHub - Online Food Ordering System with Automated CI/CD Pipeline

A food-ordering website (Flask + SQLite) used to demonstrate real DevOps practice: **Git/GitHub, automated tests (pytest), Continuous Integration (GitHub Actions), Docker containerization, and Continuous Deployment (GitHub Actions → Render free tier).**

## 1. Overview, objectives, use case
Restaurants need a simple way to take orders online. This project builds that application and wraps it in an automated pipeline: every change pushed to GitHub is tested automatically, and only code that passes can be deployed.

**Objectives:** build a working app • test it automatically • package it in a container • automate build/test/deploy.

## 2. Features
Menu of 10 items • search + category filter • cart (add / remove / update quantity) • backend-calculated totals • checkout with server-side validation • orders + order items saved in SQLite • confirmation page with unique order ID (`ORD-XXXXXXXX`) • order history • success/error messages • **demo payment notice (no real payments)**.

**Stack:** HTML/CSS/JS + Bootstrap 5 (CDN) • Python Flask • SQLite • pytest • Git/GitHub • GitHub Actions • Docker + Gunicorn • Render (free).

## 3. Architecture
```
 Browser ──HTTP──▶ Gunicorn ──▶ Flask app (app.py) ──▶ SQLite (database.py)
                                   │                      menu_items / orders / order_items
                                   └── Jinja templates + static CSS/JS
```

## 4. DevOps concepts implemented
| Concept | Where | What it does |
|---|---|---|
| Version control | `.gitignore`, GitHub repo | Tracks every change; keeps venv, `.db`, `.env` out of Git |
| Automated testing | `tests/` | 37 pytest tests, each using a temporary DB |
| **CI** | `.github/workflows/ci.yml` | On push/PR to `main`: checkout → Python 3.12 → install → syntax + import check → pytest. Any failure = red ✗ |
| Containerization | `Dockerfile`, `.dockerignore` | Gunicorn on `0.0.0.0:8000`, non-root user, SQLite in `/data` volume, no secrets in image |
| **CD** | `.github/workflows/deploy.yml`, `render.yaml` | After CI succeeds on `main`, calls a Render deploy hook stored as a GitHub secret |

**CI vs CD:** *Continuous Integration* = automatically build and test every change. *Continuous Delivery/Deployment* = automatically release tested code to a server.

### Pipeline flow
```
Developer ─ git push ─▶ GitHub ─▶ CI workflow
                                   ├─ install deps
                                   ├─ syntax/import check
                                   └─ pytest ──✗ fail → STOP (red ✗, nothing deployed)
                                              └✓ pass → Deploy workflow → Render deploy hook → Live site
```

## 5. Folder structure
```
food-ordering-system/
├── app.py  database.py  requirements.txt  render.yaml
├── Dockerfile  .dockerignore  .gitignore  .env.example
├── templates/ (base, index, cart, checkout, confirmation, orders, error .html)
├── static/css/style.css   static/js/script.js
├── tests/ (conftest.py, test_app.py)
└── .github/workflows/ (ci.yml, deploy.yml)
```

## 6. Run locally (Windows PowerShell)
Prerequisites: Python 3.12+ (tick "Add to PATH"), Git, VS Code; Docker Desktop for the container step.
```powershell
cd food-ordering-system
python -m venv venv
venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. The database `instance/food.db` is created automatically.
Optional: `$env:SECRET_KEY="any-long-random-text"` before `python app.py` (otherwise a random key is used and carts reset on restart).

## 7. Run tests
```powershell
python -m pytest -v
```
Expected: `37 passed`. Tests use a temporary database, so your real data is never touched.

## 8. Docker
```powershell
docker build -t food-ordering .
docker volume create food-data
docker run -d --name food -p 8000:8000 -e SECRET_KEY="change-me-long-random" -v food-data:/data food-ordering
```
Open http://localhost:8000 (health check: http://localhost:8000/health). Orders survive restarts because the DB lives in the `food-data` volume.
Stop/remove: `docker stop food; docker rm food`. Logs: `docker logs food`.

## 9. Push to GitHub
Create an **empty** repo on github.com (no README), then:
```powershell
git init
git branch -M main
git add .
git commit -m "Initial commit: food ordering system with CI/CD"
git remote add origin https://github.com/<your-username>/food-ordering-system.git
git push -u origin main
```
Run `git status` first: `venv/`, `instance/`, `*.db`, `.env` must not be listed.

## 10. Inspect GitHub Actions
Repo → **Actions** tab → "CI - Test Food Ordering System" → click a run → click the job to see each step. Green ✓ = all passed. Optional badge:
`![CI](https://github.com/<user>/food-ordering-system/actions/workflows/ci.yml/badge.svg)`

## 11. Deployment (Render free tier) - one-time manual setup
**Limitations (from Render's docs):** free web services exist (512 MB RAM, 750 free hours/month, idle services sleep so the first request is slow). The free filesystem is **ephemeral**: SQLite data is lost on every restart/redeploy, and persistent disks need a paid plan. So the deployed demo's order history resets, which is acceptable for a demo. For permanent data, use a paid Render disk (set `DATABASE_PATH` to the mount path) or a managed database (needs code changes). Re-check Render's current pricing before submission.

Steps:
1. Push the repo to GitHub (section 9) and confirm CI is green.
2. On render.com sign up → **New → Blueprint** → select your repo (uses `render.yaml`: Docker, free plan, **auto-deploy off**, generated `SECRET_KEY`). Alternatively **New → Web Service**, runtime Docker, free instance, auto-deploy **No**, health check path `/health`.
3. Render service → **Settings → Deploy Hook** → copy the URL (it is a secret).
4. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret** → name `RENDER_DEPLOY_HOOK_URL`, value = the hook URL.
5. Push any commit to `main`. CI runs; if green, "CD - Deploy to Render" runs and triggers a deploy. Site: `https://<service-name>.onrender.com`.

Never paste the hook URL into code or chat. If the secret is missing, the deploy job fails with a clear message (CI still works).

## 12. DevOps Demonstration
1. `python app.py` → open the site.
2. Browse/search/filter → add items → cart → update quantity → checkout (Name `Asha Rao`, Phone `9876543210`, any address of 10+ characters) → show the order ID → open Order History.
3. `python -m pytest -v` → show 37 passing tests.
4. `docker build` and `docker run` (section 8) → open http://localhost:8000.
5. Edit the hero text in `templates/index.html`, then `git add .; git commit -m "Update hero text"; git push`.
6. Open the **Actions** tab → watch CI run.
7. Show the green ✓. **To demonstrate failure:** change `"₹249.00"` expectation in `tests/test_app.py` to a wrong value, push → red ✗ → the Deploy workflow does **not** run. Revert afterwards.
8. If configured, show the live Render URL updating.

### Viva questions
1. **What is DevOps?** Practices and culture that automate building, testing and releasing software so development and operations work together.
2. **CI vs CD?** CI automatically builds/tests every commit; CD automatically delivers tested code to a server.
3. **Why GitHub Actions?** Built into GitHub, free for small projects, configured by a YAML file in the repo.
4. **What triggers your pipeline?** A push or pull request to `main`.
5. **What if a test fails?** The workflow turns red and the deploy workflow is skipped, so broken code isn't released.
6. **Why Docker?** It packages the app with its dependencies so it runs the same everywhere.
7. **Why a Docker volume?** Container files vanish when it is removed; a volume keeps the SQLite DB.
8. **Why Gunicorn, not `flask run`?** Flask's dev server isn't meant for production; Gunicorn is a production WSGI server.
9. **How are secrets kept safe?** Environment variables locally/in Docker and GitHub Secrets in CI/CD; `.env` is git-ignored.
10. **Why compute totals on the backend?** Browser data can be tampered with; the server reads prices from the database.

**How this shows DevOps in the real world:** one `git push` triggers automated testing and, if it passes, automated deployment, the same loop real software teams use.

## 13. Troubleshooting
- `Activate.ps1 cannot be loaded` → `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- `python` not found → reinstall Python with "Add to PATH", or use `py`.
- Port in use → `$env:PORT=5001; python app.py`.
- Docker "daemon not running" → start Docker Desktop.
- Deploy job says secret not set → do step 4 of section 11.
- Render site slow at first → free instances sleep when idle.

## 14. Limitations and future work
No login/admin panel • demo-only payment • SQLite is ephemeral on Render free • single Gunicorn worker • future: PostgreSQL, admin dashboard, sandbox payment gateway, publish Docker image to GHCR, coverage/linting in CI.
