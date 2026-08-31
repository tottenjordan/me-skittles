# Analysis

## Coverage Analysis

AFL++ automatically tracks coverage through edge instrumentation. Coverage information is stored in `fuzzer_stats` and `plot_data`.

### Measuring Coverage

Use `afl-plot` to visualize coverage over time:

```bash
./afl++ <host/docker> afl-plot out/default out_graph/
```

### Improving Coverage

- Use dictionaries for format-aware fuzzing
- Run longer campaigns (cycles_wo_finds indicates plateau)
- Try different mutation strategies with multi-core fuzzing
- Analyze coverage gaps and add targeted seed inputs

> **See Also:** For detailed coverage analysis techniques, identifying coverage gaps,
> and systematic coverage improvement, see the **coverage-analysis** technique skill.


## Sanitizer Integration

Sanitizers are essential for finding memory corruption bugs that don't cause immediate crashes.

### AddressSanitizer (ASan)

```bash
./afl++ <host/docker> AFL_USE_ASAN=1 afl-clang-fast++ -DNO_MAIN=1 -O2 -fsanitize=fuzzer harness.cc main.cc -o fuzz
```

**Note:** Memory limit (`-m`) is not supported with ASan due to 20TB virtual memory reservation.

### UndefinedBehaviorSanitizer (UBSan)

```bash
./afl++ <host/docker> AFL_USE_UBSAN=1 afl-clang-fast++ -DNO_MAIN=1 -O2 -fsanitize=fuzzer,undefined harness.cc main.cc -o fuzz
```

### Common Sanitizer Issues

| Issue | Solution |
|-------|----------|
| ASan slows fuzzing | Use only 1 ASan job in multi-core setup |
| Stack exhaustion | Increase stack with `ASAN_OPTIONS=stack_size=...` |
| GCC version mismatch | Ensure system GCC matches AFL++ plugin version |

> **See Also:** For comprehensive sanitizer configuration and troubleshooting,
> see the **address-sanitizer** technique skill.
