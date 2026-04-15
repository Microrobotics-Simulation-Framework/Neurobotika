# Protocol: Generation of Bio-Realistic Arachnoid Trabeculae and Microstructures for Spinal SAS Mesh Augmentation

**Target Application:** Lattice Boltzmann Method (LBM) fluid flow simulation of CSF in the spinal subarachnoid space  
**Version:** 1.0 — March 2026  
**Context:** Augmentation of MRI-derived spinal canal STL geometry with sub-MRI-resolution microstructures

> [!WARNING]
> **GAP IN LITERATURE**
> It is extremely important to explicitly note that detailed, fully-mapped morphometry of the arachnoid trabeculae in the spinal SAS represents a massive gap in the current scientific literature. These structures are microscopic, delicate, and immensely difficult to image properly in humans. The mathematical and computational generation techniques outlined here are used as a predictive structural proxy. The ultimate goal is to use these procedurally swept microstructures as a biological stepping stone, pending high-resolution in vivo experimental structural mapping (e.g., using an OCT catheter coupled with a SLAM/GTSAM backend on an animal model) to truly ground truth these approximations.

---

## 1. Biological Basis and Morphometric Reference Data

### 1.1 Microstructure Taxonomy

The spinal subarachnoid space (SAS) contains four principal classes of microstructure that are invisible to clinical MRI but exert significant effects on local CSF hydrodynamics. These are catalogued below with their morphological characteristics as established by SEM/TEM studies (Killer et al. 2003; Saboori 2021; Mortazavi et al. 2018; Nicholas & Weller 1988; Parkinson 1991).

**Class 1 — Arachnoid Trabeculae (AT).** Collagen type-I strands coated with meningothelial cells, spanning from the arachnoid mater to the pia mater. Five dominant architectures have been identified by Saboori (2021): single strands, branched strands, tree-like shapes, sheets, and trabecular networks. In the spinal cord specifically, the dorsal compartment contains substantially denser trabecular populations than the ventral compartment (ScienceDirect; Nicholas & Weller 1988).

**Class 2 — Arachnoid Septa.** Perforated sheet-like membranes that partially subdivide the SAS into communicating chambers. These are broader than trabeculae and may contain fenestrations (pores) that allow CSF communication between adjacent compartments. In the optic nerve SAS, Killer et al. (2003) documented fenestrated septa at the mid-orbital segment with perforation diameters of approximately 10–50 μm.

**Class 3 — Arachnoid Pillars.** Stout columnar structures that bridge the SAS, typically found in regions where mechanical loading is higher. These are thicker than trabeculae (diameters up to 50–100 μm) and act as primary structural supports.

**Class 4 — Veil-like Adhesions (Cytoplasmic Extensions).** Extremely thin lamellae of flattened meningothelial cells stretched between adjacent trabeculae, forming web-like interconnections. These are the finest structures (sub-micron to a few microns in thickness) and primarily contribute to surface-area amplification rather than structural resistance.

### 1.2 Quantitative Morphometric Parameters

The following parameter values are drawn from published morphometric studies. Note the critical assumption documented in Section 3.1: spinal SAS morphometry is poorly quantified relative to cranial and optic nerve SAS, so several values below are extrapolated from cranial measurements with noted corrections.

| Parameter | Value | Source | Notes |
|-----------|-------|--------|-------|
| Trabecular fiber diameter | 5–50 μm (mean ~30 μm) | Killer et al. 2003 (optic nerve: 5–7 μm); Pasquesi et al. 2016 (cranial: ~30 μm mean) | Spinal trabeculae are likely thicker on average than optic nerve values |
| Volume fraction (VF) of trabeculae | 19–35% | Pasquesi et al. 2016 (cranial: mean 26%); Rossinelli et al. 2023 (optic nerve: ~35%) | VF is region-dependent; dorsal spinal SAS likely higher than ventral |
| Porosity (ε = 1 − VF_solid) | 0.65–0.95 | Derived from VF data; Gupta et al. 2010 estimate ~0.99 for open SAS | Range spans from dense trabecular mesh to nearly open regions |
| Inter-trabecular spacing | 50–500 μm | Estimated from SEM images (Saboori 2015; Killer et al. 2003) | Highly variable; smaller in dorsal, larger in ventral compartment |
| Branching angle | 20°–70° | Estimated from SEM micrographs of branching trabeculae | No systematic quantitative study exists for spinal AT |
| Branching ratio (daughters per node) | 1–3 (predominantly bifurcation) | Inferred from SEM imagery of tree-like architectures (Saboori 2021) | |
| Septal perforation diameter | 10–50 μm | Killer et al. 2003 (optic nerve septa) | Assumed similar for spinal septa |
| Septal thickness | 2–10 μm | Estimated from TEM cross-sections | |
| Pillar diameter | 30–100 μm | Killer et al. 2003; SEM morphometry | |
| Surface area amplification factor | 3.2–4.9× | Rossinelli et al. 2023 (optic nerve) | Critical for mass transfer modeling |
| Spinal SAS annular gap (pia-to-arachnoid) | 2–6 mm | MRI-based measurements (varies with spinal level) | Widest at lumbar cistern; narrows at cervical levels |

