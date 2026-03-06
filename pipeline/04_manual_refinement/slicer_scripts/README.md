# 3D Slicer Scripts

These Python scripts are intended to be run from within 3D Slicer's Python console or interactor, **not** from the command line.

## Usage

1. Open 3D Slicer
2. Open the Python Console: `View > Python Console`
3. Run: `exec(open('/path/to/load_volumes.py').read())`

Or use the Python Interactor: `View > Python Interactor` and paste the script.

## Scripts

### `load_volumes.py`

Loads the MGH 100 um brain volume and the SynthSeg label map overlay, configures the slice views, and creates a new segmentation node ready for manual editing.

**Configuration:** Edit the file paths at the top of the script to match your local data directory.
