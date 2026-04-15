# Protocol: Generation of Bio-Realistic Arachnoid Trabeculae and Microstructures for Spinal SAS Mesh Augmentation

**Target Application:** Lattice Boltzmann Method (LBM) fluid flow simulation of CSF in the spinal subarachnoid space  
**Version:** 1.2 — April 2026  
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
| Trabecular fiber diameter | 5–50 μm (mean ~30 μm) | Killer et al. 2003 (optic nerve: 5–7 μm); Benko et al. 2020 (cranial: ~30 μm mean) | Spinal trabeculae are likely thicker on average than optic nerve values |
| Volume fraction (VF) of trabeculae | 19–35% | Benko et al. 2020 (cranial: mean 22.0–29.2%, with VF +12% near superior brain, +5–10% in frontal lobes); Rossinelli et al. 2023 (optic nerve: ~35%) | VF is region-dependent; dorsal spinal SAS likely higher than ventral; substantial inter-subject variability even within a single anatomical region |
| Porosity (ε = 1 − VF_solid) | 0.65–0.95 | Derived from VF data; Gupta et al. 2010 estimate ~0.99 for open SAS | Range spans from dense trabecular mesh to nearly open regions |
| Inter-trabecular spacing | 50–500 μm | Estimated from SEM images (Saboori 2015; Killer et al. 2003) | Highly variable; smaller in dorsal, larger in ventral compartment |
| Branching angle | 20°–70° | Estimated from SEM micrographs of branching trabeculae | No systematic quantitative study exists for spinal AT |
| Branching ratio (daughters per node) | 1–3 (predominantly bifurcation) | Inferred from SEM imagery of tree-like architectures (Saboori 2021) | |
| Septal perforation diameter | 10–50 μm | Killer et al. 2003 (optic nerve septa) | Assumed similar for spinal septa |
| Septal thickness | 2–10 μm | Estimated from TEM cross-sections | |
| Pillar diameter | 30–100 μm | Killer et al. 2003; SEM morphometry | |
| Surface area amplification factor | 3.2–4.9× | Rossinelli et al. 2023 (optic nerve) | Critical for mass transfer modeling; Rossinelli et al. 2024 showed ONSAS without microstructure has 3× smaller surface area and 17× decreased mass transfer rate |
| Trabecular thickness (peak PDF) | 40–60 μm diameter | Rossinelli et al. 2023 (Dataset1, model-independent 3D thickness via maximum inscribed ball) | No structures larger than 200 µm; provides a quantitative reference PDF for validation |
| Spinal SAS annular gap (pia-to-arachnoid) | 2–6 mm | MRI-based measurements (varies with spinal level) | Widest at lumbar cistern; narrows at cervical levels |

### 1.3 Regional Heterogeneity in the Spinal SAS

The distribution of microstructures along the spinal column is non-uniform, which must be accounted for in any generation algorithm. The following regional model is adopted:

**Dorsal compartment:** Dense trabecular network, predominantly branched strands and tree-like forms, higher volume fraction (~25–35%), smaller inter-trabecular spacing (50–200 μm). The posterior SAS has been shown to have denser packing, which biases CSF flow toward the anterior compartment as observed in 4D phase-contrast MRI.

**Ventral compartment:** Sparser trabeculae, predominantly single strands and some sheets, lower volume fraction (~10–20%), larger spacing (200–500 μm). Blood vessels (especially the anterior spinal artery) are ensheathed by trabeculae in this region.

**Lateral compartments:** Intermediate density, with nerve root sleeves acting as additional flow obstacles. Denticulate ligaments are the dominant macrostructure here but are typically resolvable from MRI.

**Craniocaudal gradient:** Thoracic is intermediate; lumbar cistern (below conus medullaris, ~L1–S2) is wider with sparser trabeculae and predominantly single-strand architectures. The cervical region requires special consideration — see below.

> [!WARNING]
> **Cervical Region Trabecular Sparsity**
> Recent evidence suggests that trabeculae in the cervical spinal SAS are sparser than previously assumed from cranial extrapolation. Sánchez et al. (2025) explicitly excluded trabeculae from their cervical-region reduced-order drug dispersion model, noting their "sparse distribution in the cervical region," while retaining nerve rootlets and denticulate ligaments as the dominant microanatomical features. This is consistent with observations from Stockman's LBM studies. The implication is that in the cervical region, **nerve roots and denticulate ligaments — not trabeculae — may dominate flow resistance and mixing effects**. The cervical VF ranges in Appendix B have been revised downward accordingly (upper cervical: 0.10–0.20; lower cervical: 0.08–0.18). These structures are macroscopic and should ideally be captured by the MRI-derived geometry input (Section 4.1), meaning the microstructure generation pipeline's cervical trabecular density should be set lower than cranial values. For complete cervical simulations, the generated trabecular microstructure should be combined with MRI-resolved nerve root and denticulate ligament geometry — a natural follow-up to the current scope.

---

## 2. Algorithm Selection

### 2.1 Candidates Considered

