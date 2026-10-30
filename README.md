# Campus Code

A university programming lab for Python, C++, C, JavaScript, Java, Go, Ruby and SQLite SQL. Everyone can open a temporary guest workspace without email or login. Optional username/password accounts retain drafts across devices. Creating an account upgrades the current guest workspace, preserving its saved code.

**Current status:** the preview is deployed at https://167.233.140.202 with HTTPS and a gVisor worker. All 36 tests, including real execution and isolation checks, passed on the Linux server. The live HTTPS API was also checked for all eight languages, guest/account flows, saved drafts, reading progress and network denial. The local Mac still has no local worker, so running only the local web server returns an unavailable-runner error. This remains a small preview deployment, not a capacity-tested campus service.

## English learning centre

The main navigation opens `#lessons`, `#examples`, `#reference`, and `#algorithms` alongside `#compiler`. The original English starter curriculum includes:

- 32 lessons: four lessons per language, with explanations, full source, expected output, practice prompts and multiple-choice checks. SQL covers tables, filtering, aggregates and joins.
- 40 searchable, language-filtered code examples with source, stdin where relevant, and expected output. Each opens directly in the matching compiler editor after a replacement confirmation when necessary.
- 32 reference entries covering functions, methods and operators, with syntax, short examples and caveats.
- Eight DSA topics: linear/binary search, bubble sort, stack, queue, hash map, linked list and BFS. DSA examples use Python; binary search and bubble sort also have deterministic step controls.

Expected outputs are authored examples, not execution results. The algorithm step views illustrate fixed examples and do not interpret student code. Reading marks are self-tracked learning progress, not assessed grades. Progress is owned by the current guest/account in SQLite, migrates when a guest creates an account, and is removed during guest cleanup. Quizzes give local practice feedback and do not require the execution worker.

Curriculum source: `scripts/build_curriculum.py`. Regenerate with `python3 scripts/build_curriculum.py`; the browser reads `public/learning-data.json`. The server validates progress IDs against this same file. After changing curriculum IDs, restart the web server. This is a starter set of original English material, not a complete accredited course or copied Programiz course content.

To validate **reviewed, trusted bundled teaching examples** using installed local toolchains, developers can run `.venv/bin/python scripts/check_curriculum.py`. This script is not a student execution route, is never called by the web app, and must never be pointed at uploaded/student code. Student code remains exclusively behind the isolated worker.

## Local preview

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python server.py
```

Open http://localhost:8000. Default storage: `.data/campus.sqlite3` (ignored by Git). Run `server.py` only for local development; use Gunicorn behind HTTPS for student deployment. Starting the web app alone supports editing, guest sessions, optional accounts, examples and server-saved drafts. A missing secure worker returns HTTP 503; submitted code is never executed directly by the web host.

To attach an installed local Linux worker, configure the same random `RUNNER_TOKEN` in both services and start:

```sh
.venv/bin/gunicorn --bind 127.0.0.1:8001 --workers 1 --threads 4 --timeout 65 'sandbox_runner:create_runner()'
```

The web app defaults to `RUNNER_URL=http://127.0.0.1:8001`. See [sandbox setup](sandbox/README.md) for the image, gVisor, resource limits and mandatory execution tests.

## Accounts, privacy and limits

