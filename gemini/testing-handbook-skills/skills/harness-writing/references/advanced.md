# Advanced

## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| **Start with parsers** | High bug density, clear entry points, easy to harness |
| **Mock I/O operations** | Prevents hangs from blocking I/O, enables determinism |
| **Use FuzzedDataProvider** | Simplifies extraction of structured data from raw bytes |
| **Reset global state** | Ensures each iteration is independent and reproducible |
| **Free resources in harness** | Prevents memory exhaustion during long campaigns |
| **Avoid logging in harness** | Logging is slow—fuzzing needs 100s-1000s exec/sec |
| **Test harness manually first** | Run harness with known inputs before starting campaign |
| **Check coverage early** | Ensure harness reaches expected code paths |

### Structure-Aware Fuzzing with Protocol Buffers

For highly structured input formats, consider using Protocol Buffers as an intermediate format with custom mutators:

```cpp
// Define your input format in .proto file
// Use libprotobuf-mutator to generate valid mutations
// This ensures fuzzer mutates message contents, not the protobuf encoding itself
```

This approach is more setup but prevents the fuzzer from wasting time on unparseable inputs. See [structure-aware fuzzing documentation](https://github.com/google/fuzzing/blob/master/docs/structure-aware-fuzzing.md) for details.

### Handling Non-Determinism

**Problem:** Random values or timing dependencies cause non-reproducible crashes.

**Solutions:**
- Replace `rand()` with deterministic PRNG seeded from fuzzer input:
  ```cpp
  uint32_t seed = fuzzed_data.ConsumeIntegral<uint32_t>();
  srand(seed);
  ```
- Mock system calls that return time, PIDs, or random data
- Avoid reading from `/dev/random` or `/dev/urandom`

### Resetting Global State

If your SUT uses global state (singletons, static variables), reset it between iterations:

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Reset global state before each iteration
    global_reset();

    target_function(data, size);

    // Clean up resources
    global_cleanup();
    return 0;
}
```

**Rationale:** Global state can cause crashes after N iterations rather than on a specific input, making bugs non-reproducible.


## Practical Harness Rules

Follow these rules to ensure effective fuzzing harnesses:

| Rule | Rationale |
|------|-----------|
| **Handle all input sizes** | Fuzzer generates empty, tiny, huge inputs—harness must handle gracefully |
| **Never call `exit()`** | Calling `exit()` stops the fuzzer process. Use `abort()` in SUT if needed |
| **Join all threads** | Each iteration must run to completion before next iteration starts |
| **Be fast** | Aim for 100s-1000s executions/sec. Avoid logging, high complexity, excess memory |
| **Maintain determinism** | Same input must always produce same behavior for reproducibility |
| **Avoid global state** | Global state reduces reproducibility—reset between iterations if unavoidable |
| **Use narrow targets** | Don't fuzz PNG and TCP in same harness—different formats need separate targets |
| **Free resources** | Prevent memory leaks that cause resource exhaustion during long campaigns |

**Note:** These guidelines apply not just to harness code, but to the entire SUT. If the SUT violates these rules, consider patching it (see the fuzzing obstacles technique).


## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| **Global state without reset** | Non-deterministic crashes | Reset all globals at start of harness |
| **Blocking I/O or network calls** | Hangs fuzzer, wastes time | Mock I/O, use in-memory buffers |
| **Memory leaks in harness** | Resource exhaustion kills campaign | Free all allocations before returning |
| **Calling `exit()` in SUT** | Stops entire fuzzing process | Use `abort()` or return error codes |
| **Heavy logging in harness** | Reduces exec/sec by orders of magnitude | Disable logging during fuzzing |
| **Too many operations per iteration** | Slows down fuzzer | Keep iterations fast and focused |
| **Mixing unrelated input formats** | Corpus entries not useful across formats | Separate harnesses for different formats |
| **Not validating input size** | Harness crashes on edge cases | Check `size` before accessing `data` |
