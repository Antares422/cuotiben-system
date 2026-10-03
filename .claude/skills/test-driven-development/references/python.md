# Python TDD Adaptations

Conventions for pytest projects, typically FastAPI + SQLAlchemy + ruff. The project's own rules (`CLAUDE.md`, a development-conventions doc, `pyproject.toml`, `conftest.py`) take precedence over this file.

## First: find what the project already has

Before the first cycle, read `pyproject.toml` (pytest options, registered markers, ruff config), `tests/conftest.py`, and the helper modules under `tests/`. Look for, and reuse:

- the database fixture and how it isolates tests (rollback per test, disposable container, SQLite);
- fakes for external services and helpers for inserting rows or asserting rejections;
- how the app is built for tests (an app factory) and how dependencies are overridden;
- the project's own pre-commit / CI test command.

Write a new fixture, fake, or helper only when nothing existing fits, and put it next to the existing ones.

## Commands

Run through the project's environment (`.venv/bin/python`, `uv run`, or the activated venv), never the system Python.

| Step | Command |
|---|---|
| RED / GREEN, one test | `python -m pytest tests/test_x.py::test_name -q` |
| Module after GREEN | `python -m pytest tests/test_x.py -q` |
| Before reporting done | the project's check command; typically `python -m ruff check .` and `python -m pytest -m "not integration"` |

Add `--strict-markers` when the project registers markers, so a misspelled marker fails instead of silently selecting nothing.

## Fast tests vs integration tests

- Tests are fast by default: deterministic, no Docker, no internet, no shared/UAT/production database, no local daemons, no developer environment variables.
- A test that needs Docker, a real database, Redis, object storage, or a third-party service carries the project's integration marker (e.g. `@pytest.mark.integration`, or module-level `pytestmark`), registered in `pyproject.toml`. Don't mark tests that don't need external resources.
- **Skipped is not RED and not GREEN.** Integration fixtures commonly skip when Docker or the database is unavailable. If the test you just wrote was skipped, you have not seen it fail or pass. Say so, and run it where the dependency exists before claiming the cycle.
- Database and migration tests run only against a disposable, isolated database. Never point tests at a shared, UAT, or production database, or at real business data.

## Test style

- Plain test functions with names that state the behavior: `test_login_url_points_to_accounts_host() -> None`.
- Match the project's typing and import conventions (e.g. `from __future__ import annotations`, typed fixtures).
- Expected errors: `with pytest.raises(SpecificError):` using the project's own exception types.
- Boundary cases for the same behavior: `@pytest.mark.parametrize` rather than copied tests.
- Follow the repo's comment language and density.

## External HTTP: fake the transport, not the client

Don't patch the client's methods. Give the real client an `httpx.Client(transport=httpx.MockTransport(handler))`, so its request building, parsing, and error handling are exercised:

```python
def handler(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/api/token/":
        return httpx.Response(200, json={"success": True})
    return httpx.Response(404)

client = SomeApiClient(
    base_url="https://api.example.com",
    http_client=httpx.Client(transport=httpx.MockTransport(handler)),
)
```

For a service with state (tokens, sessions, records), use a small in-memory fake class whose `handler` reads and writes a dict, fills in the defaults the real service adds, and has switches to make specific endpoints fail. Reuse the project's existing fake if there is one. `requests`-based code: use `responses` or the project's equivalent in the same spirit.

## FastAPI endpoints

- Build the app with the project's app factory and use `TestClient`; replace dependencies with `app.dependency_overrides[get_x] = lambda: ...`.
- Configuration comes from `monkeypatch.setenv(...)` with test values, never the real environment. A new environment variable also goes into `.env.example` and the config module.
- Assert the full response contract the project defines (status code, envelope fields, error identifier), not just the status code.
- Each new endpoint needs success, failure, and boundary tests; permission checks and state transitions need a test for the rejected path. Put these on the test list before the first cycle.

## Database

- Use the project's per-test isolation (typically a connection whose transaction is rolled back after each test), so tests don't clean up after themselves.
- Assert constraint violations inside a SAVEPOINT (`with conn.begin_nested():` under `pytest.raises(IntegrityError)`), so one test can check several rejected writes without aborting the outer transaction.
- Schema changes go through new migration files; the RED test for a new constraint is a write that should be rejected.

## Time and randomness

Give code that depends on the current time a `now` parameter or clock, and pass tests a fixed `datetime(..., tzinfo=timezone.utc)`, so expiry and TTL boundaries can be tested exactly (just before, at, just after). Seed or inject randomness the same way.
