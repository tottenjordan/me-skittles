# Advanced

## Advanced Usage

### Tips and Tricks

| Tip | Why It Helps |
|-----|--------------|
| Use `--time` flag | Identifies slow rules and files for optimization |
| Limit ellipsis usage | Reduces false positives and improves performance |
| Use `pattern-inside` for context | Creates clearer, more focused findings |
| Enable autocomplete | Speeds up command-line workflow |
| Use `focus-metavariable` | Highlights specific code locations in output |

### Scanning Non-Standard Extensions

Force language interpretation for unusual file extensions:

```bash
semgrep --config=/path/to/config --lang python --scan-unknown-extensions /path/to/file.xyz
```

### Dataflow Tracing

Use `--dataflow-traces` to understand how values flow to findings:

```bash
semgrep --dataflow-traces -f taint_rule.yml test.py
```

Example output:

```
Taint comes from:
  test.py
    2┆ data = get_user_input()

This is how taint reaches the sink:
  test.py
    3┆ return output(data)
```

### Polyglot File Scanning

Scan embedded languages (e.g., JavaScript in HTML):

```yaml
rules:
  - id: eval-in-html
    languages: [html]
    message: eval in JavaScript
    patterns:
      - pattern: <script ...>$Y</script>
      - metavariable-pattern:
          metavariable: $Y
          language: javascript
          patterns:
            - pattern: eval(...)
    severity: WARNING
```

### Constant Propagation

Match instances where metavariables hold specific values:

```yaml
rules:
  - id: high-value-check
    languages: [python]
    message: $X is higher than 1337
    patterns:
      - pattern: function($X)
      - metavariable-comparison:
          metavariable: $X
          comparison: $X > 1337
    severity: WARNING
```

### Autofix Feature

Add automatic fixes to rules:

```yaml
rules:
  - id: ioutil-readdir-deprecated
    languages: [golang]
    message: ioutil.ReadDir is deprecated. Use os.ReadDir instead.
    severity: WARNING
    pattern: ioutil.ReadDir($X)
    fix: os.ReadDir($X)
```

Preview fixes without applying:

```bash
semgrep -f rule.yaml --dryrun --autofix
```

Apply fixes:

```bash
semgrep -f rule.yaml --autofix
```

### Performance Optimization

Analyze performance:

```bash
semgrep --config=auto --time
```

Optimize rules:
1. Use `paths` to narrow file scope
2. Minimize ellipsis usage
3. Use `pattern-inside` to establish context first
4. Remove unnecessary metavariables

### Managing Third-Party Rules

Use [semgrep-rules-manager](https://github.com/iosifache/semgrep-rules-manager/) to collect third-party rules:

```bash
pip install semgrep-rules-manager
mkdir -p $HOME/custom-semgrep-rules
semgrep-rules-manager --dir $HOME/custom-semgrep-rules download
semgrep -f $HOME/custom-semgrep-rules
```


## CI/CD Integration

### GitHub Actions

#### Recommended Approach

1. Full scan on main branch with broad rulesets (scheduled)
2. Diff-aware scanning for pull requests with focused rules
3. Block PRs with unresolved findings (once mature)

#### Example Workflow

```yaml
name: Semgrep
on:
  pull_request: {}
  push:
    branches: ["master", "main"]
  schedule:
    - cron: '0 0 1 * *' # Monthly

jobs:
  semgrep-schedule:
    if: ((github.event_name == 'schedule' || github.event_name == 'push' || github.event.pull_request.merged == true)
        && github.actor != 'dependabot[bot]')
    name: Semgrep default scan
    runs-on: ubuntu-latest
    container:
      image: returntocorp/semgrep
    steps:
      - name: Checkout main repository
        uses: actions/checkout@v4
      - run: semgrep ci
        env:
          SEMGREP_RULES: p/default

  semgrep-pr:
    if: (github.event_name == 'pull_request' && github.actor != 'dependabot[bot]')
    name: Semgrep PR scan
    runs-on: ubuntu-latest
    container:
      image: returntocorp/semgrep
    steps:
      - uses: actions/checkout@v4
      - run: semgrep ci
        env:
          SEMGREP_RULES: >
            p/cwe-top-25
            p/owasp-top-ten
            p/r2c-security-audit
            p/trailofbits
```

#### Adding Custom Rules in CI

**Rules in same repository:**

```yaml
env:
  SEMGREP_RULES: p/default custom-semgrep-rules-dir/
```

**Rules in private repository:**

```yaml
env:
  SEMGREP_PRIVATE_RULES_REPO: semgrep-private-rules
steps:
  - name: Checkout main repository
    uses: actions/checkout@v4
  - name: Checkout private custom Semgrep rules
    uses: actions/checkout@v4
    with:
      repository: ${{ github.repository_owner }}/${{ env.SEMGREP_PRIVATE_RULES_REPO }}
      token: ${{ secrets.SEMGREP_RULES_TOKEN }}
      path: ${{ env.SEMGREP_PRIVATE_RULES_REPO }}
  - run: semgrep ci
    env:
      SEMGREP_RULES: ${{ env.SEMGREP_PRIVATE_RULES_REPO }}
```

### Testing Rules in CI

```yaml
name: Test Semgrep rules

on: [push, pull_request]

jobs:
  semgrep-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
          cache: "pip"
      - run: python -m pip install -r requirements.txt
      - run: semgrep --test --test-ignore-todo ./path/to/rules/
```