### 1.3 Regional Heterogeneity in the Spinal SAS

The distribution of microstructures along the spinal column is non-uniform, which must be accounted for in any generation algorithm. The following regional model is adopted:

**Dorsal compartment:** Dense trabecular network, predominantly branched strands and tree-like forms, higher volume fraction (~25–35%), smaller inter-trabecular spacing (50–200 μm). The posterior SAS has been shown to have denser packing, which biases CSF flow toward the anterior compartment as observed in 4D phase-contrast MRI.

**Ventral compartment:** Sparser trabeculae, predominantly single strands and some sheets, lower volume fraction (~10–20%), larger spacing (200–500 μm). Blood vessels (especially the anterior spinal artery) are ensheathed by trabeculae in this region.

**Lateral compartments:** Intermediate density, with nerve root sleeves acting as additional flow obstacles. Denticulate ligaments are the dominant macrostructure here but are typically resolvable from MRI.

**Craniocaudal gradient:** Cervical SAS is narrower with relatively denser microstructure; thoracic is intermediate; lumbar cistern (below conus medullaris, ~L1–S2) is wider with sparser trabeculae and predominantly single-strand architectures.

---

## 2. Algorithm Selection

### 2.1 Candidates Considered

Four algorithmic families were evaluated for procedural generation of trabecular microstructure within an annular SAS volume:

**Candidate A — L-Systems (Lindenmayer Systems).** Grammar-based rewriting systems that generate branching structures through iterative symbol substitution. Strengths: well-understood, deterministic for a given grammar, excellent for self-similar branching patterns. Weaknesses: inherently context-free (branches are unaware of spatial environment without extensions), tend toward symmetric structures, difficult to constrain within arbitrary 3D volumes, and poor at producing the spatially-aware, volume-filling behavior seen in biological trabeculae.

**Candidate B — Space Colonization Algorithm (SCA).** Attraction-point-based growth algorithm (Runions et al. 2007) where branch segments iteratively grow toward distributed attractor points within a bounding volume, consuming attractors as they are reached. Strengths: naturally volume-filling, branches avoid each other via attractor consumption, inherently environment-aware, produces organic non-self-similar branching, well-suited to arbitrary 3D bounding volumes, and has an existing implementation that outputs binary 3D matrices for LBM input. Weaknesses: more computationally expensive than L-systems, less control over exact branching statistics, requires tuning of kill distance, influence distance, and segment length.

**Candidate C — Constrained Constructive Optimization (CCO).** Originally developed for vascular tree generation (Frisbee et al.), this iterative framework adds terminal segments one at a time to minimize a global cost function (typically total volume or power dissipation). Strengths: biophysically motivated, produces physiologically realistic branching networks. Weaknesses: designed for perfusion trees with a single root, not well-suited to multi-anchored meshwork topologies where trabeculae connect two surfaces; very computationally expensive for dense networks.

**Candidate D — Voronoi/CVT-based Scaffold with Randomized Perturbation.** Generate a Voronoi tessellation of the SAS volume, extract edges as a scaffold, randomly prune and perturb to achieve target volume fraction. Strengths: computationally fast, easy to control density and isotropy, uniform spacing control. Weaknesses: produces overly regular, crystalline-looking structures that do not resemble the organic, anisotropic morphology seen in SEM images; poor representation of the five identified AT architectures.

### 2.2 Selected Algorithm: Hybrid Space Colonization with Multi-Type Seeding

**Primary recommendation: Space Colonization Algorithm (SCA)** with the following extensions:

The SCA is the strongest fit for this application because (a) trabecular growth during embryogenesis literally occurs by a space-colonization-like process — the trabecular structure arises from withdrawal of GAG gel, resulting in fluid-filled cavities with random spacing and size, with the mesenchymal material between these cavities forming the trabeculae; (b) the algorithm naturally fills arbitrary 3D volumes (the annular SAS geometry) without requiring explicit parametrization of the volume shape; (c) branches naturally avoid each other and produce non-self-intersecting networks; (d) a published implementation already exists that outputs binary 3D matrices compatible with LBM voxel grids; and (e) the algorithm's parameters (segment length, kill distance, influence radius, attractor density) map intuitively to biological observables (trabecular diameter, inter-trabecular spacing, branching density).

