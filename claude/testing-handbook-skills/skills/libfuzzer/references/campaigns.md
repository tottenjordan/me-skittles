# Campaigns

## Running Campaigns

### Basic Run

```bash
./fuzz corpus/
```

This runs until a crash is found or you stop it (Ctrl+C).

### Recommended: Continue After Crashes

```bash
./fuzz -fork=1 -ignore_crashes=1 corpus/
```

The `-fork` and `-ignore_crashes` flags (experimental but widely used) allow fuzzing to continue after finding crashes.

### Common Options

**Control input size:**
```bash
./fuzz -max_len=4000 corpus/
```
Rule of thumb: 2x the size of minimal realistic input.

**Set timeout:**
```bash
./fuzz -timeout=2 corpus/
```
Abort test cases that run longer than 2 seconds.

**Use a dictionary:**
```bash
./fuzz -dict=./format.dict corpus/
```

**Close stdout/stderr (speed up fuzzing):**
```bash
./fuzz -close_fd_mask=3 corpus/
```

**See all options:**
```bash
./fuzz -help=1
```

### Multi-Core Fuzzing

**Option 1: Jobs and workers (recommended):**
```bash
./fuzz -jobs=4 -workers=4 -fork=1 -ignore_crashes=1 corpus/
```
- `-jobs=4`: Run 4 sequential campaigns
- `-workers=4`: Process jobs in parallel with 4 processes
- Test cases are shared between jobs

**Option 2: Fork mode:**
```bash
./fuzz -fork=4 -ignore_crashes=1 corpus/
```

**Note:** For serious multi-core fuzzing, consider switching to AFL++, Honggfuzz, or LibAFL.

### Re-executing Test Cases

**Re-run a single crash:**
```bash
./fuzz ./crash-a9993e364706816aba3e25717850c26c9cd0d89d
```

**Test all inputs in a directory without fuzzing:**
```bash
./fuzz -runs=0 corpus/
```

### Interpreting Output

When fuzzing runs, you'll see statistics like:

```
INFO: Seed: 3517090860
INFO: Loaded 1 modules (9 inline 8-bit counters)
#2      INITED cov: 3 ft: 4 corp: 1/1b exec/s: 0 rss: 26Mb
#57     NEW    cov: 4 ft: 5 corp: 2/4b lim: 4 exec/s: 0 rss: 26Mb
```

| Output | Meaning |
|--------|---------|
| `INITED` | Fuzzing initialized |
| `NEW` | New coverage found, added to corpus |
| `REDUCE` | Input minimized while keeping coverage |
| `cov: N` | Number of coverage edges hit |
| `corp: X/Yb` | Corpus size: X entries, Y total bytes |
| `exec/s: N` | Executions per second |
| `rss: NMb` | Resident memory usage |

**On crash:**
```
==11672== ERROR: libFuzzer: deadly signal
artifact_prefix='./'; Test unit written to ./crash-a9993e364706816aba3e25717850c26c9cd0d89d
0x61,0x62,0x63,
abc
Base64: YWJj
```

The crash is saved to `./crash-<hash>` with the input shown in hex, UTF-8, and Base64.

**Reproducibility:** Use `-seed=<value>` to reproduce a fuzzing campaign (single-core only).


## Corpus Management

### Creating Initial Corpus

Create a directory for the corpus (can start empty):

```bash
mkdir corpus/
```

**Optional but recommended:** Provide seed inputs (valid example files):

```bash
# For a PNG parser:
cp examples/*.png corpus/

# For a protocol parser:
cp test_packets/*.bin corpus/
```

**Benefits of seed inputs:**
- Fuzzer doesn't start from scratch
- Reaches valid code paths faster
- Significantly improves effectiveness

### Corpus Structure

The corpus directory contains:
- Input files that trigger unique code paths
- Minimized versions (libFuzzer automatically minimizes)
- Named by content hash (e.g., `a9993e364706816aba3e25717850c26c9cd0d89d`)

### Corpus Minimization

libFuzzer automatically minimizes corpus entries during fuzzing. To explicitly minimize:

```bash
mkdir minimized_corpus/
./fuzz -merge=1 minimized_corpus/ corpus/
```

This creates a deduplicated, minimized corpus in `minimized_corpus/`.

> **See Also:** For corpus creation strategies, seed selection, format-specific corpus building,
> and corpus maintenance, see the **fuzzing-corpus** technique skill.


## Fuzzing Dictionary

Dictionaries help the fuzzer discover interesting inputs faster by providing hints about the input format.

### Dictionary Format

Create a text file with quoted strings (one per line):

```conf
# Lines starting with '#' are comments

# Magic bytes
magic="\x89PNG"
magic2="IEND"

# Keywords
"GET"
"POST"
"Content-Type"

# Hex sequences
delimiter="\xFF\xD8\xFF"
```

### Using a Dictionary

```bash
./fuzz -dict=./format.dict corpus/
```

### Generating a Dictionary

**From header files:**
```bash
grep -o '".*"' header.h > header.dict
```

**From man pages:**
```bash
man curl | grep -oP '^\s*(--|-)\K\S+' | sed 's/[,.]$//' | sed 's/^/"&/; s/$/&"/' | sort -u > man.dict
```

**From binary strings:**
```bash
strings ./binary | sed 's/^/"&/; s/$/&"/' > strings.dict
```

**Using LLMs:** Ask ChatGPT or similar to generate a dictionary for your format (e.g., "Generate a libFuzzer dictionary for a JSON parser").

> **See Also:** For advanced dictionary generation, format-specific dictionaries, and
> dictionary optimization strategies, see the **fuzzing-dictionaries** technique skill.
