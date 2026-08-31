# Patterns

## Common Patterns

### Pattern: Identifying Magic Values

**Problem**: Fuzzer cannot discover paths guarded by magic value checks.

**Coverage reveals:**
```cpp
// Coverage shows this block is never executed
if (buf == 0x7F454C46) {  // ELF magic number
    // start parsing buf
}
```

**Solution**: Add magic values to dictionary file:
```
# magic.dict
"\x7F\x45\x4C\x46"
```

### Pattern: Handling Crashing Inputs

**Problem**: Coverage generation fails when corpus contains crashing inputs.

**Before:**
```bash
./fuzz_exec corpus/  # Crashes on bad input, no coverage generated
```

**After:**
```cpp
// Fork before executing to isolate crashes
int main(int argc, char **argv) {
    // ... directory opening code ...

    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_type == DT_REG) {
            pid_t pid = fork();
            if (pid == 0) {
                // Child process - crash won't affect parent
                char filepath[1024];
                snprintf(filepath, sizeof(filepath), "%s/%s", argv[1], entry->d_name);
                load_file_and_test(filepath);
                exit(0);
            } else {
                // Parent waits for child
                waitpid(pid, NULL, 0);
            }
        }
    }
}
```

### Pattern: CMake Integration

**Use Case**: Adding coverage builds to CMake projects.

```cmake
project(FuzzingProject)
cmake_minimum_required(VERSION 3.0)

# Main binary
add_executable(program main.cc)

# Fuzzing binary
add_executable(fuzz main.cc harness.cc)
target_compile_definitions(fuzz PRIVATE NO_MAIN=1)
target_compile_options(fuzz PRIVATE -g -O2 -fsanitize=fuzzer)
target_link_libraries(fuzz -fsanitize=fuzzer)

# Coverage execution binary
add_executable(fuzz_exec main.cc harness.cc execute-rt.cc)
target_compile_definitions(fuzz_exec PRIVATE NO_MAIN)
target_compile_options(fuzz_exec PRIVATE -O2 -fprofile-instr-generate -fcoverage-mapping)
target_link_libraries(fuzz_exec -fprofile-instr-generate)
```

Build:
```bash
cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ .
cmake --build . --target fuzz_exec
```


## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Use LLVM 18+ with `-show-directory-coverage` | Organizes large reports by directory structure instead of flat file list |
| Export to lcov format for better HTML | `llvm-cov export -format=lcov` + `genhtml` provides cleaner per-file reports |
| Compare coverage across campaigns | Store `.profdata` files with timestamps to track progress over time |
| Filter harness code from reports | Use `-ignore-filename-regex` to focus on SUT coverage only |
| Automate coverage in CI/CD | Generate coverage reports automatically after scheduled fuzzing runs |
| Use gcovr 5.1+ for Clang 14+ | Older gcovr versions have compatibility issues with recent LLVM |

### Incremental Coverage Updates

GCC's gcov instrumentation incrementally updates `.gcda` files across multiple runs. This is useful for tracking coverage as you add test cases:

```bash
# First run
./fuzz_exec_gcov corpus_batch_1/
gcovr --html coverage_v1.html

# Second run (adds to existing coverage)
./fuzz_exec_gcov corpus_batch_2/
gcovr --html coverage_v2.html

# Start fresh
gcovr --delete  # Remove .gcda files
./fuzz_exec_gcov corpus/
```

### Handling Large Codebases

For projects with hundreds of source files:

1. **Filter by prefix**: Only generate reports for relevant directories
   ```bash
   llvm-cov show ./fuzz_exec -instr-profile=fuzz.profdata /path/to/src/
   ```

2. **Use directory coverage**: Group by directory to reduce clutter (LLVM 18+)
   ```bash
   llvm-cov show -show-directory-coverage -format=html -output-dir html/
   ```

3. **Generate JSON for programmatic analysis**:
   ```bash
   llvm-cov export -format=lcov > coverage.json
   ```

### Differential Coverage

Compare coverage between two fuzzing campaigns:

```bash
# Campaign 1
LLVM_PROFILE_FILE=campaign1.profraw ./fuzz_exec corpus1/
llvm-profdata merge -sparse campaign1.profraw -o campaign1.profdata

# Campaign 2
LLVM_PROFILE_FILE=campaign2.profraw ./fuzz_exec corpus2/
llvm-profdata merge -sparse campaign2.profraw -o campaign2.profdata

# Compare
llvm-cov show ./fuzz_exec \
  -instr-profile=campaign2.profdata \
  -instr-profile=campaign1.profdata \
  -show-line-counts-or-regions
```


## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| Using fuzzer-reported coverage for comparisons | Different fuzzers calculate coverage differently, making cross-tool comparison meaningless | Use dedicated coverage tools (llvm-cov, gcovr) for reproducible measurements |
| Generating coverage with optimizations | `-O3` optimizations can eliminate code, making coverage misleading | Use `-O2` or `-O0` for coverage builds |
| Not filtering harness code | Harness coverage inflates numbers and obscures SUT coverage | Use `-ignore-filename-regex` or `--exclude` to filter harness files |
| Mixing LLVM and GCC instrumentation | Incompatible formats cause parsing failures | Stick to one toolchain for coverage builds |
| Ignoring crashing inputs | Crashes prevent coverage generation, hiding real coverage data | Fix crashes first, or use process forking to isolate them |
| Not tracking coverage over time | One-time coverage checks miss regressions and improvements | Store coverage data with timestamps and track trends |