The hybrid extension adds a second pass for generating sheet-like septa and veil-like adhesions, which the base SCA (designed for 1D branching) cannot produce directly.

### 2.3 Why Not the Others?

L-systems were rejected primarily because the arachnoid trabeculae are not self-similar recursive structures — they are spatially heterogeneous, environment-responsive networks. While stochastic L-systems can approximate this, the parameter tuning required to achieve volume-aware, non-self-intersecting growth within an annular geometry effectively re-implements what SCA does natively.

CCO was rejected because it assumes a perfusion tree topology (single inlet branching to multiple terminals) whereas trabeculae form a meshwork anchored on two surfaces (pia and arachnoid) with many-to-many connectivity.

Voronoi scaffolds were rejected because they produce visually unrealistic, overly regular structures. However, the Voronoi approach is retained as a fallback for the sheet/septa generation sub-step (see Section 4.4), where the regularity of Voronoi cells is actually closer to the quasi-periodic spacing observed in septal partitions.

---

## 3. Assumptions

### 3.1 Morphometric Extrapolation Assumption

**ASSUMPTION A1:** Quantitative morphometric data from the cranial SAS and optic nerve SAS (which have been studied extensively via SEM, TEM, and SRμCT) are applicable to the spinal SAS with noted corrections for the known dorsal-ventral and craniocaudal gradients. This is the single largest source of uncertainty in the protocol. The spinal SAS has been studied qualitatively (Parkinson 1991; Nicholas & Weller 1988; Reina et al. 2015) but lacks the systematic volumetric quantification available for the optic nerve (Rossinelli et al. 2023) or cranial SAS (Pasquesi et al. 2016). The parameter sweep in Section 5 is designed to bracket this uncertainty.

### 3.2 Rigid-Wall Assumption

**ASSUMPTION A2:** The pia and arachnoid boundaries are treated as rigid, non-deforming surfaces for the purpose of microstructure generation and LBM simulation. This neglects cardiac-cycle-driven cord motion (which causes ~0.1–0.5 mm displacement of the spinal cord), respiratory-driven dural deformation, and the viscoelastic compliance of the meningeal membranes. This is standard practice in spinal SAS CFD (Yiallourou et al. 2012; Gupta et al. 2010) and is acceptable for steady-state or quasi-steady pulsatile simulations. For fully coupled FSI simulations, the generated microstructure can be advected with the deforming mesh in a subsequent step.

### 3.3 Newtonian Fluid Assumption

**ASSUMPTION A3:** CSF is modeled as an incompressible Newtonian fluid with density ρ = 1004 kg/m³ and dynamic viscosity μ = 0.7–1.0 × 10⁻³ Pa·s. This is well-established for CSF, which has water-like properties with slightly elevated density and viscosity due to dissolved proteins (~0.15–0.45 g/L in normal CSF). Non-Newtonian effects are negligible at physiological shear rates.

### 3.4 No-Slip Assumption on Trabecular Surfaces

**ASSUMPTION A4:** No-slip boundary conditions are applied on all trabecular surfaces in the LBM simulation. Given that trabeculae are covered by a continuous layer of meningothelial cells (demonstrated by TEM — Killer et al. 2003), the no-slip assumption is physically appropriate. The LBM implementation should use interpolated bounce-back (e.g., Bouzidi with Mei correction) for sub-grid accuracy on the curved trabecular surfaces.

### 3.5 Static Microstructure Assumption

**ASSUMPTION A5:** The generated trabecular microstructure is treated as a static obstacle field in the LBM domain. Trabeculae are compliant collagen structures in vivo, but their small diameter (~30 μm) and collagen composition suggest very small deformations under CSF pressure oscillations (~1–4 mmHg). For first-order CSF flow simulations, static treatment is justified.

### 3.6 Resolution-Coupling Assumption

**ASSUMPTION A6:** The LBM grid resolution must be fine enough to resolve the smallest generated microstructures. A minimum of 3–5 lattice nodes across a trabecular diameter is required for the bounce-back scheme to produce accurate drag (Mei et al. 2002; de Boer et al. 2025). For a 30 μm trabecular diameter, this requires dx ≤ 6–10 μm. This severely constrains the simulable domain size and will likely require either (a) local mesh refinement, (b) a multi-scale approach (resolve microstructure in a representative volume element, extract effective permeability, apply as Brinkman drag in the full domain), or (c) cloud GPU resources.

---

## 4. Microstructure Generation Pipeline

### 4.1 Input Requirements

The pipeline takes as input:

1. **Spinal SAS mesh** — An STL or volumetric representation of the spinal canal segmented from MRI, consisting of an outer surface (arachnoid/dura boundary) and an inner surface (pia/cord boundary). These should define the annular SAS volume.

