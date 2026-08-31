# Customization

## How to Customize

### Writing Custom Rules

Semgrep rules are YAML files with pattern-matching syntax. Basic structure:

```yaml
rules:
  - id: rule-id
    languages: [go]
    message: Some message
    severity: ERROR # INFO / WARNING / ERROR
    pattern: test(...)
```

### Running Custom Rules

```bash
# Single file
semgrep --config custom_rule.yaml

# Directory of rules
semgrep --config path/to/rules/
```

### Key Syntax Reference

| Syntax/Operator | Description | Example |
|-----------------|-------------|---------|
| `...` | Match zero or more arguments/statements | `func(..., arg=value, ...)` |
| `$X`, `$VAR` | Metavariable (captures and tracks values) | `$FUNC($INPUT)` |
| `<... ...>` | Deep expression operator (nested matching) | `if <... user.is_admin() ...>:` |
| `pattern-inside` | Match only within context | Pattern inside a loop |
| `pattern-not` | Exclude specific patterns | Negative matching |
| `pattern-either` | Logical OR (any pattern matches) | Multiple alternatives |
| `patterns` | Logical AND (all patterns match) | Combined conditions |
| `metavariable-pattern` | Nested metavariable constraints | Constrain captured values |
| `metavariable-comparison` | Compare metavariable values | `$X > 1337` |

### Example: Detecting Insecure Request Verification

```yaml
rules:
  - id: requests-verify-false
    languages: [python]
    message: requests.get with verify=False disables SSL verification
    severity: WARNING
    pattern: requests.get(..., verify=False, ...)
```

### Example: Taint Mode for SQL Injection

```yaml
rules:
  - id: sql-injection
    mode: taint
    pattern-sources:
      - pattern: request.args.get(...)
    pattern-sinks:
      - pattern: cursor.execute($QUERY)
    pattern-sanitizers:
      - pattern: int(...)
    message: Potential SQL injection with unsanitized user input
    languages: [python]
    severity: ERROR
```

### Testing Custom Rules

Create test files with annotations:

```python
# ruleid: requests-verify-false
requests.get(url, verify=False)

# ok: requests-verify-false
requests.get(url, verify=True)
```

Run tests:

```bash
semgrep --test ./path/to/rules/
```

For autofix testing, create `.fixed` files (e.g., `test.py` → `test.fixed.py`):

```bash
semgrep --test
# Output: 1/1: ✓ All tests passed
#         1/1: ✓ All fix tests passed
```


## Configuration

### Configuration File

Semgrep doesn't require a central config file. Configuration is done via:
- Command-line flags
- Environment variables
- `.semgrepignore` for path exclusions

### Ignore Patterns

Create `.semgrepignore` in repository root:

```
# Ignore directories
tests/
vendor/
node_modules/

# Ignore file types
*.min.js
*.generated.go

# Include .gitignore patterns
:include .gitignore
```

### Suppressing False Positives

Add inline comments to suppress specific findings:

```python
# nosemgrep: rule-id
risky_function()
```

**Best practices:**
- Specify the exact rule ID (not generic `# nosemgrep`)
- Explain why the rule is disabled
- Report false positives to improve rules

### Metadata in Custom Rules

Include metadata for better context:

```yaml
rules:
  - id: example-rule
    metadata:
      cwe: "CWE-89"
      confidence: HIGH
      likelihood: MEDIUM
      impact: HIGH
      subcategory: vuln
    # ... rest of rule
```
