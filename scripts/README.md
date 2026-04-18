# Scripts

Top-level convenience scripts for local development. The canonical way to run the pipeline is via AWS Step Functions (see `pipeline/README.md` and `infra/README.md`); these scripts are for local setup and laptop-scale runs.

## Scripts

### `setup_environment.sh`

Sets up the Python virtual environment and installs all dependencies.

```bash
./scripts/setup_environment.sh
```

### `run_full_pipeline.sh`

Runs the automated phases of the pipeline (1–3, 5–7) against local data, pausing at Phase 4 for manual refinement in 3D Slicer. Useful for laptop-scale development runs without needing AWS.

```bash
./scripts/run_full_pipeline.sh [--data-dir ./data]
```

For production-scale runs, use the Step Functions state machine deployed by `infra/` instead — it's idempotent (skip-if-done per phase), parallelises where possible, and produces a `manifest.json` for Phase 1.