2. **Spinal level labels** — Annotation of the mesh with spinal levels (C1–S2) to enable regional density variation.

3. **Dorsal/ventral orientation** — A dorsal-ventral axis definition (or normal vector field on the cord surface) to enable the dorsal-ventral density asymmetry.

4. **Target LBM resolution** — The grid spacing dx that will be used for the subsequent LBM simulation, which determines the minimum feature size of generated structures.

### 4.2 Step 1 — SAS Volume Voxelization

Voxelize the annular SAS volume at the target LBM resolution dx. For each voxel, compute:

- **Distance to pia surface** (d_pia)
- **Distance to arachnoid surface** (d_arach)
- **Local SAS gap width** (h = d_pia + d_arach)
- **Dorsal-ventral angle** (θ_dv) relative to the cord centroid at that axial level
- **Spinal level** (s, mapped from C1=1 to S2=27)

These fields will parameterize the regional variation of the generation algorithm.

### 4.3 Step 2 — Attractor Point Seeding (SCA Phase)

Distribute attractor points within the SAS volume according to a spatially varying density field. The density field ρ_att(x) controls the local trabecular density and should reflect the known regional heterogeneity:

```
ρ_att(x) = ρ_base × f_dv(θ_dv) × f_level(s) × (1 + η(x))
```

Where:

- **ρ_base** is the baseline attractor density (points per mm³), a primary sweep parameter
- **f_dv(θ_dv)** is the dorsal-ventral modulation factor:
  - f_dv = 1.0 for dorsal (θ_dv ∈ [−45°, +45°] from dorsal midline)
  - f_dv = 0.4–0.6 for ventral (θ_dv ∈ [135°, 225°])
  - Smooth sinusoidal interpolation in lateral regions
- **f_level(s)** is the craniocaudal modulation:
  - f_level = 1.0 for cervical (C1–C7)
  - f_level = 0.8 for thoracic (T1–T12)
  - f_level = 0.5 for lumbar cistern (L1–S2)
- **η(x)** is a spatially correlated noise field (Perlin noise or similar) with amplitude 0.1–0.3, providing local irregularity

**Seeding algorithm:** Poisson disk sampling with spatially varying radius r_disk(x) = ρ_att(x)^(−1/3), ensuring minimum spacing between attractors while achieving the target density.

### 4.4 Step 3 — Anchor Point Placement

Trabeculae must be anchored to the pia and arachnoid surfaces. Place anchor (seed) points on both surfaces:

**Pia surface anchors:** Sample points on the pia surface mesh with density proportional to ρ_att evaluated at the surface. These serve as SCA root nodes (growth origins).

**Arachnoid surface anchors:** Similarly sample the arachnoid surface. In the SCA framework, these can be treated as additional root nodes growing inward, or (preferably) as a termination condition — trabecular branches that reach within a kill distance of the arachnoid surface are connected to the nearest arachnoid anchor.

**Multi-root SCA variant:** Rather than growing from a single root, initialize the SCA with all pia-surface anchors as simultaneous root nodes. Each grows independently toward the attractor cloud. When a branch from one root approaches a branch from another root (within a merge distance d_merge ≈ 2–3 × segment length), they may be connected with probability p_merge ∈ [0.1, 0.4], creating the meshwork connectivity observed in SEM images.

### 4.5 Step 4 — Space Colonization Growth

Execute the SCA with the following parameters (see Section 5 for sweep ranges):

**Core SCA parameters:**

| Parameter | Symbol | Role | Nominal Value |
|-----------|--------|------|---------------|
| Segment length | D | Length of each new branch segment | 30–60 μm (≈ 1–2 trabecular diameters) |
| Kill distance | d_k | Attractor removed when node is within this distance | 60–150 μm |
| Influence radius | d_i | Maximum distance at which an attractor influences a node | 200–600 μm |
| Tropism bias | w_norm | Weight toward pia-to-arachnoid normal direction | 0.3–0.7 (0 = isotropic, 1 = purely radial) |
| Random perturbation | σ_perturb | Angular jitter added to growth direction per step | 5°–25° |
| Maximum iterations | N_iter | Growth termination | Until attractor exhaustion or convergence |

**Growth direction computation at each iteration:**

For each active node n_i with influencing attractors {a_j}, the growth direction is:

```
d_growth = normalize( w_norm × n_radial + (1 − w_norm) × d_SCA + σ_perturb × ξ )
```

Where d_SCA is the standard SCA direction (normalized average of vectors from n_i toward each influencing a_j), n_radial is the local outward normal from the pia surface, and ξ is a random unit vector providing stochastic perturbation.

