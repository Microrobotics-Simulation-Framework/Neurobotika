# Unity Microrobot CSF Viewer

A WebGL-based interactive viewer that lets users navigate the CSF system mesh as if they were a microrobot.

## Concept

The viewer places a camera (the "microrobot") inside the CSF mesh. The user can fly through the ventricular system, squeeze through the cerebral aqueduct, exit through the foramina, and travel the subarachnoid space down the spinal canal. The mesh surfaces are rendered from the inside, with lighting and scale cues to convey the anatomy.

## Unity Project Setup

- **Version:** Unity 2022.3 LTS (or newer LTS)
- **Render pipeline:** Universal Render Pipeline (URP) for WebGL compatibility
- **Target platform:** WebGL (primary), with standalone builds for development

The Unity project lives in `unity/`. It is a standard Unity project — open it with Unity Hub.

## Mesh Import

The pipeline exports meshes in `.glb` format (Phase 6, `export_unity.py`). These are imported into Unity as prefabs.

### LOD Strategy

The full CSF mesh may have millions of triangles. For smooth WebGL performance:

| LOD Level | Triangle Count | Use |
|-----------|---------------|-----|
| LOD0 | Full resolution | Close-up (inside ventricles, foramina) |
| LOD1 | ~50% decimation | Medium distance |
| LOD2 | ~10% decimation | Far overview / minimap |

The `export_unity.py` script generates all three LOD levels. In Unity, these are configured as LOD Groups on the mesh GameObjects.

## Viewer Features

### Core (MVP)
- First-person camera inside the mesh (microrobot POV)
- WASD + mouse movement (or touch controls on mobile)
- Collision detection against mesh walls
- Labels/tooltips when approaching named structures (e.g., "Cerebral Aqueduct", "Foramen of Monro")
- Minimap showing current position in the full CSF system

### Future
- Scale reference (overlay showing real-world dimensions)
- Guided tour mode (automated camera path through the CSF system)
- Cross-section view toggle
- VR support (WebXR)

## WebGL Build

Build the Unity project for WebGL:
1. `File > Build Settings > WebGL`
2. Set compression to Brotli
3. Build to `unity/WebGLBuild/`

The output is a set of static files:
```
WebGLBuild/
├── Build/
│   ├── WebGLBuild.data.br
│   ├── WebGLBuild.framework.js.br
│   ├── WebGLBuild.loader.js
│   └── WebGLBuild.wasm.br
├── TemplateData/
│   ├── style.css
│   └── favicon.ico
├── StreamingAssets/          (mesh files loaded at runtime, if not baked in)
└── index.html
```

## Deployment

The WebGL build is wrapped by the static site in `web/` and deployed to S3 + CloudFront. See [deployment.md](deployment.md).

The `web/index.html` page loads the Unity player in an iframe or directly embeds it with appropriate loading UI.

## Development Workflow

1. Export meshes from pipeline Phase 6
2. Import `.glb` files into `unity/Assets/Meshes/`
3. Develop in Unity Editor with standalone build for fast iteration
4. Build WebGL when ready to deploy
5. Copy WebGL output to `web/unity/`
6. Deploy with `cd infra && terraform apply`
