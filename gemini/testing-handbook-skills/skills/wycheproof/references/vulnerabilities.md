# Vulnerabilities

## Common Vulnerabilities Detected

Wycheproof test vectors are designed to catch specific vulnerability patterns:

| Vulnerability | Description | Affected Algorithms | Example CVE |
|---------------|-------------|---------------------|-------------|
| Signature malleability | Multiple valid signatures for same message | ECDSA, EdDSA | CVE-2024-42459 |
| Invalid DER encoding | Accepting non-canonical DER signatures | ECDSA | CVE-2024-42460, CVE-2024-42461 |
| Invalid curve attacks | ECDH with invalid curve points | ECDH | Common in many libraries |
| Padding oracle | Timing leaks in padding validation | RSA-PKCS1 | Historical OpenSSL issues |
| Tag forgery | Accepting modified authentication tags | AES-GCM, ChaCha20-Poly1305 | Various implementations |

### Signature Malleability: Deep Dive

**Problem:** Implementations that don't validate signature encoding can accept multiple valid signatures for the same message.

**Example (EdDSA):** Appending or removing zeros from signature:
```text
Valid signature:   ...6a5c51eb6f946b30d
Invalid signature: ...6a5c51eb6f946b30d0000  (should be rejected)
```

**How to detect:**
```python
# Add signature length check
if len(sig) != 128:  # EdDSA signatures must be exactly 64 bytes (128 hex chars)
    return False
```

**Impact:** Can lead to consensus problems when different implementations accept/reject the same signatures.

**Related Wycheproof tests:**
- EdDSA: tcId 37 - "removing 0 byte from signature"
- ECDSA: tcId 06 - "Legacy: ASN encoding of r misses leading 0"


## Case Study: Elliptic npm Package

This case study demonstrates how Wycheproof found three CVEs in the popular elliptic npm package (3000+ dependents, millions of weekly downloads).

### Overview

The [elliptic](https://www.npmjs.com/package/elliptic) library is an elliptic-curve cryptography library written in JavaScript, supporting ECDH, ECDSA, and EdDSA. Using Wycheproof test vectors on version 6.5.6 revealed multiple vulnerabilities:

- **CVE-2024-42459**: EdDSA signature malleability (appending/removing zeros)
- **CVE-2024-42460**: ECDSA DER encoding - invalid bit placement
- **CVE-2024-42461**: ECDSA DER encoding - leading zero in length field

### Methodology

1. **Identify supported curves**: ed25519 for EdDSA
2. **Find test vectors**: `testvectors_v1/ed25519_test.json`
3. **Parse test vectors**: Load JSON and extract tests
4. **Write test harness**: Create parameterized tests
5. **Run tests**: Identify failures
6. **Analyze root causes**: Examine implementation code
7. **Propose fixes**: Add validation checks

### Key Findings

**EdDSA Issue (CVE-2024-42459):**
- Missing signature length validation
- Allowed trailing zeros in signatures
- Fix: Add `if(sig.length !== 128) return false;`

**ECDSA Issue 1 (CVE-2024-42460):**
- Missing check for first bit being zero in DER-encoded r and s values
- Fix: Add `if ((data[p.place] & 128) !== 0) return false;`

**ECDSA Issue 2 (CVE-2024-42461):**
- DER length field accepted leading zeros
- Fix: Add `if(buf[p.place] === 0x00) return false;`

### Impact

All three vulnerabilities allowed multiple valid signatures for a single message, leading to consensus problems across implementations.

**Lessons learned:**
- Wycheproof catches subtle encoding bugs
- Reusable test harnesses pay dividends
- Test vector comments and flags help diagnose issues
- Even popular libraries benefit from systematic test vector validation


## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Filter test groups by parameters | Focus on test vectors relevant to your implementation constraints |
| Use test vector flags | Understand specific vulnerability patterns being tested |
| Check the `notes` field | Get detailed explanations of flag meanings |
| Test both encrypt/decrypt and sign/verify | Ensure bidirectional correctness |
| Run tests in CI | Catch regressions and benefit from new test vectors |
| Use parameterized tests | Get clear failure messages with tcId and comment |

### Common Mistakes

| Mistake | Why It's Wrong | Correct Approach |
|---------|----------------|------------------|
| Only testing valid cases | Misses vulnerabilities where invalid inputs are accepted | Test all result types: valid, invalid, acceptable |
| Ignoring "acceptable" result | Implementation might have subtle bugs | Treat acceptable as warnings worth investigating |
| Not filtering test groups | Wastes time on unsupported parameters | Filter by keySize, ivSize, etc. based on your implementation |
| Not updating test vectors | Miss new vulnerability patterns | Use submodules or scheduled fetches |
| Testing only one direction | Encrypt/sign might work but decrypt/verify fails | Test both operations |