Five algorithmic families were evaluated for procedural generation of trabecular microstructure within an annular SAS volume:

**Candidate A — L-Systems (Lindenmayer Systems).** Grammar-based rewriting systems that generate branching structures through iterative symbol substitution. Strengths: well-understood, deterministic for a given grammar, excellent for self-similar branching patterns. Weaknesses: inherently context-free (branches are unaware of spatial environment without extensions), tend toward symmetric structures, difficult to constrain within arbitrary 3D volumes, and poor at producing the spatially-aware, volume-filling behavior seen in biological trabeculae.

**Candidate B — Space Colonization Algorithm (SCA).** Attraction-point-based growth algorithm (Runions et al. 2007) where branch segments iteratively grow toward distributed attractor points within a bounding volume, consuming attractors as they are reached. Strengths: naturally volume-filling, branches avoid each other via attractor consumption, inherently environment-aware, produces organic non-self-similar branching, well-suited to arbitrary 3D bounding volumes, and has an existing implementation that outputs binary 3D matrices for LBM input. Weaknesses: more computationally expensive than L-systems, less control over exact branching statistics, requires tuning of kill distance, influence distance, and segment length.

**Candidate C — Constrained Constructive Optimization (CCO).** Originally developed for vascular tree generation (Frisbee et al.), this iterative framework adds terminal segments one at a time to minimize a global cost function (typically total volume or power dissipation). Strengths: biophysically motivated, produces physiologically realistic branching networks. Weaknesses: designed for perfusion trees with a single root, not well-suited to multi-anchored meshwork topologies where trabeculae connect two surfaces; very computationally expensive for dense networks.

**Candidate D — Voronoi/CVT-based Scaffold with Randomized Perturbation.** Generate a Voronoi tessellation of the SAS volume, extract edges as a scaffold, randomly prune and perturb to achieve target volume fraction. Strengths: computationally fast, easy to control density and isotropy, uniform spacing control. Weaknesses: produces overly regular, crystalline-looking structures that do not resemble the organic, anisotropic morphology seen in SEM images; poor representation of the five identified AT architectures.

**Candidate E — Stochastic Cylinder Placement.** The approach used by Tangen et al. (2015) and further developed by Ayansiji/Linninger et al. (2023), where microscopic trabeculae below the image detection threshold are added artificially as randomly placed cylinders within the SAS. Tangen et al. found a 2–2.5-fold increase in pressure drop due to the added trabeculae. Strengths: computationally simple, conceptually straightforward, demonstrates the importance of including microstructure. Weaknesses: random cylinder distributions lack **morphological realism** (no branching, no five-class architectural diversity), cannot reproduce **anisotropic permeability** (the randomly oriented cylinders produce isotropic resistance tensors), and do not capture the **architecture-class diversity** observed in SEM studies. Furthermore, the Linninger group's finding that oscillatory CSF flow around microanatomical features creates geometry-induced mixing patterns with eddies and vortices suggests that realistic branching morphology — which random cylinders underestimate — is important for accurate mass transport prediction. SCA-based generation with biologically motivated density fields addresses all of these shortcomings.

### 2.2 Selected Algorithm: Hybrid Space Colonization with Multi-Type Seeding

**Primary recommendation: Space Colonization Algorithm (SCA)** with the following extensions:

The SCA is the strongest fit for this application because (a) trabecular growth during embryogenesis literally occurs by a space-colonization-like process — the trabecular structure arises from withdrawal of GAG gel, resulting in fluid-filled cavities with random spacing and size, with the mesenchymal material between these cavities forming the trabeculae; (b) the algorithm naturally fills arbitrary 3D volumes (the annular SAS geometry) without requiring explicit parametrization of the volume shape; (c) branches naturally avoid each other and produce non-self-intersecting networks; (d) a published implementation already exists that outputs binary 3D matrices compatible with LBM voxel grids; (e) the algorithm's parameters (segment length, kill distance, influence radius, attractor density) map intuitively to biological observables (trabecular diameter, inter-trabecular spacing, branching density); and (f) independent biomedical validation of SCA for biological network generation is provided by Kreitner et al. (2024), who used a space colonization approach for realistic retinal vascular network synthesis in OCTA imaging, confirming the algorithm's suitability for generating biologically realistic branching networks beyond botanical applications.

The hybrid extension adds a second pass for generating sheet-like septa and veil-like adhesions, which the base SCA (designed for 1D branching) cannot produce directly.

### 2.3 Why Not the Others?

L-systems were rejected primarily because the arachnoid trabeculae are not self-similar recursive structures — they are spatially heterogeneous, environment-responsive networks. While stochastic L-systems can approximate this, the parameter tuning required to achieve volume-aware, non-self-intersecting growth within an annular geometry effectively re-implements what SCA does natively.

CCO was rejected because it assumes a perfusion tree topology (single inlet branching to multiple terminals) whereas trabeculae form a meshwork anchored on two surfaces (pia and arachnoid) with many-to-many connectivity.

