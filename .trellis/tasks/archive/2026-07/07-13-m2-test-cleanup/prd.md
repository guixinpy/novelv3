# Clean up obsolete tests from M2 adapter layer deletion

## Goal

After deleting 30 adapter/descriptor files and stubbing tool_executor/tool_contracts/tool_registry, 582 tests fail. Most test the old architecture that was deleted. Remove or fix them so the test suite is green again.

## Strategy

1. Identify tests that directly test deleted modules → delete
2. Identify tests that fail due to stubs but test kept functionality → fix stubs or tests
3. Run full suite, iterate
4. Goal: `pytest tests/ -q` all passing

## Acceptance Criteria

- [ ] `pytest tests/ -q` passes with no failures
- [ ] 75 agent tests still pass
