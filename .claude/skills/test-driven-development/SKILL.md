---
name: test-driven-development
description: >
  TDD workflow: enforces Red-Green-Refactor cycle, test-first rules, and
  verification steps. Only trigger when the user explicitly invokes
  /test-driven-development or says "使用tdd" / "用tdd". Do NOT auto-trigger
  on general coding requests like "implement", "add", "fix", or "write".
---

# Test-Driven Development (TDD)

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Wrote production code in this session before its test? Delete that code and start the cycle over — don't keep it as a reference or adapt it into the test. Code you wrote first shapes the test to fit it, which is exactly what TDD exists to prevent.

This applies to code you write. Code the user already has (uncommitted or not) is never deleted under this rule; cover it with tests as described in [Existing code without tests](#existing-code-without-tests).

## When to Use

**Always:** New features, bug fixes, refactoring, behavior changes

**Exceptions (only with the user's agreement):** Throwaway prototypes, generated code, configuration files

## Before the First Cycle

1. **Find the project's test command** and how to run a single test (the build file, `package.json` scripts, `pytest.ini`/`pyproject.toml`, `Makefile`, CI config). Use the project's runner, not a new one.
2. **Run the relevant existing tests once.** If they already fail, tell the user before starting — otherwise a pre-existing failure gets mistaken for your RED or your regression.
3. **Write a short test list** for the task: the behaviors to cover, simplest first. Work through it one behavior per cycle; add to it as new cases come up rather than widening the current test.

## Red-Green-Refactor

### RED — Write Failing Test

Write one minimal test showing what should happen. Illustrative (Java/JUnit; use the project's own language and framework):

```java
@Test
void retriesFailedOperations3Times() {
    AtomicInteger attempts = new AtomicInteger(0);

    String result = RetryUtil.retryOperation(() -> {
        if (attempts.incrementAndGet() < 3) throw new RuntimeException("fail");
        return "success";
    });

    assertThat(result).isEqualTo("success");
    assertThat(attempts.get()).isEqualTo(3);
}
```

Requirements: one behavior, clear name, real code (no mocks unless unavoidable).

### Verify RED — Watch It Fail

Run only the new test (e.g. `mvn test -Dtest=RetryUtilTest`, `pytest path::test_name`, `npx vitest run -t "name"`, `go test -run TestName ./pkg`).

- It must fail on an assertion, with a message that points at the missing behavior.
- Compile or import error because the function doesn't exist yet? That is not RED yet. Add the minimal signature (a stub that returns a default or throws "not implemented"), rerun, and get the assertion failure.
- Fails for another reason (bad setup, typo, wrong fixture)? Fix the test and rerun until it fails for the right reason.
- Passes immediately? You're testing existing behavior — change the test, or drop it if the behavior is already covered.

### GREEN — Minimal Code

Write the simplest code that passes the test. Don't add features, refactor other code, or "improve" beyond the test.

### Verify GREEN — Watch It Pass

Run the new test, then the tests for the affected module.

- New test passes
- All other tests still pass
- Test fails? Fix the code, not the test. Change a test only when it asserted the wrong behavior, and say so.

### REFACTOR — Clean Up

After green only: remove duplication, improve names, extract helpers. Rerun the tests after each change. Don't add behavior.

Then take the next item from the test list.

## Existing Code Without Tests

To change code that has no tests, first pin down what it does now:

1. Write **characterization tests** that assert the current behavior (including behavior that looks wrong — note it for the user instead of fixing it silently). These should pass immediately; that's expected here.
2. For each change, write a failing test for the new behavior and continue with the normal cycle.
3. If the code can't be tested without a large restructuring, make the smallest seam that allows it (extract a function, inject a dependency) and tell the user what you changed and why.

## Good Tests

| Quality | Good | Bad |
|---------|------|-----|
| **Minimal** | One thing. "and" in name? Split it. | `void validatesEmailAndDomainAndWhitespace()` |
| **Clear** | Name describes behavior | `void test1()` |
| **Shows intent** | Demonstrates desired API | Obscures what code should do |
| **Deterministic** | Fixed clock, seeded randomness, no real network | Depends on `now()`, test order, or an external service |

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write the wished-for API. Write the assertion first. Ask the user if the expected behavior is unclear. |
| Test too complicated | Design too complicated. Simplify the interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify the design. |

## Bug Fixes

Write a failing test that reproduces the bug first, and confirm it fails the way the bug report describes. Then fix it with the normal cycle. The test proves the fix and prevents the regression.

## Testing Anti-Patterns

When adding mocks or test utilities, read [testing-anti-patterns.md](testing-anti-patterns.md):
- Testing mock behavior instead of real behavior
- Adding test-only methods to production classes
- Mocking without understanding dependencies
- Incomplete mock data

## Language and Project References

Read the one that matches the project before the first cycle:

- **Python**: [references/python.md](references/python.md) — finding the project's existing fixtures and fakes, pytest commands, fast vs integration tests, `httpx.MockTransport` fakes, FastAPI `TestClient`, rollback DB fixtures.
- **Java**: [references/java.md](references/java.md) — Maven/Gradle single-test commands, getting past compile errors to a real RED, Mockito strict stubs, `Clock`.
- **ruoyi-vue-pro**: when working in that project, also see [references/ruoyi.md](references/ruoyi.md) for test base classes, ruoyi utilities, mock strategy, and Security context setup.

## Reporting

When you finish, give the user the evidence per behavior: the test name, the RED failure line you saw, and the GREEN run. Report only commands you actually ran; if you skipped a step (with the user's agreement), say which one.
