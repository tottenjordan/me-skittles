# Customization

## How to Customize

### Writing Custom Queries

CodeQL queries use a declarative, object-oriented language called QL with Java-like syntax and SQL-like query expressions.

**Basic query structure:**
```ql
import cpp

from FunctionCall call
where call.getTarget().getName() = "memcpy"
select call.getLocation(), call.getArgument(0)
```

This selects all expressions passed as the first argument to `memcpy`.

**Creating a custom class:**
```ql
import cpp

class MemcpyCall extends FunctionCall {
  MemcpyCall() {
    this.getTarget().getName() = "memcpy"
  }

  Expr getDestination() {
    result = this.getArgument(0)
  }

  Expr getSource() {
    result = this.getArgument(1)
  }

  Expr getSize() {
    result = this.getArgument(2)
  }
}

from MemcpyCall call
select call.getLocation(), call.getDestination()
```

### Key Syntax Reference

| Syntax/Operator | Description | Example |
|-----------------|-------------|---------|
| `from Type x where P(x) select f(x)` | Query: select f(x) for all x where P(x) is true | `from FunctionCall call where call.getTarget().getName() = "memcpy" select call` |
| `exists(...)` | Existential quantification | `exists(FunctionCall call \| call.getTarget() = fun)` |
| `forall(...)` | Universal quantification | `forall(Expr e \| e = arg.getAChild() \| e.isConstant())` |
| `+` | Transitive closure (1+ times) | `start.getASuccessor+()` |
| `*` | Reflexive transitive closure (0+ times) | `start.getASuccessor*()` |
| `result` | Special variable for method/function output | `result = this.getArgument(0)` |

### Example: Finding Unhandled Errors

```ql
import cpp

/**
 * @name Unhandled error return value
 * @id custom/unhandled-error
 * @description Function calls that return error codes that are not checked
 * @kind problem
 * @problem.severity warning
 * @precision medium
 */

predicate isErrorReturningFunction(Function f) {
  f.getName().matches("%error%") or
  f.getName().matches("%Error%")
}

from FunctionCall call
where
  isErrorReturningFunction(call.getTarget()) and
  not exists(Expr parent |
    parent = call.getParent*() and
    (parent instanceof IfStmt or parent instanceof SwitchStmt)
  )
select call, "Error return value not checked"
```

### Adding Query Metadata

Query metadata is defined in an initial comment:

```ql
/**
 * @name Short name for the issue
 * @id scope/query-name
 * @description Longer description of the issue
 * @kind problem
 * @tags security external/cwe/cwe-123
 * @problem.severity error
 * @precision high
 */
```

**Required fields:**
- `name`: Short string identifying the issue
- `id`: Unique identifier (lowercase letters, numbers, `/`, `-`)
- `description`: Longer description (a few sentences)
- `kind`: Either `problem` or `path-problem`
- `problem.severity`: `error`, `warning`, or `recommendation`
- `precision`: `low`, `medium`, `high`, or `very-high`

**Output format requirements:**
- `problem` queries: Output must be `(Location, string)`
- `path-problem` queries: Output must be `(DataFlow::Node, DataFlow::PathNode, DataFlow::PathNode, string)`

### Testing Custom Queries

Create a test pack with `qlpack.yml`:

```yaml
name: scope/name-test
version: 0.0.1
dependencies:
  codeql-query-pack-to-test: "*"
extractor: cpp
```

Create a test directory (e.g., `MemcpyCall/`) containing:
- `test.c`: Source file with code pattern to detect
- `MemcpyCall.qlref`: Text file with path to the query
- `MemcpyCall.expected`: Expected output

Run tests:
```bash
codeql test run -- path/to/test/pack/
```

If `MemcpyCall.expected` is missing or incorrect, an `MemcpyCall.actual` file is created. Review it, and if correct, rename to `MemcpyCall.expected`.


## Configuration

### CodeQL Standard Libraries

CodeQL standard libraries are language-specific. Refer to API documentation:

- [C and C++](https://codeql.github.com/codeql-standard-libraries/cpp/)
- [Go](https://codeql.github.com/codeql-standard-libraries/go/)
- [Java and Kotlin](https://codeql.github.com/codeql-standard-libraries/java/)
- [JavaScript and TypeScript](https://codeql.github.com/codeql-standard-libraries/javascript/)
- [Python](https://codeql.github.com/codeql-standard-libraries/python/)
- [C#](https://codeql.github.com/codeql-standard-libraries/csharp/)
- [Ruby](https://codeql.github.com/codeql-standard-libraries/ruby/)
- [Swift](https://codeql.github.com/codeql-standard-libraries/swift/)

### Supported Languages

CodeQL supports C/C++, C#, Go, Java, Kotlin, JavaScript, TypeScript, Python, Ruby, and Swift. Check [supported languages and frameworks](https://codeql.github.com/docs/codeql-overview/supported-languages-and-frameworks) for details.
