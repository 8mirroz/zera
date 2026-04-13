# Testing Anti-Patterns

1. **The Mockery**: Mocking everything including the database driver, network, and filesystem, until you are testing your own mocks.
   - *Fix*: Use functional/integration tests with real (containerized) deps when possible.

2. **The Inspector**: Testing private methods or internal state.
   - *Fix*: Test only public interfaces. Behavior, not implementation.

3. **The Slowpoke**: Tests that sleep() or wait for arbitrary timeouts.
   - *Fix*: Use deterministic polling or event-based waiting.

4. **The Interdependent**: Test B depends on Test A running first.
   - *Fix*: Each test must be atomic and clean up its own state.

5. **The Flake**: Fails 1% of the time.
   - *Fix*: Isolate it, loop it 100 times, find the race condition.
