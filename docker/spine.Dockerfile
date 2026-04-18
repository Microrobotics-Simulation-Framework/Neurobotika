# Neurobotika Spine Segmentation (Phase 3) — TotalSpineSeg
#
# TotalSpineSeg is an nnUNetv2-based pipeline that segments vertebrae,
# intervertebral discs, spinal cord, and spinal canal from T2w MRIs.
# That gives us the two masks we need for spinal SAS: cord + canal.
#
# SCT (Spinal Cord Toolbox) is deliberately NOT installed here — its
# bundled installer is fragile in a non-interactive Docker build, and
# Phase 3's SAS computation only needs cord + canal which TotalSpineSeg
# already produces. SCT's PAM50 registration / vertebral labelling is a
# future Phase 5 enhancement.
#
# Build:
#   ./docker/build-on-codebuild.sh spine
#
# Run locally:
#   docker run --gpus all neurobotika-spine \
#     python3 /app/03/run_spineseg.py --input s3://... --output-dir s3://...

FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

# git is needed by pip for any VCS dependencies nnunetv2 / totalspineseg pull.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

# totalspineseg needs Python ≥3.10 (image has 3.11), pip ≥23, setuptools ≥67.
# Install totalspineseg with its nnunetv2 extra, plus our S3 wrapper deps.
RUN pip install --no-cache-dir --upgrade "pip>=23" "setuptools>=67" && \
    pip install --no-cache-dir \
        "totalspineseg[nnunetv2]" \
        awscli \
        boto3 \
        nibabel \
        numpy \
        click

COPY pipeline/03_spine_segmentation/ /app/03/

WORKDIR /app
