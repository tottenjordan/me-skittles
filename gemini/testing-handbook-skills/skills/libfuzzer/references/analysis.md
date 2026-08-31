# Analysis

## Coverage Analysis

While libFuzzer shows basic coverage stats (`cov: N`), detailed coverage analysis requires additional tools.

### Source-Based Coverage

**1. Recompile with coverage instrumentation:**
```bash
clang++ -fsanitize=fuzzer -fprofile-instr-generate -fcoverage-mapping harness.cc target.cc -o fuzz
```

**2. Run fuzzer to collect coverage:**
```bash
LLVM_PROFILE_FILE="coverage-%p.profraw" ./fuzz -runs=10000 corpus/
```

**3. Merge coverage data:**
```bash
llvm-profdata merge -sparse coverage-*.profraw -o coverage.profdata
```

**4. Generate coverage report:**
```bash
llvm-cov show ./fuzz -instr-profile=coverage.profdata
```

**5. Generate HTML report:**
```bash
llvm-cov show ./fuzz -instr-profile=coverage.profdata -format=html > coverage.html
```

### Improving Coverage

**Tips:**
- Provide better seed inputs in corpus
- Use dictionaries for format-aware fuzzing
- Check if harness properly exercises target
- Consider structure-aware fuzzing for complex formats
- Run longer campaigns (days/weeks)

> **See Also:** For detailed coverage analysis techniques, identifying coverage gaps,
> systematic coverage improvement, and comparing coverage across fuzzers, see the
> **coverage-analysis** technique skill.


## Sanitizer Integration

### AddressSanitizer (ASan)

ASan detects memory errors like buffer overflows and use-after-free bugs. **Highly recommended for fuzzing.**

**Enable ASan:**
```bash
clang++ -fsanitize=fuzzer,address -g -O2 -U_FORTIFY_SOURCE harness.cc target.cc -o fuzz
```

**Example ASan output:**
```
==1276163==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6020000c4ab1
WRITE of size 1 at 0x6020000c4ab1 thread T0
    #0 0x55555568631a in check_buf(char*, unsigned long) main.cc:13:25
    #1 0x5555556860bf in LLVMFuzzerTestOneInput harness.cc:7:3
```

**Configure ASan with environment variables:**
```bash
ASAN_OPTIONS=verbosity=1:abort_on_error=1 ./fuzz corpus/
```

**Important flags:**
- `verbosity=1`: Show ASan is active
- `detect_leaks=0`: Disable leak detection (leaks reported at end)
- `abort_on_error=1`: Call `abort()` instead of `_exit()` on errors

**Drawbacks:**
- 2-4x slowdown
- Requires ~20TB virtual memory (disable memory limits: `-rss_limit_mb=0`)
- Best supported on Linux

> **See Also:** For comprehensive ASan configuration, common pitfalls, symbolization,
> and combining with other sanitizers, see the **address-sanitizer** technique skill.

### UndefinedBehaviorSanitizer (UBSan)

UBSan detects undefined behavior like integer overflow, null pointer dereference, etc.

**Enable UBSan:**
```bash
clang++ -fsanitize=fuzzer,undefined -g -O2 harness.cc target.cc -o fuzz
```

**Combine with ASan:**
```bash
clang++ -fsanitize=fuzzer,address,undefined -g -O2 harness.cc target.cc -o fuzz
```

### MemorySanitizer (MSan)

MSan detects uninitialized memory reads. More complex to use (requires rebuilding all dependencies).

```bash
clang++ -fsanitize=fuzzer,memory -g -O2 harness.cc target.cc -o fuzz
```

### Common Sanitizer Issues

| Issue | Solution |
|-------|----------|
| ASan slows fuzzing too much | Use `-fsanitize-recover=address` for non-fatal errors |
| Out of memory | Set `ASAN_OPTIONS=rss_limit_mb=0` or `-rss_limit_mb=0` |
| Stack exhaustion | Increase stack size: `ASAN_OPTIONS=stack_size=8388608` |
| False positives with `_FORTIFY_SOURCE` | Use `-U_FORTIFY_SOURCE` flag |
| MSan reports in dependencies | Rebuild all dependencies with `-fsanitize=memory` |
