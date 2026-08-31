# Custom Fuzzers

## Usage Modes

LibAFL supports two primary usage modes:

### 1. libFuzzer Drop-in Replacement

Use LibAFL as a replacement for libFuzzer with existing harnesses.

**Compilation:**
```bash
clang++ -DNO_MAIN -g -O2 -fsanitize=fuzzer-no-link libFuzzer.a harness.cc main.cc -o fuzz
```

**Running:**
```bash
./fuzz corpus/
```

**Recommended for long campaigns:**
```bash
./fuzz -fork=1 -ignore_crashes=1 corpus/
```

### 2. Custom Fuzzer as Rust Library

Build a fully customized fuzzer using LibAFL components.

**Create project:**
```bash
cargo init --lib my_fuzzer
cd my_fuzzer
cargo add libafl@0.13 libafl_targets@0.13 libafl_bolts@0.13 libafl_cc@0.13 \
  --features "libafl_targets@0.13/libfuzzer,libafl_targets@0.13/sancov_pcguard_hitcounts"
```

**Configure Cargo.toml:**
```toml
[lib]
crate-type = ["staticlib"]
```


## Writing a Custom Fuzzer

> **See Also:** For detailed harness writing techniques, patterns for handling complex inputs,
> and advanced strategies, see the **fuzz-harness-writing** technique skill.

### Fuzzer Components

A LibAFL fuzzer consists of modular components:

1. **Observers** - Collect execution feedback (coverage, timing)
2. **Feedback** - Determine if inputs are interesting
3. **Objective** - Define fuzzing goals (crashes, timeouts)
4. **State** - Maintain corpus and metadata
5. **Mutators** - Generate new inputs
6. **Scheduler** - Select which inputs to mutate
7. **Executor** - Run the target with inputs

### Basic Fuzzer Structure

```rust
use libafl::prelude::*;
use libafl_bolts::prelude::*;
use libafl_targets::{libfuzzer_test_one_input, std_edges_map_observer};

#[no_mangle]
pub extern "C" fn libafl_main() {
    let mut run_client = |state: Option<_>, mut restarting_mgr, _core_id| {
        // 1. Setup observers
        let edges_observer = HitcountsMapObserver::new(
            unsafe { std_edges_map_observer("edges") }
        ).track_indices();
        let time_observer = TimeObserver::new("time");

        // 2. Define feedback
        let mut feedback = feedback_or!(
            MaxMapFeedback::new(&edges_observer),
            TimeFeedback::new(&time_observer)
        );

        // 3. Define objective
        let mut objective = feedback_or_fast!(
            CrashFeedback::new(),
            TimeoutFeedback::new()
        );

        // 4. Create or restore state
        let mut state = state.unwrap_or_else(|| {
            StdState::new(
                StdRand::new(),
                InMemoryCorpus::new(),
                OnDiskCorpus::new(&output_dir).unwrap(),
                &mut feedback,
                &mut objective,
            ).unwrap()
        });

        // 5. Setup mutator
        let mutator = StdScheduledMutator::new(havoc_mutations());
        let mut stages = tuple_list!(StdMutationalStage::new(mutator));

        // 6. Setup scheduler
        let scheduler = IndexesLenTimeMinimizerScheduler::new(
            &edges_observer,
            QueueScheduler::new()
        );

        // 7. Create fuzzer
        let mut fuzzer = StdFuzzer::new(scheduler, feedback, objective);

        // 8. Define harness
        let mut harness = |input: &BytesInput| {
            let buf = input.target_bytes().as_slice();
            libfuzzer_test_one_input(buf);
            ExitKind::Ok
        };

        // 9. Setup executor
        let mut executor = InProcessExecutor::with_timeout(
            &mut harness,
            tuple_list!(edges_observer, time_observer),
            &mut fuzzer,
            &mut state,
            &mut restarting_mgr,
            timeout,
        )?;

        // 10. Load initial inputs
        if state.must_load_initial_inputs() {
            state.load_initial_inputs(
                &mut fuzzer,
                &mut executor,
                &mut restarting_mgr,
                &input_dir
            )?;
        }

        // 11. Start fuzzing
        fuzzer.fuzz_loop(&mut stages, &mut executor, &mut state, &mut restarting_mgr)?;
        Ok(())
    };

    // Launch fuzzer
    Launcher::builder()
        .run_client(&mut run_client)
        .cores(&cores)
        .build()
        .launch()
        .unwrap();
}
```
