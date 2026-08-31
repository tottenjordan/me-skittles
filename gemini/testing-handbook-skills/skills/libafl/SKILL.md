---
name: libafl
type: fuzzer
description: >
  LibAFL is a modular fuzzing library for building custom fuzzers. Use for
  advanced fuzzing needs, custom mutators, or non-standard fuzzing targets.
---

# LibAFL

LibAFL is a modular fuzzing library that implements features from AFL-based fuzzers like AFL++. Unlike traditional fuzzers, LibAFL provides all functionality in a modular and customizable way as a Rust library. It can be used as a drop-in replacement for libFuzzer or as a library to build custom fuzzers from scratch.

## When to Use

| Fuzzer | Best For | Complexity |
|--------|----------|------------|
| libFuzzer | Quick setup, single-threaded | Low |
| AFL++ | Multi-core, general purpose | Medium |
| LibAFL | Custom fuzzers, advanced features, research | High |

**Choose LibAFL when:**
- You need custom mutation strategies or feedback mechanisms
- Standard fuzzers don't support your target architecture
- You want to implement novel fuzzing techniques
- You need fine-grained control over fuzzing components
- You're conducting fuzzing research

## Quick Start

LibAFL can be used as a drop-in replacement for libFuzzer with minimal setup:

```c++
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Call your code with fuzzer-provided data
    my_function(data, size);
    return 0;
}
```

Build LibAFL's libFuzzer compatibility layer:
```bash
git clone https://github.com/AFLplusplus/LibAFL
cd LibAFL/libafl_libfuzzer_runtime
./build.sh
```

Compile and run:
```bash
clang++ -DNO_MAIN -g -O2 -fsanitize=fuzzer-no-link libFuzzer.a harness.cc main.cc -o fuzz
./fuzz corpus/
```

## Installation

### Prerequisites

- Clang/LLVM 15-18
- Rust (via rustup)
- Additional system dependencies

### Linux/macOS

Install Clang:
```bash
apt install clang
```

Or install a specific version via apt.llvm.org:
```bash
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 15
```

Configure environment for Rust:
```bash
export RUSTFLAGS="-C linker=/usr/bin/clang-15"
export CC="clang-15"
export CXX="clang++-15"
```

Install Rust:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Install additional dependencies:
```bash
apt install libssl-dev pkg-config
```

For libFuzzer compatibility mode, install nightly Rust:
```bash
rustup toolchain install nightly --component llvm-tools
```

### Verification

Build LibAFL to verify installation:
```bash
cd LibAFL/libafl_libfuzzer_runtime
./build.sh
# Should produce libFuzzer.a
```

## Writing a Harness

LibAFL harnesses follow the same pattern as libFuzzer when using drop-in replacement mode:

```c++
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Your fuzzing target code here
    return 0;
}
```

When building custom fuzzers with LibAFL as a Rust library, harness logic is integrated directly into the fuzzer. See the "Writing a Custom Fuzzer" section below for the full pattern.

> **See Also:** For detailed harness writing techniques, see the **harness-writing** technique skill.

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| No coverage increases | Instrumentation failed | Verify compiler wrapper used, check for `-fsanitize-coverage` |
| Fuzzer won't start | Empty corpus with no interesting inputs | Provide seed inputs that trigger code paths |
| Linker errors with `libafl_main` | Runtime not linked | Use `-Wl,--whole-archive` or `-u libafl_main` |
| LLVM version mismatch | LibAFL requires LLVM 15-18 | Install compatible LLVM version, set environment variables |
| Rust compilation fails | Outdated Rust or Cargo | Update Rust with `rustup update` |
| Slow fuzzing | Sanitizers enabled | Expected 2-5x slowdown, necessary for finding bugs |
| Environment variable interference | `CC`, `CXX`, `RUSTFLAGS` set | Unset after building LibAFL project |
| Cannot attach debugger | Multi-process fuzzing | Run in single-process mode (see Debugging section) |

## Reference material

**[references/custom-fuzzers.md](references/custom-fuzzers.md)** — usage modes and building a custom fuzzer

**[references/examples.md](references/examples.md)** — compilation, running campaigns, advanced usage, and worked examples

## Related Skills

### Technique Skills

| Skill | Use Case |
|-------|----------|
| **fuzz-harness-writing** | Detailed guidance on writing effective harnesses |
| **address-sanitizer** | Memory error detection during fuzzing |
| **undefined-behavior-sanitizer** | Undefined behavior detection |
| **coverage-analysis** | Measuring and improving code coverage |
| **fuzzing-corpus** | Building and managing seed corpora |
| **fuzzing-dictionaries** | Creating dictionaries for format-aware fuzzing |

### Related Fuzzers

| Skill | When to Consider |
|-------|------------------|
| **libfuzzer** | Simpler setup, don't need LibAFL's advanced features |
| **aflpp** | Multi-core fuzzing without custom fuzzer development |
| **cargo-fuzz** | Fuzzing Rust projects with less setup |

## Resources

### Official Documentation

- [LibAFL Book](https://aflplus.plus/libafl-book/) - Official handbook with comprehensive documentation
- [LibAFL GitHub](https://github.com/AFLplusplus/LibAFL) - Source code and examples
- [LibAFL API Documentation](https://docs.rs/libafl/latest/libafl/) - Rust API reference

### Examples and Tutorials

- [LibAFL Examples](https://github.com/AFLplusplus/LibAFL/tree/main/fuzzers) - Collection of example fuzzers
- [cargo-fuzz with LibAFL](https://github.com/AFLplusplus/LibAFL/tree/main/fuzzers/fuzz_anything/cargo_fuzz) - Using LibAFL as cargo-fuzz backend
- [Testing Handbook LibAFL Examples](https://github.com/trailofbits/testing-handbook/tree/main/materials/fuzzing/libafl) - Complete working examples from this handbook