The tropism bias w_norm is critical: too low produces isotropic tangles that don't bridge the SAS gap; too high produces monotonous radial pillars. A value of 0.3–0.5 produces the visually realistic mix of radial spanning and lateral branching seen in SEM images.

### 4.6 Step 5 — Radius Assignment (Murray's Law Variant)

After the SCA produces a skeletal graph, assign radii to each segment using an inverse-distance-from-tip rule inspired by Murray's law for biological branching:

```
r(node) = r_tip × (n_downstream + 1)^(1/γ)
```

Where:
- **r_tip** = 2.5–5 μm (radius of terminal trabecular fibers, based on SEM: 5–10 μm diameter range for finest structures)
- **n_downstream** = number of downstream (tip-ward) segments in the subtree
- **γ** = Murray exponent, typically 3 for vascular trees; use **γ = 2.5–3.5** as a sweep parameter, since trabeculae are not optimized for flow but for mechanical support

Cap the maximum radius at r_max = 25–50 μm (matching the observed upper bound of trabecular diameters).

### 4.7 Step 6 — Septa and Sheet Generation (Second Pass)

The SCA produces 1D branching structures (trabeculae and pillars). Septa and veil-like adhesions are generated as a second pass:

**Septa generation:**

1. Identify pairs of adjacent trabecular branches with inter-branch distance < d_septa_threshold (100–200 μm) and approximately parallel orientation (angular deviation < 30°).
2. Between qualifying pairs, generate a triangulated membrane surface by interpolating between the two branch curves.
3. Add fenestrations (perforations) to each septum: punch circular holes with diameter d_pore ~ 10–50 μm, distributed as a Poisson process with density ρ_pore (1–5 pores per 100×100 μm² area).

**Veil-like adhesion generation:**

1. Identify triplets of nearby trabecular branches with mutual distances < d_veil_threshold (50–100 μm).
2. Generate thin triangular membrane patches spanning the triangle formed by the three nearest points on the respective branches.
3. Assign membrane thickness of 1–3 μm (likely sub-grid for most LBM resolutions; treat as infinitely thin no-slip surfaces using bounce-back on the nearest voxel faces).

**Proportion control:** The relative abundance of each microstructure type should be parameterized:

| Structure Type | Target Volume Fraction Contribution | Region Bias |
|----------------|--------------------------------------|-------------|
| Single-strand trabeculae | 30–40% of total solid VF | Uniform |
| Branched/tree-like trabeculae | 30–40% | Dorsal > ventral |
| Pillars (thick trabeculae) | 5–10% | Where SAS gap is narrowest |
| Septa (perforated sheets) | 10–20% | Lateral and mid-orbital equivalents |
| Veil-like adhesions | 5–10% | Dorsal (between dense branches) |

### 4.8 Step 7 — Voxelization and LBM Integration

Convert the generated geometry (skeletal graph with radii + membrane surfaces) to the LBM voxel grid:

1. **Rasterize trabecular branches** as cylinders using 3D Bresenham line algorithm with radius dilation. Each branch segment between two nodes is rasterized as a cylinder of the assigned radius.

2. **Rasterize septa and adhesions** as thin surfaces using triangle rasterization on the voxel grid.

3. **Assign boundary conditions:** All solid voxels corresponding to microstructures receive no-slip bounce-back boundary conditions. For sub-grid accuracy on curved trabecular surfaces, use Bouzidi interpolated bounce-back with Mei correction (consistent with existing MADDENING/MIME workflow).

4. **Compute realized porosity:** After voxelization, measure the actual porosity ε_realized = (fluid voxels) / (total SAS voxels) and compare to target. Iterate attractor density ρ_base if deviation > 5%.

5. **Output:** Binary 3D array (0 = fluid, 1 = solid) or distance field for sub-grid bounce-back.

---

## 5. Parameter Sweep Design

### 5.1 Sweep Strategy

Given the high uncertainty in spinal SAS morphometry, a systematic parameter sweep is essential. The sweep is designed as a Latin Hypercube Sample (LHS) over the most influential parameters, with the objective of identifying configurations that produce (a) the correct effective permeability, (b) the correct dorsal-ventral flow asymmetry, and (c) realistic visual morphology when compared to published SEM images.

### 5.2 Primary Sweep Parameters

The following parameters have the strongest effect on LBM-computed flow properties and should be swept:

