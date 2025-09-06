# Testing Plan – Gmail Smart Cleaner

## Objectives
- Validate safety: never modify protected or whitelisted emails.
- Ensure deterministic, conservative actions in dry-run and live modes.
- Verify end-to-end reporting, storage, and scheduling behavior.
- Keep external calls isolated via stubs/mocks with opt-in live tests.

## Test Scope & Environments
- Test types: Unit, Integration, optional System (manual/CI nightly).
- Environments:
  - Local dev: pytest with mocks; no real network by default.
  - CI: unit + integration on every PR; system tests behind secrets, scheduled.
  - Docker: build-and-run integration to validate container entrypoints.

## Tooling
- Pytest, pytest-cov, pytest-mock, freezegun, hypothesis (optional),
  tempfile for isolated FS, sqlite3 for ephemeral DB.
- Stubs over network: stub `GmailClient` and LLM layer directly (avoid HTTP).
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.system`,
  plus `slow`, `online`, `docker`.

## Cross-Cutting Concerns
- Safety rails: whitelists, protected labels, starred/important untouched.
- Idempotency: repeated runs should not re-apply actions or drift.
- Privacy: LLM gets only allowed fields; body truncation enforced.
- Limits: respect `max_messages_per_run`, `fetch_window_hours`.
- Timezones: schedule at local TZ; consistent with `TZ` env.
- Error handling: retries/backoff; partial failure still yields report.

---

## Unit Tests
Focus on pure logic and narrow adapters; mock external services.

### config.py
- load_config_defaults: missing keys → defaults applied.
- validate_schedule: invalid `time` or `timezone` raises descriptive error.
- expand_paths: relative paths expand relative to project root.

### logging_setup.py
- level_selection: verbosity maps to expected levels.
- formatter_structure: logs include run id and ISO timestamps.

### models.py
- enums_and_dataclasses: Action values, dataclass defaults behave as expected.

### policies.py
- whitelist_sender_domain: sender and domain detection (case/plus handling).
- protected_labels: starred/important and custom protected labels block actions.
- heuristics_newsletter: List-Unsubscribe or RFC headers → ARCHIVE recommendation.
- heuristics_spammy_subject: obvious spam patterns yield TRASH recommendation.
- policy_decide_precedence: whitelist > protected > heuristics > undecided.

### classifier.py
- llm_payload_redaction: truncates body to `max_body_chars`, excludes attachments.
- llm_conservative_defaults: low confidence → prefer ARCHIVE/LABEL over TRASH.
- decide_thresholds: threshold boundaries map to expected actions.
- error_mapping: LLM timeout/API error produces undecided classification.

### gmail_client.py
(Against a stub interface, not Google SDK.)
- modify_labels_idempotent: repeated calls don’t duplicate labels.
- archive_removes_inbox: `archive_message` removes `INBOX` only.
- trash_moves_only: `trash_message` moves to Trash; reversible semantics.
- send_email_renders: markdown to text/HTML produces both parts.

### storage.py
- last_run_roundtrip: set/get behavior with sqlite/tempfile.
- append_audit_records_appends: new rows appended immutably; count increases.

### reporter.py
- markdown_sections_present: counts, examples, errors sections rendered.
- save_report_path: saves to dated path; returns final location.

### engine.py
- decide_action_policy_wins: policy decision overrides LLM.
- dry_run_no_side_effects: no Gmail modifications when `dry_run: true`.
- counts_and_examples: decisions aggregate into correct counts/examples.
- error_propagation: failing one message logs error and continues.

### scheduler.py
- compute_next_run: next fire time respects TZ and daily time.
- run_once_executes: runner called exactly once.

### main.py
- cli_subcommands: `run` and `serve` parse; `--config` path handled.
- healthcheck: returns zero/non-zero appropriately.

---

## Integration Tests
Exercise multiple modules together with in-memory stubs; no real network.

### Fixtures
- GmailStub: in-memory mailbox with messages, labels, and state transitions.
- LLMStub: deterministic classifications by subject keywords and envelopes.
- Seed data: JSON/EML fixtures for newsletters, receipts, promos, and personal.

### Scenarios
- e2e_dry_run:
  - Given 20 mixed messages, when process_inbox in dry-run, then
    - no Gmail state changes, but report shows intended actions and counts.
- e2e_live_archive_trash:
  - With `action: trash` and safety rails, verify only non-protected messages are trashed,
    newsletters archived; audit entries appended; report saved + emailed via stub.
- idempotent_repeated_run:
  - Run twice on same seed; second run executes zero actions.
- limits_respected:
  - With `max_messages_per_run=10`, only first 10 processed; resume next day using `last_run`.
- timezone_schedule:
  - Configure TZ and daily time; using freezegun, verify scheduler triggers at expected wall-clock.
- error_and_retry:
  - GmailStub intermittently fails; engine retries then logs error; run completes with partial success.
- privacy_and_redaction:
  - Verify that LLMStub receives only subject, sender, snippet, and truncated body; no full thread.
- markdown_report_golden:
  - Compare generated report to a golden file template with placeholders for dates.

### Docker Integration
- Build image and run one-shot command:
  - `docker build -t cleanmail:dev .`
  - `docker run --rm -e TZ=Europe/Berlin -v $(pwd)/reports:/app/reports -v $(pwd)/data:/app/data cleanmail:dev run --dry-run`
  - Assert non-empty report file and zero exit code.
- Scheduler smoke:
- Start container with `serve` and an override to trigger immediately (test-only flag), ensure one run occurs.

---

## Optional System Tests (Live Gmail)
Opt-in, off by default; requires a dedicated test Gmail account and secrets.

### Preconditions
- Separate Gmail account (not your primary) with OAuth credentials and token.
- Seed mailbox with labeled messages for each category (whitelist, protected, newsletter, promo, spam, receipt, personal).
- Configure strict mode: start with `dry_run: true`.

### Steps
1) Seed messages:
   - Use SMTP or Gmail API to insert sample emails with characteristic headers (List-Unsubscribe, receipts).
2) Run container one-off with `dry_run: true`:
   - Verify no state changes; report emailed to test recipient and saved to disk.
3) Switch to `action: trash` with small scope (e.g., `max_messages_per_run=5`).
   - Verify only non-protected items moved to Trash; labels applied where expected.
4) Quarantine aging (optional):
   - Pre-populate Trash with older test emails; run cleanup; verify permanent delete only for >N days.
5) Cleanup:
   - Restore whitelisted messages; empty test Trash; remove test labels.

### Safeguards
- Never run against primary account.
- Use narrow Gmail queries during tests (e.g., `subject:"[TEST]"`).
- Enforce `dry_run` on first pass; require explicit flag to allow modifications.
- Rate limits: small batches; exponential backoff on 429/5xx.

---

## Test Data & Fixtures
- Location: `tests/fixtures/` with JSON message payloads and `.eml` samples.
- Golden reports under `tests/fixtures/reports/` with date placeholders like `{{DATE}}`.
- Factory helpers to construct `MessageSummary` quickly.

## CI Strategy
- PR: run `ruff` (later), unit + integration, coverage >= 85% for core logic.
- Nightly: optional system tests with secrets, `-m system`.
- Caching: pip cache; no external network in unit/integration.
- Artifacts: upload generated reports from integration runs for inspection.

## Running Tests Locally
- All: `pytest -q`
- Unit only: `pytest -m unit -q`
- Exclude slow/online: `pytest -m 'not slow and not online'`
- Coverage: `pytest --cov=src/cleanmail --cov-report=term-missing`

## Risks & Mitigations
- Flaky time-based tests → freezegun and deterministic TZ.
- LLM nondeterminism → stubbed classifier and golden outputs.
- Gmail API changes → wrapper abstraction and contract tests against stub.
- Data leakage in logs → explicit redaction in logging and tests asserting redaction.

## Exit Criteria
- Safety: unit tests for whitelist/protected labels and dry-run pass.
- Engine: end-to-end integration with golden report passes.
- Docker: image runs, generates report, exits 0 in dry-run.
- Optional: one successful system test in the dedicated account before enabling live trash.

