# Web — Static Site

A minimal static website that wraps the Unity WebGL build and hosts the CSF microrobot viewer.

## Structure

```
web/
├── index.html           # Landing page with Unity WebGL embed
├── css/
│   └── style.css        # Minimal styling
└── unity/               # Unity WebGL build output (copied from unity/WebGLBuild/)
    ├── Build/
    ├── TemplateData/
    └── StreamingAssets/
```

## Deployment

The contents of `web/` are synced to the `neurobotika-web` S3 bucket and served via CloudFront.

```bash
# Sync web content
aws s3 sync web/ s3://neurobotika-web/ --delete

# Sync Unity build (with correct content-types for Brotli)
aws s3 sync web/unity/Build/ s3://neurobotika-web/unity/Build/ \
    --content-encoding br \
    --exclude "*" --include "*.br"
```

See [docs/deployment.md](../docs/deployment.md) for full deployment instructions including required content-type headers for Unity WebGL with Brotli compression.

## Local Development

To test locally, serve the `web/` directory with any static file server:

```bash
python -m http.server 8000 --directory web/
```

Note: Unity WebGL with Brotli compression requires proper content-type headers. For local testing, use the uncompressed build or a server that supports Brotli (e.g., `npx serve web/`).
