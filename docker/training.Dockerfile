# Neurobotika Training Pipeline (Phase 7)
# GPU image: nnU-Net model training
#
# Build:
#   docker build -f docker/training.Dockerfile -t neurobotika-training .
#
# Run locally:
#   docker run --gpus all -v $(pwd)/data:/data neurobotika-training \
#     bash /app/07/train_nnunet.sh

FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2

RUN pip install --no-cache-dir \
    nnunetv2 \
    nibabel \
    numpy \
    scipy \
    click

# Install AWS CLI for S3 data transfers
RUN pip install --no-cache-dir awscli

COPY pipeline/07_model_training/ /app/07/

# nnU-Net environment variables
ENV nnUNet_raw="/data/nnunet/raw"
ENV nnUNet_preprocessed="/data/nnunet/preprocessed"
ENV nnUNet_results="/data/nnunet/results"

WORKDIR /app
