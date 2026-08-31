---
name: constant-time-testing
type: domain
description: >
  Constant-time testing detects timing side channels in cryptographic code.
  Use when auditing crypto implementations for timing vulnerabilities.
---

# Constant-Time Testing

Timing attacks exploit variations in execution time to extract secret information from cryptographic implementations. Unlike cryptanalysis that targets theoretical weaknesses, timing attacks leverage implementation flaws - and they can affect any cryptographic code.

## Background

Timing attacks were introduced by [Kocher](https://paulkocher.com/doc/TimingAttacks.pdf) in 1996. Since then, researchers have demonstrated practical attacks on RSA ([Schindler](https://link.springer.com/content/pdf/10.1007/3-540-44499-8_8.pdf)), OpenSSL ([Brumley and Boneh](https://crypto.stanford.edu/~dabo/papers/ssl-timing.pdf)), AES implementations, and even post-quantum algorithms like [Kyber](https://eprint.iacr.org/2024/1049.pdf).

### Key Concepts

| Concept | Description |
|---------|-------------|
| Constant-time | Code path and memory accesses independent of secret data |
| Timing leakage | Observable execution time differences correlated with secrets |
| Side channel | Information extracted from implementation rather than algorithm |
| Microarchitecture | CPU-level timing differences (cache, division, shifts) |

### Why This Matters

Timing vulnerabilities can:
- **Expose private keys** - Extract secret exponents in RSA/ECDH
- **Enable remote attacks** - Network-observable timing differences
- **Bypass cryptographic security** - Undermine theoretical guarantees
- **Persist silently** - Often undetected without specialized analysis

Two prerequisites enable exploitation:
1. **Access to oracle** - Sufficient queries to the vulnerable implementation
2. **Timing dependency** - Correlation between execution time and secret data

### Common Constant-Time Violation Patterns

Four patterns account for most timing vulnerabilities:

```c
// 1. Conditional jumps - most severe timing differences
if(secret == 1) { ... }
while(secret > 0) { ... }

// 2. Array access - cache-timing attacks
lookup_table[secret];

// 3. Integer division (processor dependent)
data = secret / m;

// 4. Shift operation (processor dependent)
data = a << secret;
```

**Conditional jumps** cause different code paths, leading to vast timing differences.

**Array access** dependent on secrets enables cache-timing attacks, as shown in [AES cache-timing research](https://cr.yp.to/antiforgery/cachetiming-20050414.pdf).

**Integer division and shift operations** leak secrets on certain CPU architectures and compiler configurations.

When patterns cannot be avoided, employ [masking techniques](https://link.springer.com/chapter/10.1007/978-3-642-38348-9_9) to remove correlation between timing and secrets.

### Example: Modular Exponentiation Timing Attacks

Modular exponentiation (used in RSA and Diffie-Hellman) is susceptible to timing attacks. RSA decryption computes:

$$ct^{d} \mod{N}$$

where $d$ is the secret exponent. The *exponentiation by squaring* optimization reduces multiplications to $\log{d}$:

$$
\begin{align*}
& \textbf{Input: } \text{base }y,\text{exponent } d=\{d_n,\cdots,d_0\}_2,\text{modulus } N \\
& r = 1 \\
& \textbf{for } i=|n| \text{ downto } 0: \\
& \quad\textbf{if } d_i == 1: \\
& \quad\quad r = r * y \mod{N} \\
& \quad y = y * y \mod{N} \\
& \textbf{return }r
\end{align*}
$$

The code branches on exponent bit $d_i$, violating constant-time principles. When $d_i = 1$, an additional multiplication occurs, increasing execution time and leaking bit information.

Montgomery multiplication (commonly used for modular arithmetic) also leaks timing: when intermediate values exceed modulus $N$, an additional reduction step is required. An attacker constructs inputs $y$ and $y'$ such that:

$$
\begin{align*}
y^2 < y^3 < N \\
y'^2 < N \leq y'^3
\end{align*}
$$

For $y$, both multiplications take time $t_1+t_1$. For $y'$, the second multiplication requires reduction, taking time $t_1+t_2$. This timing difference reveals whether $d_i$ is 0 or 1.

## When to Use

**Apply constant-time analysis when:**
- Auditing cryptographic implementations (primitives, protocols)
- Code handles secret keys, passwords, or sensitive cryptographic material
- Implementing crypto algorithms from scratch
- Reviewing PRs that touch crypto code
- Investigating potential timing vulnerabilities

**Consider alternatives when:**
- Code does not process secret data
- Public algorithms with no secret inputs
- Non-cryptographic timing requirements (performance optimization)

## Quick Reference

| Scenario | Recommended Approach | Skill |
|----------|---------------------|-------|
| Prove absence of leaks | Formal verification | SideTrail, ct-verif, FaCT |
| Detect statistical timing differences | Statistical testing | **dudect** |
| Track secret data flow at runtime | Dynamic analysis | **timecop** |
| Find cache-timing vulnerabilities | Symbolic execution | Binsec, pitchfork |

## Testing Workflow

```
Phase 1: Static Analysis        Phase 2: Statistical Testing
┌─────────────────┐            ┌─────────────────┐
│ Identify secret │      →     │ Detect timing   │
│ data flow       │            │ differences     │
│ Tool: ct-verif  │            │ Tool: dudect    │
└─────────────────┘            └─────────────────┘
         ↓                              ↓
Phase 4: Root Cause             Phase 3: Dynamic Tracing
┌─────────────────┐            ┌─────────────────┐
│ Pinpoint leak   │      ←     │ Track secret    │
│ location        │            │ propagation     │
│ Tool: Timecop   │            │ Tool: Timecop   │
└─────────────────┘            └─────────────────┘
```

**Recommended approach:**
1. **Start with dudect** - Quick statistical check for timing differences
2. **If leaks found** - Use Timecop to pinpoint root cause
3. **For high-assurance** - Apply formal verification (ct-verif, SideTrail)
4. **Continuous monitoring** - Integrate dudect into CI pipeline

## Reference material

**[references/tooling.md](references/tooling.md)** — tooling categories and the available tools

**[references/implementation.md](references/implementation.md)** — the implementation guide, vulnerability classes, case studies, and advanced usage

## Related Skills

### Tool Skills

| Skill | Primary Use in Constant-Time Analysis |
|-------|---------------------------------------|
| **dudect** | Statistical detection of timing differences via Welch's t-test |
| **timecop** | Dynamic tracing to pinpoint exact location of timing leaks |

### Technique Skills

| Skill | When to Apply |
|-------|---------------|
| **coverage-analysis** | Ensure test inputs exercise all code paths in crypto function |
| **ci-integration** | Automate constant-time testing in continuous integration pipeline |

### Related Domain Skills

| Skill | Relationship |
|-------|--------------|
| **crypto-testing** | Constant-time analysis is essential component of cryptographic testing |
| **fuzzing** | Fuzzing crypto code may trigger timing-dependent paths |

## Skill Dependency Map

```
                    ┌─────────────────────────┐
                    │  constant-time-analysis │
                    │     (this skill)        │
                    └───────────┬─────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────┐           ┌───────────────────┐
    │      dudect       │           │     timecop       │
    │  (statistical)    │           │    (dynamic)      │
    └────────┬──────────┘           └────────┬──────────┘
             │                               │
             └───────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   Supporting Techniques      │
              │ coverage, CI integration     │
              └──────────────────────────────┘
```

## Resources

### Key External Resources

**[These results must be false: A usability evaluation of constant-time analysis tools](https://www.usenix.org/system/files/sec24fall-prepub-760-fourne.pdf)**
Comprehensive usability study of constant-time analysis tools. Key findings: developers struggle with false positives, need better error messages, and benefit from tool integration. Evaluates FaCT, ct-verif, dudect, and Memsan across multiple cryptographic implementations. Recommends improved tooling UX and better documentation.

**[List of constant-time tools - CROCS](https://crocs-muni.github.io/ct-tools/)**
Curated catalog of constant-time analysis tools with tutorials. Covers formal tools (ct-verif, FaCT), dynamic tools (Memsan, Timecop), symbolic tools (Binsec), and statistical tools (dudect). Includes practical tutorials for setup and usage.

**[Paul Kocher: Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems](https://paulkocher.com/doc/TimingAttacks.pdf)**
Original 1996 paper introducing timing attacks. Demonstrates attacks on modular exponentiation in RSA and Diffie-Hellman. Essential historical context for understanding timing vulnerabilities.

**[Remote Timing Attacks are Practical (Brumley & Boneh)](https://crypto.stanford.edu/~dabo/papers/ssl-timing.pdf)**
Demonstrates practical remote timing attacks against OpenSSL. Shows network-level timing differences are sufficient to extract RSA keys. Proves timing attacks work in realistic network conditions.

**[Cache-timing attacks on AES](https://cr.yp.to/antiforgery/cachetiming-20050414.pdf)**
Shows AES implementations using lookup tables are vulnerable to cache-timing attacks. Demonstrates practical attacks extracting AES keys via cache timing side channels.

**[KyberSlash: Division Timings Leak Secrets](https://eprint.iacr.org/2024/1049.pdf)**
Recent discovery of timing vulnerabilities in Kyber (NIST post-quantum standard). Shows division operations leak secret coefficients. Highlights that constant-time issues persist even in modern post-quantum cryptography.

### Video Resources

- [Trail of Bits: Constant-Time Programming](https://www.youtube.com/watch?v=vW6wqTzfz5g) - Overview of constant-time programming principles and tools
