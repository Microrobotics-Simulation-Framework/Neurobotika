# Phase 8: Microstructure Generation

This phase is dedicated to bridging the gap in clinical MRI resolutions (which fail to capture the tiny microstructures of the Subarachnoid Space like arachnoid trabeculae, septa, and veil-like adhesions). 

Using the Space Colonization Algorithm (SCA), we procedurally generate these structures based on existing volumetric distributions. This approach was selected over alternatives including stochastic cylinder placement (Tangen/Linninger et al. 2015) because SCA produces morphologically realistic, anisotropic branching networks that capture the five distinct AT architectures identified by Saboori (2021), while random cylinder distributions produce isotropic resistance tensors and lack architectural diversity.

## Multi-Scale Simulation Architecture

The simulation uses a **two-level approach**:

### Level 1: Pore-Resolved RVE Simulations
- **Domain**: 2×2×2 mm³ Representative Volume Elements at dx = 5–10 μm (200³–400³ voxels)
- **Method**: D3Q19 LBM with Bouzidi interpolated bounce-back (MIME IBLBMFluidNode)
- **Extracts**: Full permeability tensor κ_ij (3 LBM runs per RVE), velocity field statistics, Taylor-Aris dispersion proxy
- **Cost**: ~30 seconds per RVE on H100; 100-sample LHS sweep ≈ 50 minutes

### Level 2: Brinkman-Penalized Coarse Simulation
- **Domain**: Full cervical spine (~10 cm), dx = 100–200 μm, single-GPU feasible
- **Method**: D3Q19 LBM with anisotropic Brinkman forcing (Seta 2009; TRT per Ginzburg 2015)
- **Key innovation**: Feeds *microstructure-derived*, spatially varying, anisotropic κ_ij(x) tensor — replacing Gupta et al. (2010)'s guessed isotropic permeability
- **Validation**: Independent test against 4D PC-MRI clinical data (Yiallourou et al. 2012)

## Paper Thesis (§5.7)

> **Thesis**: Bulk permeability is insufficient to characterize the solute transport environment of the spinal SAS. Morphologically distinct microstructures that are *hydraulically equivalent* (same κ_eff, same A-P flow ratio) produce *significantly different dispersion and mass transfer characteristics*.

**Key figure**: Scatter plot of κ_eff vs. dispersion proxy (V11) across all LHS samples. If the plot shows a cloud rather than a line, it proves the thesis.

## Optimal Parameter Identification (LHS Sweep & Validation)

To identify the optimal scaffolding parameters within a multidimensional space (such as volume fraction and branching angles), we employ a **Latin Hypercube Sample (LHS) sweep** coupled with a **three-tier validation framework** (calibration → validation → independent test).

### Three-Tier Validation Framework

| Tier | Metrics | Role |
|------|---------|------|
| **Calibration** | κ_eff (V1), A-P flow ratio (V3), VF (V4), thickness/separation PDFs (V6a/b) | Loss function — used during parameter selection |
| **Validation** | κ anisotropy (V2), pressure drop (V5), mass transfer (V7), stagnation zones (V10), dispersion proxy (V11) | Post-hoc — NOT used in selection |
| **Independent test** | Peak cervical velocity, waveform NRMSE, phase lag vs. 4D PC-MRI | Level 2 Brinkman vs. clinical MRI — never touched during calibration |

### 1. Morphological Ground Truth Calibration
First, we bound the input parameters using morphological ground truth:
- **Arachnoid Trabeculae Taxonomy**: Guided by Saboori (2021) to ensure we qualitatively capture the five distinct arachnoid trabeculae architectures observed in scanning electron microscopy (SEM) studies.
- **Morphometrics**: We utilize high-resolution volume fraction and surface area amplification metrics (3.2–4.9×) derived from the optic nerve study by Rossinelli et al. (2023), with cranial AT spatial distribution data from Benko et al. (2020) — average VF 22.0–29.2%.
- **Quantitative Thickness/Separation PDFs**: Trabecular thickness and separation PDFs from Rossinelli et al. (2023) serve as quantitative validation targets (thickness peak: 40–60 µm, nothing >200 µm), computed via model-independent 3D inscribed-ball method (Hildebrand & Rüegsegger 1997) and matched using Wasserstein distance.

