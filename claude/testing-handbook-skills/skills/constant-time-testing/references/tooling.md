# Tooling

## Constant-Time Tooling Categories

The cryptographic community has developed four categories of timing analysis tools:

| Category | Approach | Pros | Cons |
|----------|----------|------|------|
| **Formal** | Mathematical proof on model | Guarantees absence of leaks | Complexity, modeling assumptions |
| **Symbolic** | Symbolic execution paths | Concrete counterexamples | Time-intensive path exploration |
| **Dynamic** | Runtime tracing with marked secrets | Granular, flexible | Limited coverage to executed paths |
| **Statistical** | Measure real execution timing | Practical, simple setup | No root cause, noise sensitivity |

### 1. Formal Tools

Formal verification mathematically proves timing properties on an abstraction (model) of code. Tools create a model from source/binary and verify it satisfies specified properties (e.g., variables annotated as secret).

**Popular tools:**
- [SideTrail](https://github.com/aws/s2n-tls/tree/main/tests/sidetrail)
- [ct-verif](https://github.com/imdea-software/verifying-constant-time)
- [FaCT](https://github.com/plsyssec/fact)

**Strengths:** Proof of absence, language-agnostic (LLVM bytecode)
**Weaknesses:** Requires expertise, modeling assumptions may miss real-world issues

### 2. Symbolic Tools

Symbolic execution analyzes how paths and memory accesses depend on symbolic variables (secrets). Provides concrete counterexamples. Focus on cache-timing attacks.

**Popular tools:**
- [Binsec](https://github.com/binsec/binsec)
- [pitchfork](https://github.com/PLSysSec/haybale-pitchfork)

**Strengths:** Concrete counterexamples aid debugging
**Weaknesses:** Path explosion leads to long execution times

### 3. Dynamic Tools

Dynamic analysis marks sensitive memory regions and traces execution to detect timing-dependent operations.

**Popular tools:**
- [Memsan](https://clang.llvm.org/docs/MemorySanitizer.html): [Tutorial](https://crocs-muni.github.io/ct-tools/tutorials/memsan)
- **Timecop** (see below)

**Strengths:** Granular control, targeted analysis
**Weaknesses:** Coverage limited to executed paths

> **Detailed Guidance:** See the **timecop** skill for setup and usage.

### 4. Statistical Tools

Execute code with various inputs, measure elapsed time, and detect inconsistencies. Tests actual implementation including compiler optimizations and architecture.

**Popular tools:**
- **dudect** (see below)
- [tlsfuzzer](https://github.com/tlsfuzzer/tlsfuzzer)

**Strengths:** Simple setup, practical real-world results
**Weaknesses:** No root cause info, noise obscures weak signals

> **Detailed Guidance:** See the **dudect** skill for setup and usage.


## Tools and Approaches

### Dudect - Statistical Analysis

[Dudect](https://github.com/oreparaz/dudect/) measures execution time for two input classes (fixed vs random) and uses Welch's t-test to detect statistically significant differences.

> **Detailed Guidance:** See the **dudect** skill for complete setup, usage patterns, and CI integration.

#### Quick Start for Constant-Time Analysis

```c
#define DUDECT_IMPLEMENTATION
#include "dudect.h"

uint8_t do_one_computation(uint8_t *data) {
    // Code to measure goes here
}

void prepare_inputs(dudect_config_t *c, uint8_t *input_data, uint8_t *classes) {
    for (size_t i = 0; i < c->number_measurements; i++) {
        classes[i] = randombit();
        uint8_t *input = input_data + (size_t)i * c->chunk_size;
        if (classes[i] == 0) {
            // Fixed input class
        } else {
            // Random input class
        }
    }
}
```

**Key advantages:**
- Simple C header-only integration
- Statistical rigor via Welch's t-test
- Works with compiled binaries (real-world conditions)

**Key limitations:**
- No root cause information when leak detected
- Sensitive to measurement noise
- Cannot guarantee absence of leaks (statistical confidence only)

### Timecop - Dynamic Tracing

[Timecop](https://post-apocalyptic-crypto.org/timecop/) wraps Valgrind to detect runtime operations dependent on secret memory regions.

> **Detailed Guidance:** See the **timecop** skill for installation, examples, and debugging.

#### Quick Start for Constant-Time Analysis

```c
#include "valgrind/memcheck.h"

#define poison(addr, len) VALGRIND_MAKE_MEM_UNDEFINED(addr, len)
#define unpoison(addr, len) VALGRIND_MAKE_MEM_DEFINED(addr, len)

int main() {
    unsigned long long secret_key = 0x12345678;

    // Mark secret as poisoned
    poison(&secret_key, sizeof(secret_key));

    // Any branching or memory access dependent on secret_key
    // will be reported by Valgrind
    crypto_operation(secret_key);

    unpoison(&secret_key, sizeof(secret_key));
}
```

Run with Valgrind:
```bash
valgrind --leak-check=full --track-origins=yes ./binary
```

**Key advantages:**
- Pinpoints exact line of timing leak
- No code instrumentation required
- Tracks secret propagation through execution

**Key limitations:**
- Cannot detect microarchitecture timing differences
- Coverage limited to executed paths
- Performance overhead (runs on synthetic CPU)
