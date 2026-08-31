# Examples

## Compilation

### Verbose Mode

Manually specify all instrumentation flags:

```bash
clang++-15 -DNO_MAIN -g -O2 \
  -fsanitize-coverage=trace-pc-guard \
  -fsanitize=address \
  -Wl,--whole-archive target/release/libmy_fuzzer.a -Wl,--no-whole-archive \
  main.cc harness.cc -o fuzz
```

### Compiler Wrapper (Recommended)

Create a LibAFL compiler wrapper to handle instrumentation automatically.

**Create `src/bin/libafl_cc.rs`:**
```rust
use libafl_cc::{ClangWrapper, CompilerWrapper, Configuration, ToolWrapper};

pub fn main() {
    let args: Vec<String> = env::args().collect();
    let mut cc = ClangWrapper::new();
    cc.cpp(is_cpp)
      .parse_args(&args)
      .link_staticlib(&dir, "my_fuzzer")
      .add_args(&Configuration::GenerateCoverageMap.to_flags().unwrap())
      .add_args(&Configuration::AddressSanitizer.to_flags().unwrap())
      .run()
      .unwrap();
}
```

**Compile and use:**
```bash
cargo build --release
target/release/libafl_cxx -DNO_MAIN -g -O2 main.cc harness.cc -o fuzz
```

> **See Also:** For detailed sanitizer configuration, common issues, and advanced flags,
> see the **address-sanitizer** and **undefined-behavior-sanitizer** technique skills.


## Running Campaigns

### Basic Run

```bash
./fuzz --cores 0 --input corpus/
```

### Multi-Core Fuzzing

```bash
./fuzz --cores 0,8-15 --input corpus/
```

This runs 9 clients: one on core 0, and 8 on cores 8-15.

### With Options

```bash
./fuzz --cores 0-7 --input corpus/ --output crashes/ --timeout 1000
```

### Text User Interface (TUI)

Enable graphical statistics view:

```bash
./fuzz -tui=1 corpus/
```

### Interpreting Output

| Output | Meaning |
|--------|---------|
| `corpus: N` | Number of interesting test cases found |
| `objectives: N` | Number of crashes/timeouts found |
| `executions: N` | Total number of target invocations |
| `exec/sec: N` | Current execution throughput |
| `edges: X%` | Code coverage percentage |
| `clients: N` | Number of parallel fuzzing processes |

The fuzzer emits two main event types:
- **UserStats** - Regular heartbeat with current statistics
- **Testcase** - New interesting input discovered


## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Use `-fork=1 -ignore_crashes=1` | Continue fuzzing after first crash |
| Use `InMemoryOnDiskCorpus` | Persist corpus across restarts |
| Enable TUI with `-tui=1` | Better visualization of progress |
| Use specific LLVM version | Avoid compatibility issues |
| Set `RUSTFLAGS` correctly | Prevent linking errors |

### Crash Deduplication

Avoid storing duplicate crashes from the same bug:

**Add backtrace observer:**
```rust
let backtrace_observer = BacktraceObserver::owned(
    "BacktraceObserver",
    libafl::observers::HarnessType::InProcess
);
```

**Update executor:**
```rust
let mut executor = InProcessExecutor::with_timeout(
    &mut harness,
    tuple_list!(edges_observer, time_observer, backtrace_observer),
    &mut fuzzer,
    &mut state,
    &mut restarting_mgr,
    timeout,
)?;
```

**Update objective with hash feedback:**
```rust
let mut objective = feedback_and!(
    feedback_or_fast!(CrashFeedback::new(), TimeoutFeedback::new()),
    NewHashFeedback::new(&backtrace_observer)
);
```

This ensures only crashes with unique backtraces are saved.

### Dictionary Fuzzing

Use dictionaries to guide fuzzing toward specific tokens:

**Add tokens from file:**
```rust
let mut tokens = Tokens::new();
if let Some(tokenfile) = &tokenfile {
    tokens.add_from_file(tokenfile)?;
}
state.add_metadata(tokens);
```

**Update mutator:**
```rust
let mutator = StdScheduledMutator::new(
    havoc_mutations().merge(tokens_mutations())
);
```

