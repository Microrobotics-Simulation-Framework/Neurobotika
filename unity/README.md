# Unity — CSF Microrobot Viewer

This directory will contain the Unity project for the interactive CSF system viewer.

## Setup

1. Install Unity Hub and Unity 2022.3 LTS (or newer LTS)
2. Create a new Unity project in this directory using the **3D (URP)** template
3. Import the CSF mesh GLB files from `data/meshes/final/` into `Assets/Meshes/`

## Project Structure (to be created)

```
unity/
├── Assets/
│   ├── Meshes/              # Imported CSF system meshes (LOD0-2)
│   ├── Materials/           # Interior surface materials
│   ├── Prefabs/             # Mesh prefabs with LOD groups
│   ├── Scenes/
│   │   └── CSFViewer.unity  # Main scene
│   └── Scripts/
│       ├── MicrorobotController.cs  # First-person navigation
│       ├── StructureLabels.cs       # Tooltip/label system
│       └── MinimapController.cs     # Minimap overlay
├── Packages/
├── ProjectSettings/
└── WebGLBuild/              # Build output (gitignored)
```

## Key Design Decisions

- **URP (Universal Render Pipeline)** — Required for WebGL compatibility. HDRP does not support WebGL.
- **Inverted normals** — The mesh is viewed from the inside. Either flip normals in Blender before import, or use a double-sided shader in Unity.
- **LOD Groups** — Use Unity's LOD system to swap between mesh resolutions based on camera distance.
- **Collision** — Use mesh colliders (from the LOD2 mesh for performance) to prevent the camera from passing through walls.

## Building for WebGL

1. `File > Build Settings > WebGL`
2. Player Settings:
   - Compression Format: Brotli (best size, requires server CORS/content-type config)
   - Memory Size: 512 MB minimum
   - Exception Handling: Disabled (for performance)
3. Build to `WebGLBuild/`
4. Copy output to `../web/unity/`

See [docs/unity-viewer.md](../docs/unity-viewer.md) for the full design document.