Voronoi scaffolds were rejected because they produce visually unrealistic, overly regular structures. However, the Voronoi approach is retained as a fallback for the sheet/septa generation sub-step (see Section 4.4), where the regularity of Voronoi cells is actually closer to the quasi-periodic spacing observed in septal partitions.

Stochastic cylinder placement (Candidate E) was rejected because, while it demonstrates the functional importance of including microstructure (Tangen et al. 2015 showed 2–2.5× pressure drop increase), the method fundamentally cannot reproduce the morphological richness required for accurate mass transport predictions. The geometry-induced mixing from realistic branching morphology (Ayansiji/Linninger et al. 2023) is a key functional property that random cylinders underestimate.

---

## 3. Assumptions

### 3.1 Morphometric Extrapolation Assumption

**ASSUMPTION A1:** Quantitative morphometric data from the cranial SAS and optic nerve SAS (which have been studied extensively via SEM, TEM, and SRμCT) are applicable to the spinal SAS with noted corrections for the known dorsal-ventral and craniocaudal gradients. This is the single largest source of uncertainty in the protocol. The spinal SAS has been studied qualitatively (Parkinson 1991; Nicholas & Weller 1988; Reina et al. 2015) but lacks the systematic volumetric quantification available for the optic nerve (Rossinelli et al. 2023) or cranial SAS (Benko et al. 2020). Benko et al. found substantial inter-subject variability even within a single anatomical region (average VF 22.0–29.2% across brains), reinforcing why the LHS sweep range of VF_target = 0.05–0.35 must be wide. The parameter sweep in Section 5 is designed to bracket this uncertainty. Note that cervical-region trabecular density may be substantially lower than cranial density (see §1.3 caveat on Sánchez et al. 2025).

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

For each parameter combination, run the LBM simulation and compute the following metrics. Metrics V1–V5 are hydrodynamic; V6 is morphological (quantitative); V7 addresses mass transfer; V8 captures scaling behavior across the LHS sweep; V9 provides advanced structural characterization.

**Metric V1 — Full Permeability Tensor (κ_ij).** Extract the complete 3×3 symmetric permeability tensor by applying pressure gradients along each of the 3 coordinate axes independently. For each applied gradient direction, measure the resulting volume-averaged velocity vector. The system ⟨u_i⟩ = −(1/μ) κ_ij ∂P/∂x_j yields the 6 independent tensor components. This approach was validated by Gao et al. (2011, Transport in Porous Media) for anisotropic permeability of real porous media using X-ray CT data. Gupta & Kurtcuoglu (2010) were the first to use anisotropic permeability in CSF modeling but *guessed* the tensor components rather than computing them from microstructure — our approach derives κ_ij from first principles via pore-resolved LBM. **Requires 3 LBM runs per RVE.** The target range for the dominant eigenvalue is **κ = 10⁻⁹ to 10⁻⁷ m²**, based on Gupta et al. (2010) and Jacobson et al. (1996). The physically realistic range for the spinal SAS with trabeculae is estimated at **κ ~ 10⁻⁸ m²** (order of magnitude). The full tensor is the input for the Level 2 Brinkman simulation (§6.3).

**Metric V2 — Permeability Anisotropy Ratio (κ_axial / κ_transverse).** The trabecular microstructure should produce anisotropic permeability. Based on the longitudinal orientation of many trabeculae and the dorsal-ventral density gradient, expect κ_axial/κ_transverse ∈ [1.5, 5.0]. This matches the anisotropic porous media model used by Gupta et al. (2010).

**Metric V3 — Anterior-Posterior Flow Ratio.** 4D phase-contrast MRI consistently shows CSF velocities dominant in the anterior (ventral) SAS. The generated microstructure, when combined with realistic boundary conditions, should reproduce this asymmetry. Target: anterior peak velocity 1.5–3× posterior peak velocity.

**Metric V4 — Realized Volume Fraction.** Compare the voxelized solid volume fraction to the target VF_target. Acceptable deviation: ±10% relative.

**Metric V5 — Pressure Drop per Unit Length.** For a physiological CSF velocity of ~0.5–5 cm/s peak, the pressure gradient should be on the order of 0.1–1.0 Pa/mm. Rossinelli et al. (2024) performed DNS at 1.625 μm/pixel resolution directly on SRμCT-derived ONSAS geometry and found that a physiological flow speed of 0.5 mm/s was achieved by imposing a hydrostatic pressure gradient of **0.37–0.67 Pa/mm** across the ONSAS structure. This remains our primary quantitative target for pressure drop validation.

**Metric V6 — Quantitative Morphology (Thickness & Separation PDFs).** This replaces the former qualitative visual morphology score with two quantitative sub-metrics computed from the voxelized binary output:

