# Targets

## Fuzzing Pure Python Code

For fuzzing broader parts of an application or library, use instrumentation functions:

```python
import atheris
with atheris.instrument_imports():
    import your_module
    from another_module import target_function

def test_one_input(data: bytes):
    target_function(data)

atheris.Setup(sys.argv, test_one_input)
atheris.Fuzz()
```

**Instrumentation Options:**
- `atheris.instrument_func` - Decorator for single function instrumentation
- `atheris.instrument_imports()` - Context manager for instrumenting all imported modules
- `atheris.instrument_all()` - Instrument all Python code system-wide


## Fuzzing Python C Extensions

Python C extensions require compilation with specific flags for instrumentation and sanitizer support.

### Environment Configuration

If using the provided Dockerfile, these are already configured. For local setup:

```bash
export CC="clang"
export CFLAGS="-fsanitize=address,fuzzer-no-link"
export CXX="clang++"
export CXXFLAGS="-fsanitize=address,fuzzer-no-link"
export LDSHARED="clang -shared"
```

### Example: Fuzzing cbor2

Install the extension from source:
```bash
CBOR2_BUILD_C_EXTENSION=1 python -m pip install --no-binary cbor2 cbor2==5.6.4
```

The `--no-binary` flag ensures the C extension is compiled locally with instrumentation.

Create `cbor2-fuzz.py`:
```python
import sys
import atheris

# _cbor2 ensures the C library is imported
from _cbor2 import loads

def test_one_input(data: bytes):
    try:
        loads(data)
    except Exception:
        # We're searching for memory corruption, not Python exceptions
        pass

def main():
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

Run:
```bash
python cbor2-fuzz.py
```

> **Important:** When running locally (not in Docker), you must [set `LD_PRELOAD` manually](https://github.com/google/atheris/blob/master/native_extension_fuzzing.md#option-a-sanitizerlibfuzzer-preloads).
