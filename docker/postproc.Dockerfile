# Neurobotika Post-Processing Pipeline (Phases 5-6)
# CPU image: ANTs registration + mesh generation
#
# Build:
#   docker build -f docker/postproc.Dockerfile -t neurobotika-postproc .
#
# Run locally (registration):
#   docker run -v $(pwd)/data:/data neurobotika-postproc \
#     python /app/05/register_brain_to_mni.py --input /data/segmentations/brain/labels.nii.gz --output /data/segmentations/merged/

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    antspyx \
    nibabel \
    trimesh \
    pymeshlab \
    scikit-image \
    numpy \
    scipy \
    click

# Install AWS CLI for S3 data transfers
RUN pip install --no-cache-dir awscli

COPY pipeline/05_registration/ /app/05/
COPY pipeline/06_mesh_generation/ /app/06/

# ANTs benefits from multi-threading
ENV ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=16

WORKDIR /app
