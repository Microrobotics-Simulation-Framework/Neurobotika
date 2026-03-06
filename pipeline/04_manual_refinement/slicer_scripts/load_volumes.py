"""
3D Slicer script: Load volumes and set up segmentation workspace.

Run from 3D Slicer's Python console:
    exec(open('/path/to/load_volumes.py').read())

Edit the paths below to match your local data directory.
"""

# === CONFIGURATION === #
DATA_DIR = "data"  # Adjust to your absolute path
BRAIN_VOLUME = f"{DATA_DIR}/raw/mgh_100um/brain_200um.nii.gz"
SYNTHSEG_LABELS = f"{DATA_DIR}/segmentations/brain/synthseg_labels.nii.gz"
# ==================== #

import slicer


def load_and_setup():
    # Load the brain volume
    print(f"Loading brain volume: {BRAIN_VOLUME}")
    brain_node = slicer.util.loadVolume(BRAIN_VOLUME)

    # Load SynthSeg labels as a label map overlay
    print(f"Loading SynthSeg labels: {SYNTHSEG_LABELS}")
    label_node = slicer.util.loadLabelVolume(SYNTHSEG_LABELS)

    # Create a new segmentation node for manual work
    seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    seg_node.SetName("CSF_Manual_Segmentation")
    seg_node.SetReferenceImageGeometryParameterFromVolumeNode(brain_node)

    # Set the brain volume as the background in all slice views
    layout_manager = slicer.app.layoutManager()
    for view_name in ["Red", "Green", "Yellow"]:
        widget = layout_manager.sliceWidget(view_name)
        logic = widget.sliceLogic()
        composite = logic.GetSliceCompositeNode()
        composite.SetBackgroundVolumeID(brain_node.GetID())
        composite.SetLabelVolumeID(label_node.GetID())
        composite.SetLabelOpacity(0.3)

    # Switch to Segment Editor
    slicer.util.selectModule("SegmentEditor")

    print("\nWorkspace ready.")
    print("  Background: brain volume")
    print("  Label overlay: SynthSeg (30% opacity)")
    print("  Segmentation node: CSF_Manual_Segmentation")
    print("\nUse the Segment Editor to add segments and start tracing.")


load_and_setup()
