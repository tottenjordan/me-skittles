# Examples

## Compilation

### Basic Compilation

The key flag is `-fsanitize=fuzzer`, which:
- Links the libFuzzer runtime (provides `main` function)
- Enables SanitizerCoverage instrumentation for coverage tracking
- Disables built-in functions like `memcmp`

```bash
clang++ -fsanitize=fuzzer -g -O2 harness.cc target.cc -o fuzz
```

**Flags explained:**
- `-fsanitize=fuzzer`: Enable libFuzzer
- `-g`: Add debug symbols (helpful for crash analysis)
- `-O2`: Production-level optimizations (recommended for fuzzing)
- `-DNO_MAIN`: Define macro if your code has a `main` function

### With Sanitizers

**AddressSanitizer (recommended):**
```bash
clang++ -fsanitize=fuzzer,address -g -O2 -U_FORTIFY_SOURCE harness.cc target.cc -o fuzz
```

**Multiple sanitizers:**
```bash
clang++ -fsanitize=fuzzer,address,undefined -g -O2 harness.cc target.cc -o fuzz
```

> **See Also:** For detailed sanitizer configuration, common issues, ASAN_OPTIONS flags,
> and advanced sanitizer usage, see the **address-sanitizer** and **undefined-behavior-sanitizer**
> technique skills.

### Build Flags

| Flag | Purpose |
|------|---------|
| `-fsanitize=fuzzer` | Enable libFuzzer runtime and instrumentation |
| `-fsanitize=address` | Enable AddressSanitizer (memory error detection) |
| `-fsanitize=undefined` | Enable UndefinedBehaviorSanitizer |
| `-fsanitize=fuzzer-no-link` | Instrument without linking fuzzer (for libraries) |
| `-g` | Include debug symbols |
| `-O2` | Production optimization level |
| `-U_FORTIFY_SOURCE` | Disable fortification (can interfere with ASan) |

### Building Static Libraries

For projects that produce static libraries:

1. Build the library with fuzzing instrumentation:
```bash
export CC=clang CFLAGS="-fsanitize=fuzzer-no-link -fsanitize=address"
export CXX=clang++ CXXFLAGS="$CFLAGS"
./configure --enable-shared=no
make
```

2. Link the static library with your harness:
```bash
clang++ -fsanitize=fuzzer -fsanitize=address harness.cc libmylib.a -o fuzz
```

### CMake Integration

```cmake
project(FuzzTarget)
cmake_minimum_required(VERSION 3.0)

add_executable(fuzz main.cc harness.cc)
target_compile_definitions(fuzz PRIVATE NO_MAIN=1)
target_compile_options(fuzz PRIVATE -g -O2 -fsanitize=fuzzer -fsanitize=address)
target_link_libraries(fuzz -fsanitize=fuzzer -fsanitize=address)
```

Build with:
```bash
cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ .
cmake --build .
```


## Real-World Examples

### Example 1: Fuzzing libpng

libpng is a widely-used library for reading/writing PNG images. Bugs can lead to security issues.

**1. Get source code:**
```bash
curl -L -O https://downloads.sourceforge.net/project/libpng/libpng16/1.6.37/libpng-1.6.37.tar.xz
tar xf libpng-1.6.37.tar.xz
cd libpng-1.6.37/
```

**2. Install dependencies:**
```bash
apt install zlib1g-dev
```

**3. Compile with fuzzing instrumentation:**
```bash
export CC=clang CFLAGS="-fsanitize=fuzzer-no-link -fsanitize=address"
export CXX=clang++ CXXFLAGS="$CFLAGS"
./configure --enable-shared=no
make
```

**4. Get a harness (or write your own):**
```bash
curl -O https://raw.githubusercontent.com/glennrp/libpng/f8e5fa92b0e37ab597616f554bee254157998227/contrib/oss-fuzz/libpng_read_fuzzer.cc
```

**5. Prepare corpus and dictionary:**
```bash
mkdir corpus/
curl -o corpus/input.png https://raw.githubusercontent.com/glennrp/libpng/acfd50ae0ba3198ad734e5d4dec2b05341e50924/contrib/pngsuite/iftp1n3p08.png
curl -O https://raw.githubusercontent.com/glennrp/libpng/2fff013a6935967960a5ae626fc21432807933dd/contrib/oss-fuzz/png.dict
```

**6. Link and compile fuzzer:**
```bash
clang++ -fsanitize=fuzzer -fsanitize=address libpng_read_fuzzer.cc .libs/libpng16.a -lz -o fuzz
```

**7. Run fuzzing campaign:**
```bash
./fuzz -close_fd_mask=3 -dict=./png.dict corpus/
```

### Example 2: Simple Division Bug

Harness that finds a division-by-zero bug:

```c++
#include <stdint.h>
#include <stddef.h>

double divide(uint32_t numerator, uint32_t denominator) {
    // Bug: No check if denominator is zero
    return numerator / denominator;
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if(size != 2 * sizeof(uint32_t)) {
        return 0;
    }

    uint32_t numerator = *(uint32_t*)(data);
    uint32_t denominator = *(uint32_t*)(data + sizeof(uint32_t));

    divide(numerator, denominator);

    return 0;
}
```

Compile and fuzz:
```bash
clang++ -fsanitize=fuzzer harness.cc -o fuzz
./fuzz
```

The fuzzer will quickly find inputs causing a crash.


## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Start with single-core, switch to AFL++ for multi-core | libFuzzer harnesses work with AFL++ |
| Use dictionaries for structured formats | 10-100x faster bug discovery |
| Close file descriptors with `-close_fd_mask=3` | Speed boost if SUT writes output |
| Set reasonable `-max_len` | Prevents wasted time on huge inputs |
| Run for days/weeks, not minutes | Coverage plateaus take time to break |
| Use seed corpus from test suites | Starts fuzzing from valid inputs |

### Structure-Aware Fuzzing

For highly structured inputs (e.g., complex protocols, file formats), use libprotobuf-mutator:

- Define input structure using Protocol Buffers
- libFuzzer mutates protobuf messages (structure-preserving mutations)
- Harness converts protobuf to native format

See [structure-aware fuzzing documentation](https://github.com/google/fuzzing/blob/master/docs/structure-aware-fuzzing.md) for details.

### Custom Mutators

libFuzzer allows custom mutators for specialized fuzzing:

```c++
extern "C" size_t LLVMFuzzerCustomMutator(uint8_t *Data, size_t Size,
                                          size_t MaxSize, unsigned int Seed) {
    // Custom mutation logic
    return new_size;
}

extern "C" size_t LLVMFuzzerCustomCrossOver(const uint8_t *Data1, size_t Size1,
                                            const uint8_t *Data2, size_t Size2,
                                            uint8_t *Out, size_t MaxOutSize,
                                            unsigned int Seed) {
    // Custom crossover logic
    return new_size;
}
```

### Performance Tuning

| Setting | Impact |
|---------|--------|
| `-close_fd_mask=3` | Closes stdout/stderr, speeds up fuzzing |
| `-max_len=<reasonable_size>` | Avoids wasting time on huge inputs |
| `-timeout=<seconds>` | Detects hangs, prevents stuck executions |
| Disable ASan for baseline | 2-4x speed boost (but misses memory bugs) |
| Use `-jobs` and `-workers` | Limited multi-core support |
| Run on Linux | Best platform support and performance |
