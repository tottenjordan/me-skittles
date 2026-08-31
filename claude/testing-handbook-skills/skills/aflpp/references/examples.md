# Examples

## Compilation

AFL++ offers multiple compilation modes with different trade-offs.

### Compilation Mode Decision Tree

Choose your compilation mode:
- **LTO mode** (`afl-clang-lto`): Best performance and instrumentation. Try this first.
- **LLVM mode** (`afl-clang-fast`): Fall back if LTO fails to compile.
- **GCC plugin** (`afl-gcc-fast`): For projects requiring GCC.

### Basic Compilation (LLVM mode)

```bash
./afl++ <host/docker> afl-clang-fast++ -DNO_MAIN=1 -O2 -fsanitize=fuzzer harness.cc main.cc -o fuzz
```

### GCC Compilation

```bash
./afl++ <host/docker> afl-g++-fast -DNO_MAIN=1 -O2 -fsanitize=fuzzer harness.cc main.cc -o fuzz
```

**Important:** GCC version must match the version used to compile the AFL++ GCC plugin.

### With Sanitizers

```bash
./afl++ <host/docker> AFL_USE_ASAN=1 afl-clang-fast++ -DNO_MAIN=1 -O2 -fsanitize=fuzzer harness.cc main.cc -o fuzz
```

> **See Also:** For detailed sanitizer configuration, common issues, and advanced flags,
> see the **address-sanitizer** and **undefined-behavior-sanitizer** technique skills.

### Build Flags

Note that `-g` is not necessary, it is added by default by the AFL++ compilers.

| Flag | Purpose |
|------|---------|
| `-DNO_MAIN=1` | Skip main function when using libFuzzer harness |
| `-O2` | Production optimization level (recommended for fuzzing) |
| `-fsanitize=fuzzer` | Enable libFuzzer compatibility mode and adds the fuzzer runtime when linking executable |
| `-fsanitize=fuzzer-no-link` | Instrument without linking fuzzer runtime (for static libraries and object files) |


## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Use LLVMFuzzerTestOneInput harnesses where possible | If a fuzzing campaign has at least 85% stability then this is the most efficient fuzzing style. If not then try standard input or file input fuzzing |
| Use dictionaries | Helps fuzzer discover format-specific keywords and magic bytes |
| Set realistic timeouts | Prevents false positives from system load |
| Limit input size | Larger inputs don't necessarily explore more space |
| Monitor stability | Low stability indicates non-deterministic behavior |

### Standard Input Fuzzing

AFL++ can fuzz programs reading from stdin without a libFuzzer harness:

```bash
./afl++ <host/docker> afl-clang-fast++ -O2 main_stdin.c -o fuzz_stdin
./afl++ <host/docker> afl-fuzz -i seeds -o out -- ./fuzz_stdin
```

This is slower than persistent mode but requires no harness code.

### File Input Fuzzing

For programs that read files, use `@@` placeholder:

```bash
./afl++ <host/docker> afl-clang-fast++ -O2 main_file.c -o fuzz_file
./afl++ <host/docker> afl-fuzz -i seeds -o out -- ./fuzz_file @@
```

For better performance, use `fmemopen` to create file descriptors from memory.

### Argument Fuzzing

Fuzz command-line arguments using `argv-fuzz-inl.h`:

```c++
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __AFL_COMPILER
#include "argv-fuzz-inl.h"
#endif

void check_buf(char *buf, size_t buf_len) {
    if(buf_len > 0 && buf[0] == 'a') {
        if(buf_len > 1 && buf[1] == 'b') {
            if(buf_len > 2 && buf[2] == 'c') {
                abort();
            }
        }
    }
}

int main(int argc, char *argv[]) {
#ifdef __AFL_COMPILER
    AFL_INIT_ARGV();
#endif

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <input_string>\n", argv[0]);
        return 1;
    }

    char *input_buf = argv[1];
    size_t len = strlen(input_buf);
    check_buf(input_buf, len);
    return 0;
}
```

Download the header:

```bash
curl -O https://raw.githubusercontent.com/AFLplusplus/AFLplusplus/stable/utils/argv_fuzzing/argv-fuzz-inl.h
```

Compile and run:

```bash
./afl++ <host/docker> afl-clang-fast++ -O2 main_arg.c -o fuzz_arg
./afl++ <host/docker> afl-fuzz -i seeds -o out -- ./fuzz_arg
```

### Performance Tuning

| Setting | Impact |
|---------|--------|
| CPU core count | Linear scaling with physical cores |
| Persistent mode | 10-20x faster than fork server |
| `-G` input size limit | Smaller = faster, but may miss bugs |
| ASan ratio | 1 ASan job per 4-8 non-ASan jobs |


## Real-World Examples

### Example: libpng

Fuzzing libpng demonstrates fuzzing a C project with static libraries:

```bash
# Get source
curl -L -O https://downloads.sourceforge.net/project/libpng/libpng16/1.6.37/libpng-1.6.37.tar.xz
tar xf libpng-1.6.37.tar.xz
cd libpng-1.6.37/

# Install dependencies
apt install zlib1g-dev

# Configure and build static library
export CC=afl-clang-fast CFLAGS=-fsanitize=fuzzer-no-link
export CXX=afl-clang-fast++ CXXFLAGS="$CFLAGS"
./configure --enable-shared=no
export AFL_LLVM_CMPLOG=1
export AFL_USE_ASAN=1
make

# Download harness
curl -O https://raw.githubusercontent.com/glennrp/libpng/f8e5fa92b0e37ab597616f554bee254157998227/contrib/oss-fuzz/libpng_read_fuzzer.cc

# Link fuzzer
export AFL_USE_ASAN=1
$CXX -fsanitize=fuzzer libpng_read_fuzzer.cc .libs/libpng16.a -lz -o fuzz

# Prepare seeds and dictionary
mkdir seeds/
curl -o seeds/input.png https://raw.githubusercontent.com/glennrp/libpng/acfd50ae0ba3198ad734e5d4dec2b05341e50924/contrib/pngsuite/iftp1n3p08.png
curl -O https://raw.githubusercontent.com/glennrp/libpng/2fff013a6935967960a5ae626fc21432807933dd/contrib/oss-fuzz/png.dict

# Start fuzzing
./afl++ <host/docker> afl-fuzz -i seeds -o out -- ./fuzz
```

### Example: CMake-based Project

```cmake
project(BuggyProgram)
cmake_minimum_required(VERSION 3.0)

add_executable(buggy_program main.cc)

add_executable(fuzz main.cc harness.cc)
target_compile_definitions(fuzz PRIVATE NO_MAIN=1)
target_compile_options(fuzz PRIVATE -O2 -fsanitize=fuzzer-no-link)
target_link_libraries(fuzz -fsanitize=fuzzer)
```

Build and fuzz:

```bash
# Build non-instrumented binary
./afl++ <host/docker> cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ .
./afl++ <host/docker> cmake --build . --target buggy_program

# Build fuzzer
./afl++ <host/docker> cmake -DCMAKE_C_COMPILER=afl-clang-fast -DCMAKE_CXX_COMPILER=afl-clang-fast++ .
./afl++ <host/docker> cmake --build . --target fuzz

# Fuzz
./afl++ <host/docker> afl-fuzz -i seeds -o out -- ./fuzz
```