### 2. Hydrodynamic and Functional Benchmarking
Once Lattice Boltzmann Method (LBM) simulations are executed for each parameter set in our LHS sweep, we map the resulting flow fields to clinical observations:
- **Full Permeability Tensor**: 3×3 symmetric κ_ij extracted via 3-direction pressure gradient LBM runs (Gao et al. 2011). This is fed to the Level 2 Brinkman as a spatially varying drag tensor.
- **4D Phase-Contrast MRI**: The simulated flow is compared against clinical MRI datasets to confirm replication of the characteristic anterior-posterior flow ratio (peak ventral velocities are typically 1.5–3× higher than dorsal ones).
- **DNS Validation (Rossinelli 2024)**: Pressure gradient targets (0.37–0.67 Pa/mm for 0.5 mm/s flow) from direct numerical simulation at 1.625 µm/pixel on SRμCT-derived ONSAS geometry. We additionally verify that the LHS sweep reproduces the exponential κ–VF scaling relationship (V8).
- **Mass Transfer Amplification (V7)**: Surface-area-normalized wall strain rate validates that microstructure amplifies mass transfer by 5–17× relative to an empty annulus.
- **Velocity Statistics (V10)**: Variance, PDFs, and stagnation zone fraction characterize the flow environment beyond bulk permeability.
- **Dispersion Proxy (V11)**: Taylor-Aris estimate from velocity variance — the key metric for the paper thesis. Validated against Stockman (2007) who found 5–10× dispersion enhancement; Ayansiji & Linninger (2023) showed ~2.5× higher than Stockman's estimates in phantom experiments.

### 3. Composite Objective Function
The "best" parameter set is ultimately identified through a Pareto-optimal selection that ensures:
- The realized permeability tensor eigenvalues converge within the physiologically realistic range of $10^{-9}$ to $10^{-7} \text{ m}^2$, as established by Gupta et al. (2010).
- The morphological architectures accurately conform to the SEM taxonomic classes **and** the quantitative thickness/separation PDFs from Rossinelli et al. (2023).
- Chord length distributions (CLDs) capture connectivity and clustering properties for porous media characterization.
- The dispersion proxy (V11) is reported but **not** used in calibration — it is a validation-tier metric for thesis support.

> **Note on cervical segments:** Cervical trabecular density has been reduced from earlier estimates (VF 0.08–0.20 vs. previously 0.15–0.30) based on Sánchez et al. (2025), who found trabeculae are sparse in the cervical region where nerve roots and denticulate ligaments dominate flow resistance.

## Key Files

### Generation
- **`config.yaml`**: Central parameter file with sweep ranges, simulation configs (Level 1 + Level 2), and validation targets.
- **`generate_trabeculae_sca.py`**: Primary SCA generation algorithm with morphometric validation stubs (V6a/b thickness/separation PDFs, V9 CLDs, V7 wall strain rate, V8 κ–VF scaling, morphological sensitivity).
- **`generate_septa.py`**: Second pass generator for flat membranes / adhesions.

### CFD Analysis
- **`cfd_analysis.py`**: Post-processing stubs for LBM velocity fields — `PermeabilityTensorExtractor` (V1, 3-direction Darcy), `VelocityStatisticsAnalyzer` (V10), `DispersionProxy` (V11, Taylor-Aris + optional particle tracking).

### Orchestration & Validation
- **`lhs_sweep.py`**: `LHSSweepOrchestrator` — manages the LHS parameter sweep, runs the full SCA→LBM→metrics pipeline per sample, collects results into HDF5, identifies Pareto-optimal sets, and generates the thesis figure.
- **`validation_framework.py`**: `ValidationFramework` — implements three-tier calibration/validation/test logic with per-criterion acceptance, composite scoring, and cross-validation against reference solvers (Palabos).

For deeper biological backing, see `docs/microstructure-generation.md`.