| Parameter | Symbol | Sweep Range | Nominal | Justification |
|-----------|--------|-------------|---------|---------------|
| Base attractor density | ρ_base | 500–5000 pts/mm³ | 2000 | Controls overall trabecular density; wide range to bracket unknown spinal VF |
| Kill distance | d_k | 40–200 μm | 100 μm | Controls inter-branch spacing and network connectivity |
| Influence radius | d_i | 150–800 μm | 400 μm | Controls branching reach; d_i >> d_k produces sparser, longer branches |
| Tropism bias | w_norm | 0.1–0.8 | 0.4 | Controls radial vs. lateral growth balance |
| Murray exponent | γ | 2.0–4.0 | 3.0 | Controls parent-child radius scaling |
| Dorsal-ventral ratio | f_dv(ventral) | 0.2–0.8 | 0.5 | Controls the asymmetry of trabecular density |
| Septal fraction | f_septa | 0.0–0.3 | 0.15 | Fraction of total VF contributed by septa |
| Overall target VF | VF_target | 0.05–0.35 | 0.20 | Broadest uncertainty; 0.05 = nearly empty, 0.35 = optic-nerve-like density |

### 5.3 Secondary Parameters (Fixed or Narrow Range)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Segment length D | dx to 3·dx | Tied to LBM resolution for voxel-accurate representation |
| Tip radius r_tip | 2.5–5 μm | Well-constrained by TEM measurements |
| Max radius r_max | 25–50 μm | Constrained by SEM measurements |
| Random perturbation σ_perturb | 10°–20° | Produces realistic irregularity without degeneracy |
| Merge probability p_merge | 0.1–0.4 | Controls meshwork connectivity |
| Septal pore diameter d_pore | 10–50 μm | Constrained by Killer et al. 2003 |
| Craniocaudal modulation f_level | As specified in 4.3 | Based on qualitative SEM observations |

### 5.4 Validation Metrics for Each Sweep Sample

For each parameter combination, run the LBM simulation and compute:

**Metric V1 — Effective Permeability (κ_eff).** Apply a pressure gradient along the craniocaudal axis and compute the volume-averaged velocity to extract κ_eff via Darcy's law. The target range is **κ = 10⁻⁹ to 10⁻⁷ m²**, based on the range used by Gupta et al. (2010) and Jacobson et al. (1996) who explored 8×10⁻³ to 8×10⁻¹⁰ m². The physically realistic range for the spinal SAS with trabeculae is estimated at **κ ~ 10⁻⁸ m²** (order of magnitude).

**Metric V2 — Permeability Anisotropy Ratio (κ_axial / κ_transverse).** The trabecular microstructure should produce anisotropic permeability. Based on the longitudinal orientation of many trabeculae and the dorsal-ventral density gradient, expect κ_axial/κ_transverse ∈ [1.5, 5.0]. This matches the anisotropic porous media model used by Gupta et al. (2010).

**Metric V3 — Anterior-Posterior Flow Ratio.** 4D phase-contrast MRI consistently shows CSF velocities dominant in the anterior (ventral) SAS. The generated microstructure, when combined with realistic boundary conditions, should reproduce this asymmetry. Target: anterior peak velocity 1.5–3× posterior peak velocity.

**Metric V4 — Realized Volume Fraction.** Compare the voxelized solid volume fraction to the target VF_target. Acceptable deviation: ±10% relative.

**Metric V5 — Pressure Drop per Unit Length.** For a physiological CSF velocity of ~0.5–5 cm/s peak, the pressure gradient should be on the order of 0.1–1.0 Pa/mm (Rossinelli et al. 2023 found 0.37–0.67 Pa/mm in the optic nerve SAS for 0.5 mm/s flow).

**Metric V6 — Visual Morphology Score.** Qualitative comparison of generated microstructure renderings with published SEM images. Assess: (a) presence of all five AT architectures, (b) absence of geometric regularity / crystalline patterns, (c) realistic density variation, (d) branch non-self-intersection.

### 5.5 Recommended Sweep Configuration

A Latin Hypercube Sample of **N = 50–100 parameter combinations** over the 8 primary parameters, with each evaluated in a representative volume element (RVE) of approximately **2×2×2 mm³** (capturing ~5–40 inter-trabecular spacings) at resolution dx = 5–10 μm. This makes each LBM simulation tractable (~(200–400)³ = 8M–64M voxels) while capturing statistically representative microstructure.

For the full spinal SAS, after identifying optimal parameters from the RVE sweep, generate the microstructure on the full domain using a tiled/stitched approach with continuity enforcement at tile boundaries.

---

## 6. LBM-Specific Considerations

### 6.1 Resolution Requirements

The lattice spacing dx must satisfy:

- **Trabecular resolution:** dx ≤ r_min / 2.5, where r_min is the smallest trabecular radius. For r_min = 2.5 μm (finest tip), this gives dx ≤ 1 μm — extremely expensive. Pragmatic compromise: resolve only structures with r ≥ 5 μm, giving dx ≤ 2 μm for full resolution, or dx = 5–10 μm accepting that the finest veil-like adhesions are sub-grid.

