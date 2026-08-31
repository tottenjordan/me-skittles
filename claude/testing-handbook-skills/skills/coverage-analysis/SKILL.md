---
name: coverage-analysis
type: technique
description: >
  Coverage analysis measures code exercised during fuzzing.
  Use when assessing harness effectiveness or identifying fuzzing blockers.
---

# Coverage Analysis

Coverage analysis is essential for understanding which parts of your code are exercised during fuzzing. It helps identify fuzzing blockers like magic value checks and tracks the effectiveness of harness improvements over time.

## Overview

Code coverage during fuzzing serves two critical purposes:

1. **Assessing harness effectiveness**: Understand which parts of your application are actually executed by your fuzzing harnesses
2. **Tracking fuzzing progress**: Monitor how coverage changes when updating harnesses, fuzzers, or the system under test (SUT)

Coverage is a proxy for fuzzer capability and performance. While coverage [is not ideal for measuring fuzzer performance](https://arxiv.org/abs/1808.09700) in absolute terms, it reliably indicates whether your harness works effectively in a given setup.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Coverage instrumentation** | Compiler flags that track which code paths are executed |
| **Corpus coverage** | Coverage achieved by running all test cases in a fuzzing corpus |
| **Magic value checks** | Hard-to-discover conditional checks that block fuzzer progress |
| **Coverage-guided fuzzing** | Fuzzing strategy that prioritizes inputs that discover new code paths |
| **Coverage report** | Visual or textual representation of executed vs. unexecuted code |

## When to Apply

**Apply this technique when:**
- Starting a new fuzzing campaign to establish a baseline
- Fuzzer appears to plateau without finding new paths
- After harness modifications to verify improvements
- When migrating between different fuzzers
- Identifying areas requiring dictionary entries or seed inputs
- Debugging why certain code paths aren't reached

**Skip this technique when:**
- Fuzzing campaign is actively finding crashes
- Coverage infrastructure isn't set up yet
- Working with extremely large codebases where full coverage reports are impractical
- Fuzzer's internal coverage metrics are sufficient for your needs

## Quick Reference

| Task | Command/Pattern |
|------|-----------------|
| LLVM coverage instrumentation (C/C++) | `-fprofile-instr-generate -fcoverage-mapping` |
| GCC coverage instrumentation | `-ftest-coverage -fprofile-arcs` |
| cargo-fuzz coverage (Rust) | `cargo +nightly fuzz coverage <target>` |
| Generate LLVM profile data | `llvm-profdata merge -sparse file.profraw -o file.profdata` |
| LLVM coverage report | `llvm-cov report ./binary -instr-profile=file.profdata` |
| LLVM HTML report | `llvm-cov show ./binary -instr-profile=file.profdata -format=html -output-dir html/` |
| gcovr HTML report | `gcovr --html-details -o coverage.html` |

## Tool-Specific Guidance

### libFuzzer

libFuzzer uses LLVM's SanitizerCoverage by default for guiding fuzzing, but you need separate instrumentation for generating reports.

**Build for coverage:**
```bash
clang++ -fprofile-instr-generate -fcoverage-mapping \
  -O2 -DNO_MAIN \
  main.cc harness.cc execute-rt.cc -o fuzz_exec
```

**Execute corpus and generate report:**
```bash
LLVM_PROFILE_FILE=fuzz.profraw ./fuzz_exec corpus/
llvm-profdata merge -sparse fuzz.profraw -o fuzz.profdata
llvm-cov show ./fuzz_exec -instr-profile=fuzz.profdata -format=html -output-dir html/
```

**Integration tips:**
- Don't use `-fsanitize=fuzzer` for coverage builds (it conflicts with profile instrumentation)
- Reuse the same harness function (`LLVMFuzzerTestOneInput`) with a different main function
- Use the `-ignore-filename-regex` flag to exclude harness code from coverage reports
- Consider using llvm-cov's `-show-instantiation` flag for template-heavy C++ code

### AFL++

AFL++ provides its own coverage feedback mechanism, but for detailed reports use standard LLVM/GCC tools.

**Build for coverage with LLVM:**
```bash
clang++ -fprofile-instr-generate -fcoverage-mapping \
  -O2 main.cc harness.cc execute-rt.cc -o fuzz_exec
```

**Build for coverage with GCC:**
```bash
AFL_USE_ASAN=0 afl-gcc -ftest-coverage -fprofile-arcs \
  main.cc harness.cc execute-rt.cc -o fuzz_exec_gcov
```

**Execute and generate report:**
```bash
# LLVM approach
LLVM_PROFILE_FILE=fuzz.profraw ./fuzz_exec afl_output/queue/
llvm-profdata merge -sparse fuzz.profraw -o fuzz.profdata
llvm-cov report ./fuzz_exec -instr-profile=fuzz.profdata

# GCC approach
./fuzz_exec_gcov afl_output/queue/
gcovr --html-details -o coverage.html
```

**Integration tips:**
- Don't use AFL++'s instrumentation (`afl-clang-fast`) for coverage builds
- Use standard compilers with coverage flags instead
- AFL++'s `queue/` directory contains your corpus
- AFL++'s built-in coverage statistics are useful for real-time monitoring but not for detailed analysis

### cargo-fuzz (Rust)

cargo-fuzz provides built-in coverage generation using LLVM tools.

**Install prerequisites:**
```bash
rustup toolchain install nightly --component llvm-tools-preview
cargo install cargo-binutils rustfilt
```

**Generate coverage data:**
```bash
cargo +nightly fuzz coverage fuzz_target_1
```

**Create HTML report script:**
```bash
cat <<'EOF' > ./generate_html
#!/bin/sh
FUZZ_TARGET="$1"
shift
SRC_FILTER="$@"
TARGET=$(rustc -vV | sed -n 's|host: ||p')
cargo +nightly cov -- show -Xdemangler=rustfilt \
  "target/$TARGET/coverage/$TARGET/release/$FUZZ_TARGET" \
  -instr-profile="fuzz/coverage/$FUZZ_TARGET/coverage.profdata" \
  -show-line-counts-or-regions -show-instantiations \
  -format=html -o fuzz_html/ $SRC_FILTER
EOF
chmod +x ./generate_html
```

**Generate report:**
```bash
./generate_html fuzz_target_1 src/lib.rs
```

**Integration tips:**
- Always use the nightly toolchain for coverage
- The `-Xdemangler=rustfilt` flag makes function names readable
- Filter by source files (e.g., `src/lib.rs`) to focus on crate code
- Use `-show-line-counts-or-regions` and `-show-instantiations` for better Rust-specific output
- Corpus is located in `fuzz/corpus/<target>/`

### honggfuzz

honggfuzz works with standard LLVM/GCC coverage instrumentation.

**Build for coverage:**
```bash
# Use standard compiler, not honggfuzz compiler
clang -fprofile-instr-generate -fcoverage-mapping \
  -O2 harness.c execute-rt.c -o fuzz_exec
```

**Execute corpus:**
```bash
LLVM_PROFILE_FILE=fuzz.profraw ./fuzz_exec honggfuzz_workspace/
```

**Integration tips:**
- Don't use `hfuzz-clang` for coverage builds
- honggfuzz corpus is typically in a workspace directory
- Use the same LLVM workflow as libFuzzer

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `error: no profile data available` | Profile wasn't generated or wrong path | Verify `LLVM_PROFILE_FILE` was set and `.profraw` file exists |
| `Failed to load coverage` | Mismatch between binary and profile data | Rebuild binary with same flags used during execution |
| Coverage reports show 0% | Wrong binary used for report generation | Use the instrumented binary, not the fuzzing binary |
| `no_working_dir_found` error (gcovr) | `.gcda` files in unexpected location | Add `--gcov-ignore-errors=no_working_dir_found` flag |
| Crashes prevent coverage generation | Corpus contains crashing inputs | Filter crashes or use forking approach to isolate failures |
| Coverage decreases after harness change | Harness now skips certain code paths | Review harness logic; may need to support more input formats |
| HTML report is flat file list | Using older LLVM version | Upgrade to LLVM 18+ and use `-show-directory-coverage` |
| `incompatible instrumentation` | Mixing LLVM and GCC coverage | Rebuild everything with same toolchain |

## Reference material

**[references/workflow.md](references/workflow.md)** — the ideal workflow and step-by-step process

**[references/patterns.md](references/patterns.md)** — common patterns, advanced usage, and anti-patterns

## Related Skills

### Tools That Use This Technique

| Skill | How It Applies |
|-------|----------------|
| **libfuzzer** | Uses SanitizerCoverage for feedback; coverage analysis evaluates harness effectiveness |
| **aflpp** | Uses edge coverage for feedback; detailed analysis requires separate instrumentation |
| **cargo-fuzz** | Built-in `cargo fuzz coverage` command for Rust projects |
| **honggfuzz** | Uses edge coverage; analyze with standard LLVM/GCC tools |

### Related Techniques

| Skill | Relationship |
|-------|--------------|
| **fuzz-harness-writing** | Coverage reveals which code paths harness reaches; guides harness improvements |
| **fuzzing-dictionaries** | Coverage identifies magic value checks that need dictionary entries |
| **corpus-management** | Coverage analysis helps curate corpora by identifying redundant test cases |
| **sanitizers** | Coverage helps verify sanitizer-instrumented code is actually executed |

## Resources

### Key External Resources

**[LLVM Source-Based Code Coverage](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html)**
Comprehensive guide to LLVM's profile instrumentation, including advanced features like branch coverage, region coverage, and integration with existing build systems. Covers compiler flags, runtime behavior, and profile data formats.

**[llvm-cov Command Guide](https://llvm.org/docs/CommandGuide/llvm-cov.html)**
Detailed CLI reference for llvm-cov commands including `show`, `report`, and `export`. Documents all filtering options, output formats, and integration with llvm-profdata.

**[gcovr Documentation](https://gcovr.com/)**
Complete guide to gcovr tool for generating coverage reports from gcov data. Covers HTML themes, filtering options, multi-directory projects, and CI/CD integration patterns.

**[SanitizerCoverage Documentation](https://clang.llvm.org/docs/SanitizerCoverage.html)**
Low-level documentation for LLVM's SanitizerCoverage instrumentation. Explains inline 8-bit counters, PC tables, and how fuzzers use coverage feedback for guidance.

**[On the Evaluation of Fuzzer Performance](https://arxiv.org/abs/1808.09700)**
Research paper examining limitations of coverage as a fuzzing performance metric. Argues for more nuanced evaluation methods beyond simple code coverage percentages.

### Video Resources

Not applicable - coverage analysis is primarily a tooling and workflow topic best learned through documentation and hands-on practice.
