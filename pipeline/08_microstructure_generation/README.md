# Phase 8: Microstructure Generation

This phase is dedicated to bridging the gap in clinical MRI resolutions (which fail to capture the tiny microstructures of the Subarachnoid Space like arachnoid trabeculae, septa, and veil-like adhesions). 

Using the Space Colonization Algorithm (SCA), we procedurally generate these structures based on existing volumetric distributions found in optic nerve literature.

### Key Files
- **`config.yaml`**: The central parameter file to tune densities, radii, and simulation factors. Crucial for experimental parameter sweeps.
- **`generate_trabeculae_sca.py`**: The primary algorithm step. Builds the core AT scaffold. Outputs volumetric grids and surface graphs.
- **`generate_septa.py`**: Second pass generator for flat membranes / adhesions.

For deeper biological backing, see `docs/microstructure-generation.md`.