- No email collection, university domain restriction or invitation code. Usernames: 3–30 ASCII letters, digits or underscores; case insensitive. Passwords: 12–256 characters, salted scrypt hashes.
- Server-side random sessions, stored as SHA-256 token hashes; 12-hour expiry; HttpOnly, SameSite=Strict cookies, plus Secure under HTTPS. Login rotates the session and logout revokes it. Origin, Host and CSRF checks protect state-changing requests. No credentials or source code are written to request logs.
- Each account or guest gets one draft per language, checked by server-side ownership. Source code is not stored in shared-browser localStorage. Theme/language preferences can be stored locally. Named account drafts are not end-to-end encrypted; the server administrator can access the database. Shared computers should use “New workspace” or “Sign out” after each student.
- A guest workspace is tied to its browser cookie, is temporary, and cannot be recovered after the cookie/session is lost. Download code or create an account to keep it. Daily cleanup removes day-old guest accounts/drafts and audit records older than 90 days.
- Persistent limits across web workers: login attempts, guest/account creation (240 guest workspaces/hour and 120 registrations/15 minutes per IP by default), saves, 20 runs/minute and 500/day per workspace, 60 runs/minute per source IP. Use `GUESTS_PER_HOUR` and `REGISTRATIONS_PER_15_MIN` to tune onboarding. Shared university NATs may require tuning execution IP limits after load testing.
- One active run per user, four globally; stale leases expire. Code is limited to 60 KB, stdin to 16 KB, total request to 100 KB. SQLite storage is suitable for an initial small deployment; this is not a tested high-volume campus service.
- No email password reset. A lab administrator can reset a named account interactively or disable it; both revoke all sessions. There is no identity-verification flow, SSO, grading, assignment management or admin dashboard.

```sh
.venv/bin/python manage.py reset-password student_username
.venv/bin/python manage.py disable-user student_username
.venv/bin/python manage.py cleanup
```

Run management commands as the web service user, against the configured `DATABASE`. Verify student identity through your university process before performing account recovery.

## Deployment later

A server preview has been deployed; see `deploy/DEPLOYMENT.md` for its service layout and verification. The `deploy/` files remain reusable templates for future deployments. The university domain has not been selected.

For a dedicated Linux VM:

1. Install Docker/gVisor, Python 3.12+, and Caddy. Create separate `campus-web` and `campus-runner` service users. **Only** the runner belongs to the Docker group. Keep source owned by root, readable by the service users, and not writable by either.
2. Place the project in `/opt/campus-code`, create the virtual environment, and install `requirements.lock`. Build the sandbox image, run the full sandbox suite, and pin the resulting local image ID.
3. Generate a random token with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`. Put it in `/etc/campus-code/web.env` and `/etc/campus-code/runner.env` using the provided examples. File modes: 0640, root-owned and readable only by the corresponding service group. Replace the origin/domain and image ID. Never commit these files.
4. Install the systemd service, guest-retention timer and sandbox-reaper timer templates. The deployment templates use loopback ports 8010 (web) and 8011 (runner); this preserves other services such as the existing API on 8000. Keep the private worker port 8011 and Docker APIs inaccessible externally. The web app must never run under the Docker-enabled user.
5. Configure Caddy using the selected domain, with valid public DNS and HTTPS. Only ports 80/443 should be public. Production startup requires an HTTPS origin and strong worker token. ProxyFix trusts exactly one loopback reverse proxy; do not bind Gunicorn publicly.
6. Test real student flows, resource limits and concurrency on the chosen hardware before opening access. This project has not undergone an independent penetration test or capacity test.
7. Back up the database with SQLite's online backup API (do not copy only the live database without its WAL), protect backups, and test recovery. Run the cleanup timer. Monitor worker readiness, HTTP 429/503 rates, disk use and service logs. Patch dependencies, host, Docker and gVisor; rebuild/test the image regularly.

A separate runner VM is preferred as usage grows. Connect through an authenticated tunnel or restricted HTTPS as documented in `sandbox/README.md`. No student container receives host mounts or application secrets.

## Verification

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check public/app.js
node --check public/auth.js
```

The default suite exercises guest access, optional accounts, guest-to-account conversion, password storage, session rotation/revocation, ownership, request validation, CSRF/origin/host rejection, rate limits, production cookie settings, bounded worker output and missing-sandbox rejection. Real execution tests are explicitly skipped unless `RUN_SANDBOX_TESTS=1`; see the sandbox README.

Automatic delivery: pushes to `main` run the complete Linux/gVisor test suite and deploy through a dedicated restricted SSH key. See [deployment operations](deploy/DEPLOYMENT.md) for rollback and runtime upgrade limits.
