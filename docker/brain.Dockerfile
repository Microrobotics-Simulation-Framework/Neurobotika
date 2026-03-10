# Neurobotika Brain Pipeline (Phases 1-2)
# GPU image: SynthSeg inference + data acquisition utilities
#
# Build:
#   docker build -f docker/brain.Dockerfile -t neurobotika-brain .
#
# Run locally:
#   docker run --gpus all -v $(pwd)/data:/data neurobotika-brain \
#     python /app/02/run_synthseg.py --input /data/raw/brain.nii.gz --output /data/segmentations/brain/

FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2

RUN pip install --no-cache-dir \
    synthseg \
    nibabel \
    numpy \
    scipy \
    click

# Install AWS CLI for S3 data transfers
RUN pip install --no-cache-dir awscli

COPY pipeline/01_data_acquisition/ /app/01/
COPY pipeline/02_brain_segmentation/ /app/02/

WORKDIR /app