- **V6a — Trabecular Thickness PDF Match.** Compute the 3D trabecular thickness field using the model-independent method of Hildebrand & Rüegsegger (1997): for each solid voxel, the local thickness is defined as the diameter of the maximum inscribed ball centered at that voxel within the solid phase. This is computed via a 3D Euclidean distance transform of the solid phase followed by ridge detection. Compare the resulting thickness PDF against the reference distribution from Rossinelli et al. (2023, Dataset1), where most trabecular volume features a thickness of approximately **40–60 µm in diameter**, with **no structures larger than 200 µm**. Quantify the match using the Wasserstein (earth mover's) distance between the generated and reference distributions. The reference distribution can be digitized from Rossinelli 2023 Figure 6.

- **V6b — Trabecular Separation PDF Match.** Compute the equivalent metric for the pore phase (invert the binary array, apply the same inscribed-ball thickness method). Compare against published trabecular separation distributions from Rossinelli et al. (2023). The distance transform required here is the same one already needed for computing Bouzidi bounce-back q values, so this metric adds minimal computational overhead.

Additionally, qualitative assessment should verify: (a) presence of all five AT architectures, (b) absence of geometric regularity / crystalline patterns, (c) realistic density variation, (d) branch non-self-intersection.

**Metric V7 — Surface-Area-Normalized Wall Strain Rate (Mass Transfer Proxy).** Rossinelli et al. (2024) demonstrated that an ONSAS featuring no microstructure displays a threefold smaller surface area and a **17-fold decrease in mass transfer rate** compared to the fully trabeculated structure. This finding establishes that the microstructure's role in mass transfer is arguably more significant than its hydraulic role, and is directly relevant to our drug-delivery-to-microrobot use case. Compute the surface-area-normalized wall strain rate γ̇_wall = (1/A_total) × ∫_S |∂u/∂n| dS, where the integral is over all trabecular surfaces S. Validate that the generated microstructure amplifies mass transfer by the expected **5–17× relative to an empty annulus** (the range accounts for different VF configurations). This metric also provides a proxy for wall shear rate / Sherwood number scaling.

**Metric V8 — Exponential κ–VF Scaling.** Rossinelli et al. (2024) found that the relationship between pressure gradient and CSF-accessible volume is well captured by an **exponential curve**. Across the LHS sweep, fit the relationship κ(VF) to an exponential model κ = a × exp(b × VF) and verify that the generated SCA structures reproduce this exponential scaling behavior, rather than merely matching point values of permeability. This is a sweep-level validation that tests whether the ensemble of generated structures collectively exhibits the correct parametric sensitivity.

**Metric V9 — Chord Length Distributions (CLD).** As a novel characterization of the generated structures, compute chord length distributions for both the pore phase and the solid phase. Chords are computed by casting rays along the three principal axes through the binary voxel array and measuring the consecutive run lengths of pore and solid intersections. CLDs capture connectivity and clustering properties that simple volume fraction or two-point correlation functions miss — the combination of Minkowski functionals and CLDs carries sufficient information to reproduce the breakthrough curve of a conservative solute (Vogel et al. 2010). CLDs are reported as histograms and compared against the published trabecular thickness and separation PDFs from Rossinelli et al. (2023) as a cross-check (these are effectively the same information computed via inscribed-ball vs. ray-casting methods). The CLD computation module accepts an optional external reference distribution for future comparison against SRμCT data if and when such datasets become available.

**Metric V10 — Velocity Field Statistics.** From the converged steady-state LBM velocity field u(x), compute: (a) spatial variance of velocity per component: Var(u_i) = ⟨u_i²⟩ − ⟨u_i⟩²; (b) velocity PDFs (histograms) for comparison across parameter sets; (c) stagnation zone volume fraction: fraction of fluid voxels with |u| < 0.01 × ⟨|u|⟩; (d) mean, max, and min velocity magnitudes. These statistics characterize the flow environment beyond bulk permeability and serve as inputs to the dispersion proxy (V11).

**Metric V11 — Effective Dispersion Proxy.** The Taylor-Aris effective longitudinal dispersion coefficient scales as D_eff ~ ⟨u'²⟩ × L² / D_m, where u' is the velocity fluctuation, L is a characteristic mixing length, and D_m is molecular diffusion (1.5×10⁻⁹ m²/s for typical intrathecal drugs). Compute ⟨u'²⟩ directly from the steady velocity field. This gives a *relative* dispersion comparison between parameter sets without solving a transport equation. For the paper's central thesis (see §5.7), relative comparison is sufficient. For quantitative validation, a more expensive particle tracking approach (Approach B) can be employed on a subset of parameter sets: release ~10⁴ passive tracers, advect with the LBM velocity field plus Brownian diffusion, track for ~10³ oscillation cycles, and compute the mean-squared displacement growth rate → dispersion tensor. Reference: Stockman (2007) used exactly this LBM + particle tracking approach for oscillatory CSF flow with idealized trabeculae, finding dispersion enhancement of 5–10× over an open annulus. Ayansiji & Linninger (2023) showed Stockman underestimated by ~2.5× compared to in vitro phantom experiments, suggesting more realistic microstructure like ours would produce higher dispersion.

### 5.5 Recommended Sweep Configuration

A Latin Hypercube Sample of **N = 50–100 parameter combinations** over the 8 primary parameters, with each evaluated in a representative volume element (RVE) of approximately **2×2×2 mm³** (capturing ~5–40 inter-trabecular spacings) at resolution dx = 5–10 μm. This makes each LBM simulation tractable (~(200–400)³ = 8M–64M voxels) while capturing statistically representative microstructure.

For the full spinal SAS, after identifying optimal parameters from the RVE sweep, generate the microstructure on the full domain using a tiled/stitched approach with continuity enforcement at tile boundaries.

**Computational cost per RVE**: At 200³ voxels, ~10⁴ timesteps to steady state ≈ 10 seconds on H100 at 1000 MLUPS. Permeability tensor extraction requires 3 runs (one per pressure gradient direction) = ~30 seconds per RVE. A 100-sample LHS sweep ≈ 50 minutes total. Very tractable.

### 5.6 Three-Tier Validation Framework

The validation metrics are organized into three tiers following a train/validation/test paradigm to prevent overfitting and ensure genuine structural realism:

| Tier | Metrics | Role |
|------|---------|------|
| **Calibration** | κ_eff (V1), A-P flow ratio (V3), VF (V4), thickness/separation PDFs (V6a/b) | Used during LHS parameter selection — these are the "loss function" that identifies acceptable parameter sets |
| **Validation** | κ anisotropy ratio (V2), pressure drop (V5), mass transfer enhancement (V7), stagnation zone fraction (V10c), **dispersion proxy (V11)** | Computed *post-hoc*, NOT used in parameter selection — agreement demonstrates structural realism beyond calibrated quantities |
| **Independent test** | Peak cervical velocity, velocity waveform NRMSE, phase lag vs. 4D PC-MRI (Yiallourou et al. 2012) | Full-domain Brinkman simulation (§6.3 Level 2) with best parameters vs. clinical data — never touched during calibration |

The calibration tier identifies the Pareto-optimal parameter sets. The validation tier then ranks these candidates by transport-relevant metrics that were *not* part of the selection process. The independent test tier provides a completely decoupled end-to-end check using clinical imaging data at a different scale.

### 5.7 Paper Thesis and Expected Findings

The paper's central mechanistic insight — which satisfies FBCNS's requirement for "new insights into mechanisms rather than just reproducing known data" — is:

> **Thesis:** Bulk permeability is insufficient to characterize the solute transport environment of the spinal SAS. Morphologically distinct microstructures that are **hydraulically equivalent** (same κ_eff, same A-P flow ratio) produce **significantly different dispersion and mass transfer characteristics**. This means the Brinkman porous-medium approximation — the current state of the art (Gupta 2010) — systematically loses transport-relevant information by collapsing microstructure to a scalar or tensor permeability.

**Expected quantitative result:** Within the family of LHS parameter sets that satisfy the calibration criteria (κ_eff within target range, A-P ratio within target range, VF within ±10%), the effective dispersion coefficient (or its velocity-variance proxy V11) varies by **2–5×** depending on which AT architecture classes dominate. Specifically:

- **Septa-dominated microstructures** (high f_septa, fenestrated sheets) → channelized flow → **high dispersion**
- **Single-strand-dominated microstructures** (low f_septa, thin cylinders) → more uniform flow → **lower dispersion**
- Both can achieve the same κ_eff by adjusting density

**Supporting evidence:** Stockman (2007) showed 5–10× dispersion enhancement from microstructure, and Rossinelli (2024) showed that well-separated trabeculae contribute more to mass transfer than densely packed ones despite lower VF — both indicating non-trivial morphology–transport coupling.

**Key figure:** Scatter plot of κ_eff vs. dispersion proxy (V11) for all LHS samples, colored by dominant AT architecture class or by septa fraction f_septa. If the plot shows a **cloud** rather than a line, it proves the thesis — hydraulic equivalence does not imply transport equivalence.

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

### 6.3 Multi-Scale Simulation Architecture

The simulation uses a formal **two-level approach**: pore-resolved RVE simulations to extract microstructure-dependent properties (Level 1), then a Brinkman-penalized coarse simulation for full-domain validation (Level 2).

#### Level 1: Pore-Resolved RVE Simulations (the workhorse)

**Domain:** Representative Volume Elements (RVEs) of approximately 2×2×2 mm³ at dx = 5–10 μm, giving 200³–400³ = 8M–64M voxel grids.

**Method:** D3Q19 LBM with Bouzidi interpolated bounce-back (IBB) on trabecular surfaces. Steady-state Stokes flow driven by an imposed pressure gradient. This is directly within the capability of the existing MIME IBLBMFluidNode.

**Physics regime:** CSF at cardiac frequency (~1 Hz), peak velocity 2–5 cm/s. Womersley number α ≈ 0.01–0.1 at the RVE scale, so the steady-state approximation is valid for permeability extraction.

**What to extract from each RVE:**

1. **Full permeability tensor κ_ij** — 6 independent components via 3 pressure-gradient-direction LBM runs (see Metric V1).
2. **Velocity field statistics** — variance, PDFs, stagnation zones (see Metric V10).
3. **Dispersion proxy** — Taylor-Aris estimate from velocity variance (see Metric V11).
4. **Morphometric descriptors** — thickness/separation PDFs, CLDs, surface area amplification, Euler number (Metrics V6, V9).

#### Level 2: Brinkman-Penalized Coarse Simulation (independent test)

**Domain:** Full cervical spine segment (~10 cm), dx = 100–200 μm, giving ~10⁶–10⁷ voxels. Single-GPU feasible.

**Method:** D3Q19 LBM with Brinkman forcing term. At each coarse lattice node inside the SAS, apply a drag force:

```
F_i = −(μ / κ_ij(x)) × u_j
```

where κ_ij(x) is the *locally varying* permeability tensor from Level 1. The tensor varies spatially because different spinal regions have different microstructure (dorsal vs. ventral, cervical vs. thoracic).

**Key innovation over Gupta 2010:** Gupta used a single isotropic permeability for the entire SAS, estimated by fitting to experimental data. We feed in a *microstructure-derived, spatially varying, anisotropic* permeability field. This is the multi-scale bridge: pore-resolved physics → macroscopic model.

**Implementation:** The Brinkman forcing requires a `BrinkmanFluidNode` in the MIME framework — an LBM node with anisotropic drag forcing that modifies the collision step. Implementation references: Seta (2009) for the forcing scheme (derived the Brinkman equation with anisotropic κ from the LBM kinetic equation), Ginzburg (2015) for TRT stabilization that avoids spurious velocity oscillations at high permeability contrast — use TRT if permeability varies by >2 orders of magnitude across the domain.

**Boundary conditions:** Pulsatile velocity inlet from 4D PC-MRI data (Yiallourou et al. 2012 provides cervical velocity waveforms). Constant pressure outlet.

**Independent test validation targets** (from clinical MRI):
- Peak cervical velocity: 2–5 cm/s (Yiallourou et al. 2012)
- Anterior-posterior velocity ratio: 1.5–3× (consistent across multiple 4D PC-MRI studies)
- Phase lag between craniocaudal levels: ~40–60 ms per vertebral segment
- Waveform shape (NRMSE < 0.2 against published clinical data)

#### Option 3 — Locally Resolved Patches

Resolve microstructure in selected regions of interest (e.g., around a microrobot operating position) while using Brinkman drag elsewhere. Requires careful interface treatment between resolved and unresolved zones.

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

## 6.5 Morphological Sensitivity Analysis

Following the approach of Rossinelli et al. (2024), who used morphological opening and closing operations to systematically increase/decrease the ONSAS volume filled with CSF and conversely decrease/increase trabecular thickness, we recommend applying equivalent morphological dilation/erosion operations as a **sensitivity analysis tool** on SCA-generated structures. After identifying optimal parameters from the LHS sweep:

1. Apply morphological **dilation** (by 1–3 voxels) to the solid phase — effectively thickening all trabeculae and closing small pores.
2. Apply morphological **erosion** (by 1–3 voxels) — thinning trabeculae and opening the structure.
3. Re-run LBM on each perturbed geometry and measure the sensitivity of κ_eff, flow ratio, and wall strain rate.

If the generated structures show similar sensitivity profiles to the real ONSAS microstructure (from Rossinelli 2024), this constitutes a strong validation argument beyond point-wise metric matching, demonstrating that the generated microstructure responds to geometric perturbations in a physiologically consistent manner.

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
[Level 1] LBM RVE simulations (3 per sample for κ_ij tensor) → MIME IBLBMFluidNode
    ↓
Permeability tensor + velocity statistics + dispersion proxy extraction
    ↓
LHS sweep orchestration → HDF5 results dataset → Pareto-optimal parameter selection
    ↓
[Level 2] Brinkman coarse simulation (full spine, dx=100–200μm) → BrinkmanFluidNode (in MIME)
    ↓
Independent test: velocity waveforms vs. 4D PC-MRI
```

### 7.2 Software Dependencies

- **Mesh processing:** OpenUSD (for MICROBOTICA integration), trimesh, or PyVista for STL manipulation
- **Voxelization:** Custom GPU kernel (JAX) or trimesh.voxel
- **SCA implementation:** Custom Python/JAX implementation recommended; reference the GitHub repository "space-colonization-algorithm" which includes a Bresenham-based 3D voxelizer outputting binary matrices for LBM
- **LBM (Level 1):** MIME IBLBMFluidNode (D3Q19, Bouzidi bounce-back)
- **LBM (Level 2):** MIME BrinkmanFluidNode (D3Q19, TRT collision, anisotropic Brinkman forcing per Seta 2009)
- **Permeability extraction:** `PermeabilityTensorExtractor` — volume-averaged Darcy's law from 3-direction LBM runs
- **Velocity analysis:** `VelocityStatisticsAnalyzer` — variance, PDFs, stagnation zones
- **Dispersion:** `DispersionProxy` — Taylor-Aris estimate from velocity variance; optional particle tracking (Stockman 2007)
- **Sweep orchestration:** `LHSSweepOrchestrator` — LHS parameter generation, pipeline instantiation, HDF5 collection
- **Validation:** `ValidationFramework` — three-tier calibration/validation/test logic
- **Visualization:** MICROBOTICA Qt/OpenUSD pipeline for rendering and validation against SEM images

### 7.3 Cross-Validation Strategy

For reviewer confidence (FBCNS reviewers are not LBM specialists):

1. For **3–5 representative RVE configurations**, run the same geometry in both MIME and an established solver (Palabos is BSD-licensed and has Bouzidi IBB).
2. Compare permeability tensors — they should agree to within **1–2%**.
3. Report this cross-validation in a supplementary table.
4. If the cross-validation reveals discrepancies >5%, investigate before proceeding.

**Risk assessment:** The primary risk is not accuracy (Bouzidi is well-understood) but edge cases in the MIME IBLBMFluidNode implementation that haven't been stress-tested — e.g., behavior near very thin structures (1–2 voxel thick septa), boundary condition interactions at RVE periodic boundaries, or memory issues at 400³ grid sizes. Plan for debugging time.

### 7.4 Computational Cost Estimate

**Level 1 (RVE):** 2×2×2 mm³ at dx = 10 μm → 200³ = 8M voxels. D3Q19 LBM requires ~19 × 8B × 8M ≈ 1.2 GB memory per population field. With double populations (stream + collide): ~2.4 GB. Well within a single H100-SXM GPU. At 1000 MLUPs (typical for JAX-LBM on H100), reaching steady state in ~10⁴ time steps requires ~10 seconds per RVE. Permeability tensor requires 3 runs = ~30 seconds per RVE. A 100-sample LHS sweep ≈ 50 minutes total. Very tractable.

**Level 2 (Brinkman):** Full cervical spine segment (~10 cm) at dx = 100–200 μm → 10⁶–10⁷ voxels. ~80 MB memory for D3Q19. Single-GPU feasible, ~1 minute to steady state. Negligible cost relative to Level 1 sweep.

**Level 1 at max resolution:** Full cervical spine at dx = 10 μm → 10000 × 1000 × 1000 = 10B voxels → ~230 GB memory for D3Q19. Requires multi-GPU distribution (4–8 H100-SXMs via SkyPilot/RunPod). Only needed for the locally-resolved-patches approach (§6.3 Option 3).

---

## 8. Key References

- Ayansiji, A.O., Linninger, A.A., et al. (2023). Oscillatory fluid flow around microanatomical features creates geometry-induced mixing patterns in the spinal subarachnoid space. *Front Physiol*.
- Benko, M., Luke, E., Alsanea, Y., & Coats, B. (2020). Spatial distribution of human arachnoid trabeculae. *J Anatomy*, 237(2), 275–284.
- Gao, Y., et al. (2011). Lattice Boltzmann simulation of anisotropic permeabilities of fabric materials from microstructural data. *Transport in Porous Media*.
- Ginzburg, I. (2015). Consistent lattice Boltzmann schemes for the Brinkman model of porous flow and infinite Chapman-Enskog expansion. *Phys Rev E*.
- Gupta, S., et al. (2010). Three-dimensional computational modeling of subject-specific cerebrospinal fluid flow in the subarachnoid space. *J Biomech Eng*, 132, 071010.
- Hildebrand, T. & Rüegsegger, P. (1997). A new method for the model-independent assessment of thickness in three-dimensional images. *J Microsc*, 185, 67–75.
- Jacobson, E.E., et al. (1996). Fluid dynamics of the cerebral aqueduct. *Pediatr Neurosurg*, 24, 229–236.
- Killer, H.E., Laeng, H.R., Flammer, J., & Groscurth, P. (2003). Architecture of arachnoid trabeculae, pillars, and septa in the subarachnoid space of the human optic nerve. *Br J Ophthalmol*, 87, 777–781.
- Kreitner, L., et al. (2024). Lightweight simulation of the retinal vascular network based on space colonization for realistic OCTA synthesis. *IEEE Trans Med Imaging*.
- Martin, B.A., et al. (2017). Subject-specific 3D model of the spinal subarachnoid space with anatomically realistic ventral and dorsal nerve rootlets. *J Biomech*, 54, 97–106.
- Mei, R., Luo, L.-S., & Shyy, W. (2002). An accurate curved boundary treatment in the lattice Boltzmann method. *J Comput Phys*, 155, 307–330.
- Mortazavi, M.M., et al. (2018). Subarachnoid trabeculae: A comprehensive review. *World Neurosurg*, 111, 279–290.
- Nicholas, D.S. & Weller, R.O. (1988). The fine anatomy of human spinal meninges. *J Neurosurg*, 69, 276–282.
- Parkinson, D. (1991). Human spinal arachnoid septa, trabeculae, and "rogue strands." *Am J Anat*, 192, 498–509.
- Pasquesi, S.A., et al. (2021). Spatial distribution of human arachnoid trabeculae. *J Biomech Eng*.
- Reina, M.A., López, A., & De Andrés, J.A. (2015). Ultrastructure of human spinal trabecular arachnoid. In *Atlas of Functional Anatomy for Regional Anesthesia and Pain Medicine*. Springer.
- Rossinelli, D., et al. (2023). Large-scale morphometry of the subarachnoid space of the optic nerve. *Fluids and Barriers of the CNS*, 20, 23.
- Rossinelli, D., et al. (2024). Large-scale in-silico analysis of CSF dynamics within the subarachnoid space of the optic nerve. *Fluids and Barriers of the CNS*.
- Runions, A., Lane, B., & Prusinkiewicz, P. (2007). Modeling trees with a space colonization algorithm. *Eurographics Workshop on Natural Phenomena*.
- Saboori, P. (2021). Subarachnoid space trabeculae architecture. *Clinical Anatomy*, 34, 40–50.
- Sánchez, A.L., et al. (2025). Reduced-order modeling of drug dispersion in the spinal subarachnoid space. *Fluids and Barriers of the CNS*.
- Seta, T. (2009). Lattice Boltzmann method for fluid flows in anisotropic porous media with Brinkman equation. *J Fluid Sci Tech*, 4(1), 116–128.
- Stockman, H.W. (2006). Effect of anatomical fine structure on the flow of cerebrospinal fluid in the spinal subarachnoid space. *J Biomech Eng*, 128, 106–114.
- Stockman, H.W. (2007). Effect of anatomical fine structure on the dispersion of solutes in the spinal subarachnoid space. *J Biomech Eng*, 129, 666–675.
- Tangen, K.M., Hsu, Y., Zhu, D.C., & Linninger, A.A. (2015). CNS wide simulation of flow resistance and drug transport due to spinal microanatomy. *J Biomech*, 48(10), 2144–2154.
- Vogel, H.-J., et al. (2010). Comparison of a lattice-Boltzmann model, a full-morphology model, and a pore network model for determining capillary pressure–saturation relationships. *Vadose Zone J*, 4, 380–388.
- Yiallourou, T.I., et al. (2012). Comparison of 4D phase-contrast MRI flow measurements to CFD simulations of CSF motion in the cervical spine. *PLoS ONE*, 7, e52284.

---

## Appendix A: Quick-Reference Decision Matrix

| If your simulation goal is... | Then prioritize... | And set... |
|-------------------------------|--------------------|----|
| Bulk CSF flow patterns | Correct VF and dorsal-ventral ratio | Level 2 Brinkman model at coarse dx (100–200 μm) with sweep-derived κ_ij tensor |
| Local drag on a microrobot | Full microstructure resolution around the robot | Level 1 at dx = 5–10 μm in an RVE around the operating position |
| Intrathecal drug dispersion | Correct dispersion proxy (V11) + mixing enhancement | Sweep κ_axial/κ_transverse ratio; septa fraction matters; velocity variance is key |
| Validation against 4D PC-MRI | Anterior-posterior flow ratio | Level 2 Brinkman with Yiallourou 2012 inlet waveform; dorsal-ventral density ratio is the key parameter |
| SEM visual comparison | All five AT architecture types present | Use moderate tropism (w_norm ~ 0.4), high attractor density |
| Proving the paper thesis | Dispersion proxy across hydraulically equivalent sets | Compare V11 values for calibration-passing parameter sets with different f_septa |

## Appendix B: Parameter Cheat Sheet for Common Spinal Levels

| Spinal Level | SAS Gap (mm) | Suggested VF | Suggested ρ_base (pts/mm³) | Key Feature |
|--------------|-------------|-------------|---------------------------|-------------|
| C1–C3 (upper cervical) | 2–3 | 0.10–0.20 | 1000–2500 | Narrow; highest flow velocities; trabeculae sparser than cranial (Sánchez 2025); nerve roots/denticulate ligaments dominate resistance |
| C4–C7 (lower cervical) | 3–4 | 0.08–0.18 | 800–2000 | Nerve root sleeves present; trabecular density likely lower than previously assumed from cranial extrapolation |
| T1–T6 (upper thoracic) | 3–5 | 0.15–0.20 | 1000–2500 | Kyphotic curvature affects flow |
| T7–T12 (lower thoracic) | 3–5 | 0.10–0.20 | 1000–2000 | Intermediate; widening toward lumbar |
| L1–L2 (conus region) | 4–6 | 0.10–0.15 | 800–1500 | Transition zone; cauda equina begins |
| L2–S2 (lumbar cistern) | 5–8 | 0.05–0.10 | 500–1000 | Wide, sparse; cauda equina nerve bundles dominant |

> [!NOTE]
> **Cervical VF Revision (v1.1):** The cervical VF ranges have been revised downward from v1.0 values (C1–C3: 0.20–0.30 → 0.10–0.20; C4–C7: 0.15–0.25 → 0.08–0.18) based on Sánchez et al. (2025), who excluded trabeculae from cervical drug dispersion modeling due to their sparse distribution. The previous values were extrapolated from cranial AT data (Benko et al. 2020), which likely overestimates cervical spinal trabecular density. For cervical simulations, combine the reduced trabecular microstructure with MRI-resolved nerve root and denticulate ligament geometry for complete flow resistance modeling.
