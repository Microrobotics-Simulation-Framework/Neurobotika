# Neurobotika Brain Segmentation (Phase 2) — SuperSynth via FreeSurfer 8.2
#
# SuperSynth (mri_super_synth) is a multi-task U-Net that does ex-vivo-
# aware segmentation + MNI registration + super-resolution + QC in one
# pass. It's purpose-built for ex-vivo MRI (our MGH ds002179 input),
# removes the need for a pre-resample-to-1mm step, and emits
# extracerebral structures that plain SynthSeg omits.
#
# Shipped in freesurfer/freesurfer:8.2.0 (~14.3 GB compressed; Batch
# instances have 100 GiB root volumes via the launch template).
#
# Known upstream bug (FS 8.2): label 24 (extraventricular CSF) is
# written incorrectly to the volumes CSV. run_brainseg.py recomputes
# all volumes from the seg NIfTI itself and writes volumes.csv so
# downstream consumers don't inherit the bug.
#
# Build:
#   ./docker/build-on-codebuild.sh brain

FROM freesurfer/freesurfer:8.2.0

# FreeSurfer 8.2 bundles its own Python under a version-specific path
# and doesn't expose python3 on the default PATH. Find the bundled
# interpreter (dir may be versioned like /usr/local/freesurfer/8.2.0/…)
# and symlink python3 into /usr/local/bin so our wrapper can use it.
# CentOS 8 base's repos are EOL, so avoid dnf entirely — bootstrap pip
# via get-pip.py against the FS Python.
RUN FS_PY_BIN=$(ls -d /usr/local/freesurfer/*/python/bin 2>/dev/null | head -1) && \
    [ -z "$FS_PY_BIN" ] && FS_PY_BIN=$(ls -d /usr/local/freesurfer/python/bin 2>/dev/null | head -1) ; \
    if [ -z "$FS_PY_BIN" ] || [ ! -x "$FS_PY_BIN/python3" ]; then \
        echo "ERROR: no python3 under /usr/local/freesurfer — paths tried:" >&2; \
        ls -d /usr/local/freesurfer/* 2>/dev/null >&2; \
        exit 1; \
    fi && \
    echo "FS Python: $FS_PY_BIN/python3" && \
    ln -sf "$FS_PY_BIN/python3" /usr/local/bin/python3 && \
    python3 --version

# Bootstrap pip for the FS-bundled Python.
RUN python3 -m ensurepip --upgrade 2>/dev/null || \
    (curl -sL https://bootstrap.pypa.io/pip/get-pip.py -o /tmp/get-pip.py && \
     python3 /tmp/get-pip.py && rm /tmp/get-pip.py)

# Diagnostic: confirm mri_super_synth is actually there in 8.2.
RUN (ls /usr/local/freesurfer/bin/ 2>/dev/null | grep -iE 'synth|super' || \
     ls /usr/local/freesurfer/*/bin/ 2>/dev/null | grep -iE 'synth|super' || \
     echo "(no synth/super binaries found)") && \
    (which mri_super_synth 2>/dev/null || echo "mri_super_synth NOT on PATH — may need to activate FS env")

# Use `python3 -m pip` so we don't depend on a pip3 shim existing on PATH.
RUN python3 -m pip install --no-cache-dir \
        awscli \
        boto3 \
        nibabel \
        numpy \
        scipy \
        click

# FS 8.2 ships a CPU-only PyTorch in its bundled Python. SuperSynth's
# --device cuda path hard-fails with "Torch not compiled with CUDA
# enabled". Replace with a CUDA 12.1 wheel that matches the GPU drivers
# on the ECS-optimized GPU AMI. Adds ~2.5 GB to the image but unlocks
# GPU inference on g5.xlarge (A10G) and g6.xlarge (L4) — both have the
# 24 GB VRAM SuperSynth requires. ~24 GB system RAM on g5/g6 is not
# enough for CPU-mode inference.
RUN python3 -m pip install --no-cache-dir --upgrade \
        --index-url https://download.pytorch.org/whl/cu121 \
        torch torchvision

# SuperSynth's model weights are distributed separately from the FS image.
# Bake them in at build time so the container boots self-contained (no
# per-job download latency or dependency on the MGH ftp server at runtime).
RUN curl -sSL --fail --retry 3 \
    https://ftp.nmr.mgh.harvard.edu/pub/dist/lcnpublic/dist/SuperSynth_Iglesias_2025/SuperSynth_August_2025.pth \
    -o /usr/local/freesurfer/8.2.0-1/models/SuperSynth_August_2025.pth && \
    ls -lh /usr/local/freesurfer/8.2.0-1/models/SuperSynth_August_2025.pth

COPY pipeline/02_brain_segmentation/ /app/02/

WORKDIR /app
