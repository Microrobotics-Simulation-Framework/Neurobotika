# Neurobotika Brain Segmentation (Phase 2) — SynthSeg via FreeSurfer
#
# Uses the official FreeSurfer 7.4.1 image because upstream SynthSeg on its
# own is not on PyPI and its setup.py pins to Python 3.6/3.8 with old
# TF/Keras versions. FreeSurfer 7.3.2+ ships mri_synthseg natively,
# handles the weights bundling, and works without a FreeSurfer license.
#
# Build:
#   docker build -f docker/brain.Dockerfile -t neurobotika-brain .
#
# Run locally:
#   docker run --gpus all neurobotika-brain \
#     python3 /app/02/run_synthseg.py --input s3://... --output s3://...

FROM freesurfer/freesurfer:7.4.1

# freesurfer/freesurfer:7.4.1 is built on CentOS Stream 8, which reached
# EOL in May 2024. mirrorlist.centos.org is offline, so dnf can't reach any
# repo. Redirect to vault.centos.org (the read-only archive) — the standard
# workaround for building on post-EOL CentOS 8 images.
RUN sed -i 's|^mirrorlist=|#mirrorlist=|'                       /etc/yum.repos.d/*.repo && \
    sed -i 's|^#*baseurl=http://mirror.centos.org|baseurl=https://vault.centos.org|' /etc/yum.repos.d/*.repo

# FS ships its own Python bundled under /usr/local/freesurfer/python/ for
# mri_synthseg's use; our wrapper runs on the system python3 instead and
# just needs pip for awscli/boto3/nibabel. mri_synthseg stays untouched.
RUN dnf install -y python3-pip && dnf clean all

RUN pip3 install --no-cache-dir \
        awscli \
        boto3 \
        nibabel \
        numpy \
        scipy \
        click

COPY pipeline/02_brain_segmentation/ /app/02/

WORKDIR /app
