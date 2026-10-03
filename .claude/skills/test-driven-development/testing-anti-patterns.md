# Testing Anti-Patterns

**Read this when:** writing or changing tests, adding mocks, or considering a test-only method in production code.

Tests verify real behavior. Mocks isolate a unit from slow or external dependencies; they are never the thing under test. Examples are Java/JUnit + Mockito; the same rules apply in any language.

## 1. Testing Mock Behavior

```java
// ❌ Asserts that the mock is there, not that Page works
@Test
void rendersSidebar() {
    Page page = new Page(new MockSidebar());
    assertNotNull(page.getSidebarComponent());
}

// ✅ Use the real component and assert Page's behavior
@Test
void rendersSidebar() {
    Page page = new Page(new Sidebar());
    assertThat(page.getNavigation()).isNotNull();
}
```

This test passes whenever the mock is present and says nothing about real behavior. Before asserting on anything a mock returns or contains, check that the assertion is about the code under test. If the sidebar must be mocked for isolation, assert on what Page does with it, not on the mock.

## 2. Test-Only Methods in Production Classes

```java
// ❌ destroy() exists only so tests can clean up
class Session {
    public void destroy() { workspaceManager.destroyWorkspace(this.id); }
}

// ✅ Cleanup lives in test utilities
public class SessionTestUtils {
    public static void cleanupSession(Session session, WorkspaceManager manager) {
        WorkspaceInfo workspace = session.getWorkspaceInfo();
        if (workspace != null) manager.destroyWorkspace(workspace.getId());
    }
}
```

A method only tests call looks like production API, can be called in production by mistake, and often sits on a class that doesn't own the resource. Put it in test utilities. If production genuinely needs the operation, add it on the class that owns the resource's lifecycle.

## 3. Mocking Without Understanding the Dependency

```java
// ❌ The mocked method also wrote the config the duplicate check reads
@Test
void detectsDuplicateServer() {
    when(toolCatalog.discoverAndCacheTools(any())).thenReturn(null);
    serverManager.addServer(config);
    serverManager.addServer(config); // should throw, doesn't
}

// ✅ Mock only the slow external part
@Test
void detectsDuplicateServer() {
    when(mcpServerManager.startServer(any())).thenReturn(mockHandle);
    serverManager.addServer(config);
    assertThrows(DuplicateServerException.class, () -> serverManager.addServer(config));
}
```

Before mocking a method, find out what side effects it has and whether the test depends on them. If it does, mock at a lower level (the actual network, process, or clock call). If you're unsure what the test needs, run it against the real implementation first, see what happens, then mock the minimum. "Mock it to be safe" is how this bug gets written.

## 4. Incomplete Mock Data

```java
// ❌ Only the fields this test reads; downstream code NPEs on getMetadata()
ApiResponse response = ApiResponse.builder()
    .status("success")
    .data(UserData.builder().userId("123").name("Alice").build())
    .build();

// ✅ Mirrors the real response structure
ApiResponse response = ApiResponse.builder()
    .status("success")
    .data(UserData.builder().userId("123").name("Alice").build())
    .metadata(Metadata.builder().requestId("req-789").timestamp(1234567890L).build())
    .build();
```

Partial mock data encodes assumptions about which fields downstream code uses; tests pass and integration fails. Build mock data from the real schema (API docs, a recorded response, the DTO definition), including fields the code under test passes along. Prefer project factories (e.g. ruoyi's `randomPojo`) that fill every field.

## When Mocks Get Too Complex

Signs: mock setup is longer than the test logic, the test breaks whenever the mock changes, or you can't say why a mock is needed. At that point an integration test with real components is usually simpler and more trustworthy than more mocking.

## Quick Reference

| Anti-pattern | Fix |
|---|---|
| Asserting on mock elements | Test the real component, or assert on the code under test |
| Test-only methods in production | Move to test utilities |
| Mocking without understanding | Learn the side effects first; mock at the lowest external level |
| Incomplete mock data | Mirror the real schema; use factories |
| Over-complex mocks | Use an integration test |
