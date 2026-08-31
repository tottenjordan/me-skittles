# Campaigns

## Running Campaigns

### Basic Run

```bash
./afl++ <host/docker> afl-fuzz -i seeds -o out -- ./fuzz
```

### Setting Environment Variables

```bash
./afl++ <host/docker> AFL_FAST_CAL=1 afl-fuzz -i seeds -o out -- ./fuzz
```

### Interpreting Output

The AFL++ UI shows real-time fuzzing statistics:

| Output | Meaning |
|--------|---------|
| **execs/sec** | Execution speed - higher is better |
| **cycles done** | Number of queue passes completed |
| **corpus count** | Number of unique test cases in queue |
| **saved crashes** | Number of unique crashes found |
| **stability** | % of stable edges (should be near 100%) |

### Output Directory Structure

```text
out/default/
├── cmdline          # How was the SUT invoked?
├── crashes/         # Inputs that crash the SUT
│   └── id:000000,sig:06,src:000002,time:286,execs:13105,op:havoc,rep:4
├── hangs/           # Inputs that hang the SUT
├── queue/           # Test cases reproducing final fuzzer state
│   ├── id:000000,time:0,execs:0,orig:minimal_seed
│   └── id:000001,src:000000,time:0,execs:8,op:havoc,rep:6,+cov
├── fuzzer_stats     # Campaign statistics
└── plot_data        # Data for plotting
```

### Analyzing Results

View live campaign statistics:

```bash
./afl++ <host/docker> afl-whatsup out
```

Create coverage plots:

```bash
apt install gnuplot
./afl++ <host/docker> afl-plot out/default out_graph/
```

### Re-executing Test Cases

```bash
./afl++ <host/docker> ./fuzz out/default/crashes/<test_case>
```

### Fuzzer Options

| Option | Purpose |
|--------|---------|
| `-G 4000` | Maximum test input length (default: 1048576 bytes) |
| `-t 1000` | Timeout in milliseconds for each test case (default: 1000ms) |
| `-m 1000` | Memory limit in megabytes (default: 0 = unlimited) |
| `-x ./dict.dict` | Use dictionary file to guide mutations |


## Corpus Management

### Creating Initial Corpus

AFL++ requires at least one non-empty seed file:

```bash
mkdir seeds
echo "aaaa" > seeds/minimal_seed
```

For real projects, gather representative inputs:
- Download example files for the format you're fuzzing
- Extract test cases from the project's test suite
- Use minimal valid inputs for your file format

### Corpus Minimization

After a campaign, minimize the corpus to keep only unique coverage:

```bash
./afl++ <host/docker> afl-cmin -i out/default/queue -o minimized_corpus -- ./fuzz
```

> **See Also:** For corpus creation strategies, dictionaries, and seed selection,
> see the **fuzzing-corpus** technique skill.


## Multi-Core Fuzzing

AFL++ excels at multi-core fuzzing with two major advantages:
1. More executions per second (scales linearly with physical cores)
2. Asymmetrical fuzzing (e.g., one ASan job, rest without sanitizers)

### Starting a Campaign

Start the primary fuzzer (in background):

```bash
./afl++ <host/docker> afl-fuzz -M primary -i seeds -o state -- ./fuzz 1>primary.log 2>primary.error &
```

Start secondary fuzzers (as many as you have cores):

```bash
./afl++ <host/docker> afl-fuzz -S secondary01 -i seeds -o state -- ./fuzz 1>secondary01.log 2>secondary01.error &
./afl++ <host/docker> afl-fuzz -S secondary02 -i seeds -o state -- ./fuzz 1>secondary02.log 2>secondary02.error &
```

### Monitoring Multi-Core Campaigns

List all running jobs:

```bash
jobs
```

View live statistics (updates every second):

```bash
./afl++ <host/docker> watch -n1 --color afl-whatsup state/
```

### Stopping All Fuzzers

```bash
kill $(jobs -p)
```


## CMPLOG

CMPLOG/RedQueen is the best path constraint solving mechanism available in any fuzzer.
To enable it, the fuzz target needs to be instrumented for it.
Before building the fuzzing target set the environment variable:

```bash
./afl++ <host/docker> AFL_LLVM_CMPLOG=1 make
```

No special action is needed for compiling and linking the harness.

To run a fuzzer instance with a CMPLOG instrumented fuzzing target, add `-c0` to the command like arguments:

```bash
./afl++ <host/docker> afl-fuzz -c0 -S cmplog -i seeds -o state -- ./fuzz 1>secondary02.log 2>secondary02.error &
```
