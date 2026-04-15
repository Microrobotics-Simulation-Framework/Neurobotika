# OpenUSD Compatibility and Export Strategy

## Overview

The Neurobotika digital twin of the cerebrospinal fluid (CSF) system involves generating immense macro-geometries (entire cerebral ventricles and spinal cord) layered with sub-MRI resolution microstructures (millions of arachnoid trabeculae strands and septa). 

Rendering, distributing, and eventually simulating within these geometries using standard file formats (OBJ, STL, FBX) results in unacceptable file sizes and performance bottlenecks.

To address this, Phase 9 leverages **OpenUSD (Universal Scene Description)** using the Pixar `pxr` core Python libraries. This enables a unified, partitioned, and highly optimized data representation.

## Key Benefits of OpenUSD for Neurobotika

1. **Instancing of Microstructures**: Trabeculae and septal sheets can be represented as PointInstances or geometric templates rather than baked geometry. An STL of a million 30μm struts could exceed gigabytes; OpenUSD can represent this via lightweight transformation matrices.
2. **Semantic Layers & Metadata**: The entire CSF system can be rigorously tagged. Sub-meshes representing the Foramen of Monro, 4th Ventricle, or Lumbar Cistern can retain semantic properties directly in the graph. 
3. **Integration**: Unlocks seamless migration to the Unity WebGL Viewer, NVIDIA Omniverse, and complex simulation frameworks (like LBM solvers).
4. **Non-Destructive Overrides**: Different simulation setups (e.g. testing SLAM microrobot navigation vs testing fluid permeability) can use USD layers (`.usda`/`.usdc`) to override properties without duplicating the base mesh.

## Export Architecture 

Upon completing the Mesh Assembly (`Phase 06`) and Microstructure Generation (`Phase 08`):

1. **Geometry Loading**: Base macro-meshes (pia/arachnoid surfaces) are converted and loaded into an initial stage.
2. **SCA Graph Parsing**: Output skeletal graphs from the Space Colonization Algorithm (nodes, radii, connection edges) are parsed.
3. **UsdGeom Integration**: The microstructures are mapped into `UsdGeom.Cylinder` objects (or custom meshes for complex septa) using Point Instancers or explicit definition depending on hierarchy needs.
4. **Export**: The stage is grouped into a `.usdz` manifest for the static WebGL viewer, and left as layered `.usda`/`.usdc` chunks for local development and physics/LBM iterations.

## Tools
We primarily rely on `pxr.Usd`, `pxr.UsdGeom`, and `pxr.Sdf` Python modules to systematically assemble the payload within the `09_openusd_export` pipeline.
