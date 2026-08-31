# Patterns

## Step-by-Step

### Step 1: Identify Entry Points

Find functions in your codebase that:
- Accept external input (parsers, validators, protocol handlers)
- Parse complex data formats (JSON, XML, binary protocols)
- Perform security-critical operations (authentication, cryptography)
- Have high cyclomatic complexity or many branches

Good targets are typically:
- Protocol parsers
- File format parsers
- Serialization/deserialization functions
- Input validation routines

### Step 2: Write Minimal Harness

Start with the simplest possible harness that calls your target function:

**C/C++:**
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    target_function(data, size);
    return 0;
}
```

**Rust:**
```rust
#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    target_function(data);
});
```

### Step 3: Add Input Validation

Reject inputs that are too small or too large to be meaningful:

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Ensure minimum size for meaningful input
    if (size < MIN_INPUT_SIZE || size > MAX_INPUT_SIZE) {
        return 0;
    }
    target_function(data, size);
    return 0;
}
```

**Rationale:** The fuzzer generates random inputs of all sizes. Your harness must handle empty, tiny, huge, or malformed inputs without causing unexpected issues in the harness itself (crashes in the SUT are fine—that's what we're looking for).

### Step 4: Structure the Input

For APIs that require typed data (integers, strings, etc.), use casting or helpers like `FuzzedDataProvider`:

**Simple casting:**
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size != 2 * sizeof(uint32_t)) {
        return 0;
    }

    uint32_t numerator = *(uint32_t*)(data);
    uint32_t denominator = *(uint32_t*)(data + sizeof(uint32_t));

    divide(numerator, denominator);
    return 0;
}
```

**Using FuzzedDataProvider:**
```cpp
#include "FuzzedDataProvider.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    FuzzedDataProvider fuzzed_data(data, size);

    size_t allocation_size = fuzzed_data.ConsumeIntegral<size_t>();
    std::vector<char> str1 = fuzzed_data.ConsumeBytesWithTerminator<char>(32, 0xFF);
    std::vector<char> str2 = fuzzed_data.ConsumeBytesWithTerminator<char>(32, 0xFF);

    concat(&str1[0], str1.size(), &str2[0], str2.size(), allocation_size);
    return 0;
}
```

### Step 5: Test and Iterate

Run the fuzzer and monitor:
- Code coverage (are all interesting paths reached?)
- Executions per second (is it fast enough?)
- Crash reproducibility (can you reproduce crashes with saved inputs?)

Iterate on the harness to improve these metrics.


## Common Patterns

### Pattern: Beyond Byte Arrays—Casting to Integers

**Use Case:** When target expects primitive types like integers or floats

**Implementation:**
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Ensure exactly 2 4-byte numbers
    if (size != 2 * sizeof(uint32_t)) {
        return 0;
    }

    // Split input into two integers
    uint32_t numerator = *(uint32_t*)(data);
    uint32_t denominator = *(uint32_t*)(data + sizeof(uint32_t));

    divide(numerator, denominator);
    return 0;
}
```

**Rust equivalent:**
```rust
fuzz_target!(|data: &[u8]| {
    if data.len() != 2 * std::mem::size_of::<i32>() {
        return;
    }

    let numerator = i32::from_ne_bytes([data[0], data[1], data[2], data[3]]);
    let denominator = i32::from_ne_bytes([data[4], data[5], data[6], data[7]]);

    divide(numerator, denominator);
});
```

**Why it works:** Any 8-byte input is valid. The fuzzer learns that inputs must be exactly 8 bytes, and every bit flip produces a new, potentially interesting input.

### Pattern: FuzzedDataProvider for Complex Inputs

**Use Case:** When target requires multiple strings, integers, or variable-length data

**Implementation:**
```cpp
#include "FuzzedDataProvider.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    FuzzedDataProvider fuzzed_data(data, size);

    // Extract different types of data
    size_t allocation_size = fuzzed_data.ConsumeIntegral<size_t>();

    // Consume variable-length strings with terminator
    std::vector<char> str1 = fuzzed_data.ConsumeBytesWithTerminator<char>(32, 0xFF);
    std::vector<char> str2 = fuzzed_data.ConsumeBytesWithTerminator<char>(32, 0xFF);

    char* result = concat(&str1[0], str1.size(), &str2[0], str2.size(), allocation_size);
    if (result != NULL) {
        free(result);
    }

    return 0;
}
```

**Why it helps:** `FuzzedDataProvider` handles the complexity of extracting structured data from a byte stream. It's particularly useful for APIs that need multiple parameters of different types.

### Pattern: Interleaved Fuzzing

**Use Case:** When multiple related operations should be tested in a single harness

**Implementation:**
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < 1 + 2 * sizeof(int32_t)) {
        return 0;
    }

    // First byte selects operation
    uint8_t mode = data[0];

    // Next bytes are operands
    int32_t numbers[2];
    memcpy(numbers, data + 1, 2 * sizeof(int32_t));

    int32_t result = 0;
    switch (mode % 4) {
        case 0:
            result = add(numbers[0], numbers[1]);
            break;
        case 1:
            result = subtract(numbers[0], numbers[1]);
            break;
        case 2:
            result = multiply(numbers[0], numbers[1]);
            break;
        case 3:
            result = divide(numbers[0], numbers[1]);
            break;
    }

    // Prevent compiler from optimizing away the calls
    printf("%d", result);
    return 0;
}
```

**Advantages:**
- Faster to write one harness than multiple individual harnesses
- Single shared corpus means interesting inputs for one operation may be interesting for others
- Can discover bugs in interactions between operations

**When to use:**
- Operations share similar input types
- Operations are logically related (e.g., arithmetic operations, CRUD operations)
- Single corpus makes sense across all operations

### Pattern: Structure-Aware Fuzzing with Arbitrary (Rust)

**Use Case:** When fuzzing Rust code that uses custom structs

**Implementation:**
```rust
use arbitrary::Arbitrary;

#[derive(Debug, Arbitrary)]
pub struct Name {
    data: String
}

impl Name {
    pub fn check_buf(&self) {
        let data = self.data.as_bytes();
        if data.len() > 0 && data[0] == b'a' {
            if data.len() > 1 && data[1] == b'b' {
                if data.len() > 2 && data[2] == b'c' {
                    process::abort();
                }
            }
        }
    }
}
```

**Harness with arbitrary:**
```rust
#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: your_project::Name| {
    data.check_buf();
});
```

**Add to Cargo.toml:**
```toml
[dependencies]
arbitrary = { version = "1", features = ["derive"] }
```

**Why it helps:** The `arbitrary` crate automatically handles deserialization of raw bytes into your Rust structs, reducing boilerplate and ensuring valid struct construction.

**Limitation:** The arbitrary crate doesn't offer reverse serialization, so you can't manually construct byte arrays that map to specific structs. This works best when starting from an empty corpus (fine for libFuzzer, problematic for AFL++).
