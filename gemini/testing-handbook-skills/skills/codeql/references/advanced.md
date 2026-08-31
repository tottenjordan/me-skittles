# Advanced

## Advanced Usage

### Creating New Query Packs

Initialize a query pack:
```bash
codeql pack init <scope>/<name>
```

This creates a `qlpack.yml` file:
```yaml
---
library: false
warnOnImplicitThis: false
name: <scope>/<name>
version: 0.0.1
```

Add standard library dependencies:
```bash
codeql pack add codeql/cpp-all
```

Create a workspace file (`codeql-workspace.yml`) for the CLI to work correctly.

Install dependencies:
```bash
codeql pack install
```

Configure the CLI to find your queries by creating `~/.config/codeql/config`:
```plain
--search-path /full/path/to/your/codeql/root/directory
```

### Recommended Directory Structure

```plain
.
├── codeql-workspace.yml
├── cpp
│   ├── lib
│   │   ├── qlpack.yml
│   │   └── scope
│   │       └── security
│   │           └── someLibrary.qll
│   ├── src
│   │   ├── qlpack.yml
│   │   ├── suites
│   │   │   ├── scope-cpp-code-scanning.qls
│   │   │   └── scope-cpp-security.qls
│   │   └── security
│   │       └── AppSecAnalysis
│   │           ├── AppSecAnalysis.c
│   │           ├── AppSecAnalysis.qhelp
│   │           └── AppSecAnalysis.ql
│   └── test
│       ├── qlpack.yml
│       └── query-tests
│           └── security
│               └── AppSecAnalysis
│                   ├── AppSecAnalysis.c
│                   ├── AppSecAnalysis.expected
│                   └── AppSecAnalysis.qlref
```

### Recursion and Transitive Closures

**Recursive predicate:**
```ql
predicate isReachableFrom(BasicBlock start, BasicBlock end) {
  start = end or isReachableFrom(start.getASuccessor(), end)
}
```

**Using transitive closure (equivalent):**
```ql
predicate isReachableFrom(BasicBlock start, BasicBlock end) {
  end = start.getASuccessor*()
}
```

Use `*` for zero or more applications, `+` for one or more.

### Excluding Individual Files

CodeQL instruments the build process. If object files already exist and are up-to-date, corresponding source files won't be added to the database. This can reduce database size but means CodeQL has only partial knowledge about excluded files and cannot reason about data flow through them.

**Recommendation:** Include third-party libraries and filter issues based on location rather than excluding files during database creation.

### Editor Support

**VSCode:** [CodeQL extension](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-codeql) provides LSP support, syntax highlighting, query running, and AST visualization.

**Neovim:** [codeql.nvim](https://github.com/pwntester/codeql.nvim) provides similar functionality.

**Helix/Other editors:** Use the CodeQL LSP server and [Tree-sitter grammar for CodeQL](https://github.com/tree-sitter/tree-sitter-ql).

**VSCode Quick Query:** Use "CodeQL: Quick Query" command to run single queries against a database.

**Debugging queries:** Add database source to workspace, then use "CodeQL: View AST" to display the AST for individual nodes.


## CI/CD Integration

### GitHub Actions

Enable code scanning from "Code security and analysis" in repository settings. Choose default or advanced setup.

**Advanced setup workflow:**
```yaml
name: "CodeQL"

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '34 10 * * 6'

jobs:
  analyze:
    name: Analyze
    runs-on: ${{ (matrix.language == 'swift' && 'macos-latest') || 'ubuntu-latest' }}
    timeout-minutes: ${{ (matrix.language == 'swift' && 120) || 360 }}

    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: [ 'cpp' ]

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Initialize CodeQL
      uses: github/codeql-action/init@v3
      with:
        languages: ${{ matrix.language }}

    - name: Autobuild
      uses: github/codeql-action/autobuild@v3

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v3
      with:
        category: "/language:${{matrix.language}}"
```

For compiled languages, replace autobuild with custom build commands:
```yaml
- run: |
    make -j8
```

### Using Custom Queries in CI

Specify query packs and queries in the "Initialize CodeQL" step:

```yaml
- uses: github/codeql-action/init@v3
  with:
    queries: security-extended,security-and-quality
    packs: trailofbits/cpp-queries
```

For repository-local queries:
```yaml
- uses: github/codeql-action/init@v3
  with:
    queries: ./codeql/UnhandledError.ql
    packs: trailofbits/cpp-queries
```

Note the `.` prefix for repository-relative paths. All queries must be part of a query pack with a `qlpack.yml` file.

### Testing Custom Queries in CI

```yaml
name: Test CodeQL queries

on: [push, pull_request]

jobs:
  codeql-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: init
        uses: github/codeql-action/init@v3
      - uses: actions/cache@v4
        with:
          path: ~/.codeql
          key: ${{ runner.os }}-${{ runner.arch }}-${{ steps.init.outputs.codeql-version }}
      - name: Run tests
        run: |
          ${{ steps.init.outputs.codeql-path }} test run ./path/to/query/tests/
```

This workflow caches query extraction and compilation for faster subsequent runs.
