# Implementation

## Implementation Guide

### Phase 1: Initial Assessment

**Identify cryptographic code handling secrets:**
- Private keys, exponents, nonces
- Password hashes, authentication tokens
- Encryption/decryption operations

**Quick statistical check:**
1. Write dudect harness for the crypto function
2. Run for 5-10 minutes with `timeout 600 ./ct_test`
3. Monitor t-value: high absolute values indicate leakage

**Tools:** dudect
**Expected time:** 1-2 hours (harness writing + initial run)

### Phase 2: Detailed Analysis

If dudect detects leakage:

**Root cause investigation:**
1. Mark secret variables with Timecop `poison()`
2. Run under Valgrind to identify exact line
3. Review the four common violation patterns
4. Check assembly output for conditional branches

**Tools:** Timecop, compiler output (`objdump -d`)

### Phase 3: Remediation

**Fix the timing leak:**
- Replace conditional branches with constant-time selection (bitwise operations)
- Use constant-time comparison functions
- Replace array lookups with constant-time alternatives or masking
- Verify compiler doesn't optimize away constant-time code

**Re-verify:**
1. Run dudect again for extended period (30+ minutes)
2. Test across different compilers and optimization levels
3. Test on different CPU architectures

### Phase 4: Continuous Monitoring

**Integrate into CI:**
- Add dudect tests to test suite
- Run for fixed duration (5-10 minutes in CI)
- Fail build if leakage detected

See the **dudect** skill for CI integration examples.


## Common Vulnerabilities

| Vulnerability | Description | Detection | Severity |
|---------------|-------------|-----------|----------|
| Secret-dependent branch | `if (secret_bit) { ... }` | dudect, Timecop | CRITICAL |
| Secret-dependent array access | `table[secret_index]` | Timecop, Binsec | HIGH |
| Variable-time division | `result = x / secret` | Timecop | MEDIUM |
| Variable-time shift | `result = x << secret` | Timecop | MEDIUM |
| Montgomery reduction leak | Extra reduction when intermediate > N | dudect | HIGH |

### Secret-Dependent Branch: Deep Dive

**The vulnerability:**
Execution time differs based on whether branch is taken. Common in optimized modular exponentiation (square-and-multiply).

**How to detect with dudect:**
```c
uint8_t do_one_computation(uint8_t *data) {
    uint64_t base = ((uint64_t*)data)[0];
    uint64_t exponent = ((uint64_t*)data)[1]; // Secret!
    return mod_exp(base, exponent, MODULUS);
}

void prepare_inputs(dudect_config_t *c, uint8_t *input_data, uint8_t *classes) {
    for (size_t i = 0; i < c->number_measurements; i++) {
        classes[i] = randombit();
        uint64_t *input = (uint64_t*)(input_data + i * c->chunk_size);
        input[0] = rand(); // Random base
        input[1] = (classes[i] == 0) ? FIXED_EXPONENT : rand(); // Fixed vs random
    }
}
```

**How to detect with Timecop:**
```c
poison(&exponent, sizeof(exponent));
result = mod_exp(base, exponent, modulus);
unpoison(&exponent, sizeof(exponent));
```

Valgrind will report:
```
Conditional jump or move depends on uninitialised value(s)
  at 0x40115D: mod_exp (example.c:14)
```

**Related skill:** **dudect**, **timecop**


## Case Studies

### Case Study: OpenSSL RSA Timing Attack

Brumley and Boneh (2005) extracted RSA private keys from OpenSSL over a network. The vulnerability exploited Montgomery multiplication's variable-time reduction step.

**Attack vector:** Timing differences in modular exponentiation
**Detection approach:** Statistical analysis (precursor to dudect)
**Impact:** Remote key extraction

**Tools used:** Custom timing measurement
**Techniques applied:** Statistical analysis, chosen-ciphertext queries

### Case Study: KyberSlash

Post-quantum algorithm Kyber's reference implementation contained timing vulnerabilities in polynomial operations. Division operations leaked secret coefficients.

**Attack vector:** Secret-dependent division timing
**Detection approach:** Dynamic analysis and statistical testing
**Impact:** Secret key recovery in post-quantum cryptography

**Tools used:** Timing measurement tools
**Techniques applied:** Differential timing analysis


## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Pin dudect to isolated CPU core (`taskset -c 2`) | Reduces OS noise, improves signal detection |
| Test multiple compilers (gcc, clang, MSVC) | Optimizations may introduce or remove leaks |
| Run dudect for extended periods (hours) | Increases statistical confidence |
| Minimize non-crypto code in harness | Reduces noise that masks weak signals |
| Check assembly output (`objdump -d`) | Verify compiler didn't introduce branches |
| Use `-O3 -march=native` in testing | Matches production optimization levels |

### Common Mistakes

| Mistake | Why It's Wrong | Correct Approach |
|---------|----------------|------------------|
| Only testing one input distribution | May miss leaks visible with other patterns | Test fixed-vs-random, fixed-vs-fixed-different, etc. |
| Short dudect runs (< 1 minute) | Insufficient measurements for weak signals | Run 5-10+ minutes, longer for high assurance |
| Ignoring compiler optimization levels | `-O0` may hide leaks present in `-O3` | Test at production optimization level |
| Not testing on target architecture | x86 vs ARM have different timing characteristics | Test on deployment platform |
| Marking too much as secret in Timecop | False positives, unclear results | Mark only true secrets (keys, not public data) |
