# Neurobotika Spine Pipeline (Phase 3)
# GPU image: TotalSpineSeg + SCT for spinal SAS segmentation
#
# Build:
#   docker build -f docker/spine.Dockerfile -t neurobotika-spine .
#
# Run locally:
#   docker run --gpus all -v $(pwd)/data:/data neurobotika-spine \
#     python /app/03/run_totalspineseg.py --input /data/raw/spine.nii.gz --output-dir /data/segmentations/spine/

FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2

RUN pip install --no-cache-dir \
    totalspineseg \
    nibabel \
    numpy \
    scipy \
    click

# Install Spinal Cord Toolbox (SCT)
# SCT is large (~2 GB); this makes the image heavy but avoids runtime downloads
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    git clone --depth 1 https://github.com/spinalcordtoolbox/spinalcordtoolbox.git /tmp/sct && \
    cd /tmp/sct && yes | ./install_sct -y && \
    rm -rf /tmp/sct && apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/sct_*/bin:${PATH}"

# Install AWS CLI for S3 data transfers
RUN pip install --no-cache-dir awscli

COPY pipeline/03_spine_segmentation/ /app/03/

WORKDIR /app
