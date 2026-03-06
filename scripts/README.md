# Scripts

Top-level convenience scripts for setting up the environment and running the full pipeline.

## Scripts

### `setup_environment.sh`

Sets up the Python virtual environment and installs all dependencies.

```bash
./scripts/setup_environment.sh
```

### `run_full_pipeline.sh`

Runs the automated phases of the pipeline (1-3, 5-6), skipping Phase 4 (manual refinement).

```bash
./scripts/run_full_pipeline.sh [--data-dir ./data] [--gpu]
```

Phase 4 (manual segmentation in 3D Slicer) must be done interactively. The script will pause and prompt you to complete it before continuing with Phases 5-6.
