# Phase 7: Custom Model Training (Optional)

Train a custom nnU-Net model on the manually refined CSF segmentations. This produces a reusable, publicly releasable tool that can automatically segment CSF structures (including foramina and cisterns) from new MRI scans.

## Why This Matters

No existing model segments foramina, the cerebral aqueduct, or individual basal cisterns. A trained model based on your manual labels would be a genuine contribution to the neuroimaging community.

## Requirements

- At least 10-20 labelled volumes for reasonable performance (more is better)
- GPU with 12+ GB VRAM recommended
- nnU-Net v2: `pip install nnunetv2 torch`

## Scripts

### `prepare_nnunet_dataset.py`

Converts your label maps into the nnU-Net dataset format (specific directory structure, naming convention, and dataset.json).

```bash
python prepare_nnunet_dataset.py \
    --images-dir data/raw/ \
    --labels-dir data/segmentations/manual/ \
    --output-dir data/nnunet/Dataset001_CSF
```

### `train_nnunet.sh`

Runs nnU-Net training with automatic architecture and hyperparameter configuration.

```bash
./train_nnunet.sh Dataset001_CSF 3d_fullres 0
```

## nnU-Net Dataset Structure

nnU-Net expects a specific layout:

```
data/nnunet/
├── nnUNet_raw/
│   └── Dataset001_CSF/
│       ├── dataset.json
│       ├── imagesTr/
│       │   ├── case_0000_0000.nii.gz
│       │   └── ...
│       ├── labelsTr/
│       │   ├── case_0000.nii.gz
│       │   └── ...
│       └── imagesTs/       (optional test set)
├── nnUNet_preprocessed/    (auto-generated)
└── nnUNet_results/         (training outputs)
```

## Notes

- nnU-Net is self-configuring: it automatically determines the best architecture, patch size, batch size, and training schedule from your data
- Training takes hours to days depending on dataset size and GPU
- The trained model can be shared via Zenodo or a dedicated release