- **Mach number constraint:** Ma = u_max / c_s < 0.1 for incompressibility, where c_s = dx/(dt·√3). For u_max ~ 5 cm/s and dx = 10 μm, this gives dt ≤ dx/(u_max × √3 × 10) ≈ 1.15 × 10⁻⁵ s. With dimensional rescaling (per MADDENING workflow), this is manageable.

- **Viscosity resolution:** The relaxation parameter τ should satisfy τ ∈ [0.55, 2.0] for BGK, or use MRT/cumulant for broader stability. For ν_CSF = 7×10⁻⁷ m²/s and dx = 10 μm: τ = 0.5 + 3ν·dt/dx² — requires appropriate dt selection.

### 6.2 Bounce-Back Scheme Selection

**Recommended: Bouzidi interpolated bounce-back with Mei (2002) force correction.**

This is consistent with the existing MADDENING/MIME workflow (sub-0.5% torque error, confirmed O(dx²) convergence from prior validation). For the complex trabecular surfaces, the Bouzidi scheme's sub-grid accuracy is essential — simple bounce-back on a staircase approximation of 5–30 μm cylinders would introduce unacceptable drag errors.

### 6.3 Multi-Scale Strategy (When Full Resolution is Infeasible)

For full-spinal-canal simulations where dx = 5–10 μm is computationally prohibitive:

**Option 1 — Brinkman Porous Medium Model:** Run the microstructure generation + LBM permeability extraction on an RVE. Use the resulting permeability tensor κ_ij as input to a Brinkman-penalized LBM on the full spinal domain at coarser resolution (dx = 50–200 μm). The Brinkman term adds a drag force F_i = −(μ/κ_ij) × u_j to each lattice node in the SAS, producing the bulk effect of unresolved microstructure. This is the approach used by Gupta et al. (2010) and is currently the state of the art for subject-specific CSF simulations.

**Option 2 — Locally Resolved Patches:** Resolve microstructure in selected regions of interest (e.g., around a microrobot operating position) while using Brinkman drag elsewhere. Requires careful interface treatment between resolved and unresolved zones.

### 6.4 CSF Physical Properties for LBM

| Property | Value | Unit |
|----------|-------|------|
| Density (ρ) | 1004 | kg/m³ |
| Dynamic viscosity (μ) | 0.7–1.0 × 10⁻³ | Pa·s |
| Kinematic viscosity (ν) | 7.0–10.0 × 10⁻⁷ | m²/s |
| Peak oscillatory velocity (cervical) | 2–5 | cm/s |
| Oscillation frequency (cardiac) | 1.0–1.2 | Hz |
| Reynolds number (based on SAS gap) | 50–500 | — |
| Womersley number (α) | 10–20 | — |

---

## 7. Implementation Recommendations

### 7.1 Data Pipeline

```
MRI DICOM → Segmentation (SynthSeg/FreeSurfer) → STL (pia + arachnoid surfaces)
    ↓
STL → Voxelization at target dx → Distance fields (d_pia, d_arach)
    ↓
Distance fields + regional labels → Attractor seeding (spatially varying density)
    ↓
SCA execution (multi-root, with tropism bias) → Skeletal graph
    ↓
Radius assignment (Murray's law variant) → Thick skeleton
    ↓
Septa + adhesion second pass → Additional surfaces
    ↓
Voxelization → Binary obstacle array or distance field
    ↓
LBM domain setup (MADDENING IBLBMFluidNode) → Simulation
```

### 7.2 Software Dependencies

- **Mesh processing:** OpenUSD (for MICROBOTICA integration), trimesh, or PyVista for STL manipulation
- **Voxelization:** Custom GPU kernel (JAX) or trimesh.voxel
- **SCA implementation:** Custom Python/JAX implementation recommended; reference the GitHub repository "space-colonization-algorithm" which includes a Bresenham-based 3D voxelizer outputting binary matrices for LBM
- **LBM:** MADDENING IBLBMFluidNode (D3Q19, Bouzidi bounce-back)
- **Permeability extraction:** Post-processing of LBM velocity/pressure fields via volume-averaged Darcy's law
- **Visualization:** MICROBOTICA Qt/OpenUSD pipeline for rendering and validation against SEM images

### 7.3 Computational Cost Estimate

For an RVE of 2×2×2 mm³ at dx = 10 μm → 200³ = 8M voxels. D3Q19 LBM requires ~19 × 8B × 8M ≈ 1.2 GB memory per population field. With double populations (stream + collide): ~2.4 GB. Well within a single H100-SXM GPU. At 1000 MLUPs (typical for JAX-LBM on H100), reaching steady state in ~10⁴ time steps requires ~10 seconds per RVE. A 100-sample LHS sweep thus takes ~17 minutes — highly tractable.

