# Production deployment — 2026-10-30

Public URL: https://autplatform.uz/#compiler
Learning centre: https://autplatform.uz/#lessons

## Services

- Initial source and shared virtual environment: `/opt/campus-code`, root-owned. Active source is selected by `/opt/campus-current`; automatic releases live in `/opt/campus-releases`.
- Web: `campus-web.service`, user `campus-web`, `127.0.0.1:8010`, 512 MiB service memory limit. The web account has no Docker group access.
- Worker: `campus-runner.service`, user `campus-runner`, `127.0.0.1:8011`. The owner explicitly approved this account's root-equivalent Docker-group access. The bearer token is private in `/etc/campus-code/{web,runner}.env`; never commit or display those files.
- Student code: disposable gVisor `runsc` containers. The tested image is pinned by its immutable image ID in the worker environment.
- Limits: two simultaneous runs globally, one per workspace; existing per-user/IP quotas also apply. Each container has 1 CPU, 512 MiB RAM, no external network, no host mounts, read-only root, bounded tmpfs/output, and a non-root UID.
- Database: `/var/lib/campus-code/campus.sqlite3`, owned by `campus-web`. Local development accounts were not uploaded.
- Maintenance: `campus-cleanup.timer` removes expired guest data and `campus-reaper.timer` removes stale labeled sandbox containers.
- Reverse proxy: existing Nginx, configuration `/etc/nginx/sites-available/campus-code`. HTTP redirects to HTTPS, while the ACME challenge path stays available.
- Existing Logistics API on port 8000 and the two active GitHub Actions runner services remain running.

## HTTPS

A publicly trusted Let's Encrypt certificate for `autplatform.uz` and `www.autplatform.uz` is installed as `autplatform.uz`. Both HTTP and www redirect to the canonical HTTPS domain. The old IP also redirects and retains its short-lived `campus-ip` certificate. The updated Certbot client is in `/opt/campus-acme`. The existing Certbot timer invokes that client through `/etc/systemd/system/certbot.service.d/campus-code.conf`. A deploy hook validates and reloads Nginx after renewal. A simulated renewal succeeded. No self-signed certificate or browser certificate bypass is used.

## Verification completed

- 36 unit/integration tests passed on the Linux server, with **no skipped sandbox tests**.
- All eight languages returned the expected result through the public HTTPS API.
- Tested guest access, guest-to-account conversion, login/logout, secure cookies, draft persistence and reading-progress persistence.
- Verified network denial through the public execution API.
- Real sandbox suite checked host file isolation, root filesystem writes, memory limits, timeouts, output flooding and disposable filesystems.
- Browser loaded the site over HTTPS without a certificate warning; a lesson example ran successfully in the compiler. Browser error log was empty.
- Service listeners were verified: public Nginx on 80/443, internal web/worker on loopback only.

## Operations

```sh
systemctl status campus-web campus-runner
journalctl -u campus-web -u campus-runner -n 100 --no-pager
systemctl restart campus-web campus-runner
systemctl list-timers campus-cleanup.timer campus-reaper.timer certbot.timer
```

Use the web service user and the configured database path for account recovery commands. Before later code updates, back up SQLite using its online backup API and retain a tested release for rollback. This preview does not yet have an off-server backup, an independent penetration test or a classroom capacity benchmark. Do not promise unlimited concurrent students.

## GitHub CI/CD

Repository: https://github.com/Shahzod1602/program_simulator

Pull requests and pushes to `main` run the full suite on a fresh GitHub-hosted Ubuntu runner, including a Docker image build and actual gVisor execution tests. A successful push to `main` deploys automatically; `workflow_dispatch` on `main` can redeploy. The unrelated existing self-hosted runners are not used.

The `production` environment holds `DEPLOY_KEY` and `DEPLOY_KNOWN_HOSTS`. A dedicated Ed25519 key connects as `campus-deploy`, with SSH forwarding, PTY and arbitrary shell commands disabled. Sudo permits only the root-owned `/usr/local/sbin/campus-deploy` receiver without arguments. Treat this deployment key as privileged: deployed worker code runs under the explicitly approved Docker-enabled worker account.

The receiver accepts a size-bounded tar stream, rejects links, hidden paths and traversal, and never runs repository installation scripts as root. Dependencies and sandbox image definitions must match the administrator-installed baseline; changes to these files deliberately stop deployment until an administrator updates and tests the runtime. CI/CD currently deploys application source and learning content; it does not replace the OS, proxy, runtime image or environment secrets.

Each deployment backs up SQLite consistently to `/var/backups/campus-code` (latest five retained), selects a fresh root-owned release, restarts web/worker and checks the health endpoint. A failed startup restores the previous source release automatically. Current and previous releases are retained. Database backups are not automatically restored: schema changes must remain compatible with rollback.

Manual source rollback (administrator): point `/opt/campus-current` at the previous retained release and restart `campus-web` and `campus-runner`. Deployment failures appear in the GitHub Actions log. Do not put keys, production environment files, database copies or account data in the repository.
