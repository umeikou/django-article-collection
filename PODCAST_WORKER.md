# Xiaoyuzhou podcast worker

Podcast requests are stored in SQLite and are processed outside Gunicorn by exactly **one** worker. Do not start a second worker against the same SQLite database.

## Configuration

Install an audited copy of `fetch_episode.py` and `auralwise.py` in a worker-readable directory. Set `PODCAST_FETCH_SCRIPT`, `PODCAST_ASR_SCRIPT`, `PODCAST_PYTHON`, `PODCAST_TEMP_ROOT`, `PODCAST_CHILD_HOME`, and `PODCAST_CHILD_PATH` in the service environment or production settings. Never make `/root/.kiro` readable by the service account.

The ASR credential is supplied to the worker only as `AURALWISE_API_KEY`. AI configuration uses the existing `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, and `DEEPSEEK_BASE_URL`. Do not put credential values in this unit, source tree, logs, or shell history.

## Install and operate

After reviewing paths and creating the writable temporary/home directories with owner `nginx`, apply migrations:

```bash
python3 manage.py migrate --settings=article_collection_django.settings_production
sudo install -m 0644 podcast-collection-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now podcast-collection-worker
sudo systemctl status podcast-collection-worker
journalctl -u podcast-collection-worker -f
```

For a one-boundary recovery run, use `python3 manage.py process_podcast_tasks --once`. To stop the worker use `sudo systemctl stop podcast-collection-worker`. The worker lease expires after `PODCAST_LEASE_SECONDS`; a restarted single worker can then safely take unfinished work.

## Recovery and safety

The worker stores each metadata, ASR, transcript, and analysis boundary. ASR task IDs and signed audio URLs are not exposed through API events or admin. Paid/private episodes are rejected before ASR. Free episodes with missing audio URLs fail without ASR. Original audio is never downloaded or retained.

A failed retryable task can be retried by its owner. Cancellation stops local follow-up work; a submitted ASR task can still incur external charges. `needs_attention` means a submission or AI dispatch result is uncertain and is never automatically resent. A staff user must reconcile it through the API/admin procedure: attach a verified existing ASR task ID, abandon an uncertain ASR submission, or confirm a specific AI item was not dispatched. Review external billing manually; this system never recharges an account.

## Deployment notes (2026-11-17)

- SQLite journals are created next to the database file. Under `ProtectSystem=strict`, `ReadWritePaths` must include the **project directory** (not only `production.db`); otherwise the worker fails with `OperationalError: unable to open database file`. The installed unit therefore lists `/usr/Project/article_collection_django` plus the podcast temp/home directories.
- Credentials: `DEEPSEEK_*` come from the existing `.env` EnvironmentFile; `AURALWISE_API_KEY` is provided via `/etc/article-collection/podcast-worker.env` (640 root:nginx, outside the source tree).
- Audited skill scripts are installed at `/opt/article-collection/podcast-scripts/` (root-owned, nginx-readable), matching `PODCAST_SKILL_DIR` in production settings.
- After a successful ASR submit the worker releases its lease and schedules the next poll `PODCAST_ASR_POLL_SECONDS` later; immediate status polls right after submission can hit provider-side transient errors (`asr_status_temporary`), which now back off automatically instead of ending the task.