For a full cervical spine segment (~10 cm length, ~1 cm SAS diameter) at dx = 10 μm → 10000 × 1000 × 1000 = 10B voxels → ~230 GB memory for D3Q19. Requires multi-GPU distribution (4–8 H100-SXMs via SkyPilot/RunPod).

---

## 8. Key References

- Killer, H.E., Laeng, H.R., Flammer, J., & Groscurth, P. (2003). Architecture of arachnoid trabeculae, pillars, and septa in the subarachnoid space of the human optic nerve. *Br J Ophthalmol*, 87, 777–781.
- Saboori, P. (2021). Subarachnoid space trabeculae architecture. *Clinical Anatomy*, 34, 40–50.
- Mortazavi, M.M., et al. (2018). Subarachnoid trabeculae: A comprehensive review. *World Neurosurg*, 111, 279–290.
- Pasquesi, S.A., et al. (2021). Spatial distribution of human arachnoid trabeculae. *J Biomech Eng*.
- Rossinelli, D., et al. (2023). Large-scale morphometry of the subarachnoid space of the optic nerve. *Fluids and Barriers of the CNS*, 20, 23.
- Nicholas, D.S. & Weller, R.O. (1988). The fine anatomy of human spinal meninges. *J Neurosurg*, 69, 276–282.
- Parkinson, D. (1991). Human spinal arachnoid septa, trabeculae, and "rogue strands." *Am J Anat*, 192, 498–509.
- Reina, M.A., López, A., & De Andrés, J.A. (2015). Ultrastructure of human spinal trabecular arachnoid. In *Atlas of Functional Anatomy for Regional Anesthesia and Pain Medicine*. Springer.
- Runions, A., Lane, B., & Prusinkiewicz, P. (2007). Modeling trees with a space colonization algorithm. *Eurographics Workshop on Natural Phenomena*.
- Gupta, S., et al. (2010). Three-dimensional computational modeling of subject-specific cerebrospinal fluid flow in the subarachnoid space. *J Biomech Eng*, 132, 071010.
- Jacobson, E.E., et al. (1996). Fluid dynamics of the cerebral aqueduct. *Pediatr Neurosurg*, 24, 229–236.
- Yiallourou, T.I., et al. (2012). Comparison of 4D phase-contrast MRI flow measurements to CFD simulations of CSF motion in the cervical spine. *PLoS ONE*, 7, e52284.
- Mei, R., Luo, L.-S., & Shyy, W. (2002). An accurate curved boundary treatment in the lattice Boltzmann method. *J Comput Phys*, 155, 307–330.

---

## Appendix A: Quick-Reference Decision Matrix

| If your simulation goal is... | Then prioritize... | And set... |
|-------------------------------|--------------------|----|
| Bulk CSF flow patterns | Correct VF and dorsal-ventral ratio | Brinkman model at coarse dx (50–200 μm) with sweep-derived κ |
| Local drag on a microrobot | Full microstructure resolution around the robot | dx = 5–10 μm in an RVE around the operating position |
| Intrathecal drug dispersion | Correct permeability anisotropy + mixing enhancement | Sweep κ_axial/κ_transverse ratio; septa fraction matters |
| Validation against 4D PC-MRI | Anterior-posterior flow ratio | Dorsal-ventral density ratio is the key parameter |
| SEM visual comparison | All five AT architecture types present | Use moderate tropism (w_norm ~ 0.4), high attractor density |

## Appendix B: Parameter Cheat Sheet for Common Spinal Levels

| Spinal Level | SAS Gap (mm) | Suggested VF | Suggested ρ_base (pts/mm³) | Key Feature |
|--------------|-------------|-------------|---------------------------|-------------|
| C1–C3 (upper cervical) | 2–3 | 0.20–0.30 | 2000–4000 | Dense, narrow; highest flow velocities |
| C4–C7 (lower cervical) | 3–4 | 0.15–0.25 | 1500–3000 | Moderate density; nerve root sleeves present |
| T1–T6 (upper thoracic) | 3–5 | 0.15–0.20 | 1000–2500 | Kyphotic curvature affects flow |
| T7–T12 (lower thoracic) | 3–5 | 0.10–0.20 | 1000–2000 | Intermediate; widening toward lumbar |
| L1–L2 (conus region) | 4–6 | 0.10–0.15 | 800–1500 | Transition zone; cauda equina begins |
| L2–S2 (lumbar cistern) | 5–8 | 0.05–0.10 | 500–1000 | Wide, sparse; cauda equina nerve bundles dominant |