**Hard-coded tokens example (PNG):**
```rust
state.add_metadata(Tokens::from([
    vec![137, 80, 78, 71, 13, 10, 26, 10], // PNG header
    "IHDR".as_bytes().to_vec(),
    "IDAT".as_bytes().to_vec(),
    "PLTE".as_bytes().to_vec(),
    "IEND".as_bytes().to_vec(),
]));
```

> **See Also:** For detailed dictionary creation strategies and format-specific dictionaries,
> see the **fuzzing-dictionaries** technique skill.

### Auto Tokens

Automatically extract magic values and checksums from the program:

**Enable in compiler wrapper:**
```rust
cc.add_pass(LLVMPasses::AutoTokens)
```

**Load auto tokens in fuzzer:**
```rust
tokens += libafl_targets::autotokens()?;
```

**Verify tokens section:**
```bash
echo "p (uint8_t *)__token_start" | gdb fuzz
```

### Performance Tuning

| Setting | Impact |
|---------|--------|
| Multi-core fuzzing | Linear speedup with cores |
| `InMemoryCorpus` | Faster but non-persistent |
| `InMemoryOnDiskCorpus` | Balanced speed and persistence |
| Sanitizers | 2-5x slowdown, essential for bugs |
| Optimization level `-O2` | Balance between speed and coverage |

### Debugging Fuzzer

Run fuzzer in single-process mode for easier debugging:

```rust
// Replace launcher with direct call
run_client(None, SimpleEventManager::new(monitor), 0).unwrap();

// Comment out:
// Launcher::builder()
//     .run_client(&mut run_client)
//     ...
//     .launch()
```

Then debug with GDB:
```bash
gdb --args ./fuzz --cores 0 --input corpus/
```


## Real-World Examples

### Example: libpng

Fuzzing libpng using LibAFL:

**1. Get source code:**
```bash
curl -L -O https://downloads.sourceforge.net/project/libpng/libpng16/1.6.37/libpng-1.6.37.tar.xz
tar xf libpng-1.6.37.tar.xz
cd libpng-1.6.37/
apt install zlib1g-dev
```

**2. Set compiler wrapper:**
```bash
export FUZZER_CARGO_DIR="/path/to/libafl/project"
export CC=$FUZZER_CARGO_DIR/target/release/libafl_cc
export CXX=$FUZZER_CARGO_DIR/target/release/libafl_cxx
```

**3. Build static library:**
```bash
./configure --enable-shared=no
make
```

**4. Get harness:**
```bash
curl -O https://raw.githubusercontent.com/glennrp/libpng/f8e5fa92b0e37ab597616f554bee254157998227/contrib/oss-fuzz/libpng_read_fuzzer.cc
```

**5. Link fuzzer:**
```bash
$CXX libpng_read_fuzzer.cc .libs/libpng16.a -lz -o fuzz
```

**6. Prepare seeds:**
```bash
mkdir seeds/
curl -o seeds/input.png https://raw.githubusercontent.com/glennrp/libpng/acfd50ae0ba3198ad734e5d4dec2b05341e50924/contrib/pngsuite/iftp1n3p08.png
```

**7. Get dictionary (optional):**
```bash
curl -O https://raw.githubusercontent.com/glennrp/libpng/2fff013a6935967960a5ae626fc21432807933dd/contrib/oss-fuzz/png.dict
```

**8. Start fuzzing:**
```bash
./fuzz --input seeds/ --cores 0 -x png.dict
```

### Example: CMake Project

Integrate LibAFL with CMake build system:

**CMakeLists.txt:**
```cmake
project(BuggyProgram)
cmake_minimum_required(VERSION 3.0)

add_executable(buggy_program main.cc)

add_executable(fuzz main.cc harness.cc)
target_compile_definitions(fuzz PRIVATE NO_MAIN=1)
target_compile_options(fuzz PRIVATE -g -O2)
```

**Build non-instrumented binary:**
```bash
cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ .
cmake --build . --target buggy_program
```

**Build fuzzer:**
```bash
export FUZZER_CARGO_DIR="/path/to/libafl/project"
cmake -DCMAKE_C_COMPILER=$FUZZER_CARGO_DIR/target/release/libafl_cc \
      -DCMAKE_CXX_COMPILER=$FUZZER_CARGO_DIR/target/release/libafl_cxx .
cmake --build . --target fuzz
```

**Run fuzzing:**
```bash
./fuzz --input seeds/ --cores 0
```
