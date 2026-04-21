"""
3D Slicer script: Pull Phase 2/3 segmentations from S3 and set up a
SegmentEditor workspace ready for manual refinement.

Intended to run inside Slicer's Python console:

    exec(open('/abs/path/to/pull_from_s3.py').read())

The run_id, brain_subject, spine_subject, and local staging dir are read
from environment variables so the same script works for every run
without editing. Set them in the shell that launched Slicer, e.g.::

    export NEUROBOTIKA_RUN_ID=run-2026-04-18-125403
    export NEUROBOTIKA_BRAIN_SUBJECT=sub-EXC004
    export NEUROBOTIKA_SPINE_SUBJECT=sub-douglas
    export NEUROBOTIKA_LOCAL_DIR="$HOME/neurobotika-slicer"
    export NEUROBOTIKA_BUCKET=neurobotika-data
    export AWS_PROFILE=neurobotika
    export AWS_DEFAULT_REGION=eu-central-1
    /opt/slicer/Slicer --python-script pull_from_s3.py

What this script does:

1. Downloads a consistent set of volumes from S3 into NEUROBOTIKA_LOCAL_DIR.
2. Loads the 200 µm MGH brain volume as the background in all slice views.
3. Loads the Phase 2 SynthSeg output as a label overlay (30 % opacity),
   so you can see which CSF structures are already segmented before
   you start painting the ones that aren't.
4. Loads the Phase 3 cord + canal soft segmentations (as a secondary
   overlay scene) for spine-region context.
5. Creates an empty ``CSF_Manual_Segmentation`` node with the 20-label
   convention from docs/manual-segmentation-guide.md already registered
   (each label gets the right color), so you can just start painting.
6. Switches to the Segment Editor module.

After refining, use ``push_merged.py`` to upload the merged label map and
resume the Step Functions execution.
"""

import os
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Config from env (with sensible defaults for local quick-start)
# ---------------------------------------------------------------------------

RUN_ID         = os.environ.get("NEUROBOTIKA_RUN_ID",         "run-example")
BRAIN_SUBJECT  = os.environ.get("NEUROBOTIKA_BRAIN_SUBJECT",  "sub-yv98")        # Lüsebrink 2021
SPINE_SUBJECT  = os.environ.get("NEUROBOTIKA_SPINE_SUBJECT",  "sub-douglas")
BUCKET         = os.environ.get("NEUROBOTIKA_BUCKET",         "neurobotika-data")
LOCAL_DIR      = Path(os.environ.get("NEUROBOTIKA_LOCAL_DIR", str(Path.home() / "neurobotika-slicer")))

S3_RUN = f"s3://{BUCKET}/runs/{RUN_ID}"

# Each entry is (s3 sub-path relative to S3_RUN, local filename).
# Only volumes — small JSON/CSV metadata is skipped to keep startup fast.
FILES_TO_FETCH = [
    # Brain raw T2 SPACE (450 µm, bright-CSF): background image in Slicer
    (f"raw/lusebrink_2021/{BRAIN_SUBJECT}/anat/{BRAIN_SUBJECT}_T2w.nii.gz",
     "brain_T2w.nii.gz"),
    # Brain raw T1w (co-registered reference)
    (f"raw/lusebrink_2021/{BRAIN_SUBJECT}/anat/{BRAIN_SUBJECT}_T1w.nii.gz",
     "brain_T1w.nii.gz"),
    # Brain segmentation (SynthSeg output on the bias-corrected T2w)
    (f"seg/brain/{BRAIN_SUBJECT}/seg.nii.gz",            "brain_seg.nii.gz"),
    # Spine T2w raw volume (secondary context)
    (f"raw/spine_generic/{SPINE_SUBJECT}/{SPINE_SUBJECT}/anat/{SPINE_SUBJECT}_T2w.nii.gz",
     "spine_T2w.nii.gz"),
    # Spine soft segmentations from TotalSpineSeg
    (f"seg/spine/{SPINE_SUBJECT}/step1_cord/input.nii.gz",  "spine_cord.nii.gz"),
    (f"seg/spine/{SPINE_SUBJECT}/step1_canal/input.nii.gz", "spine_canal.nii.gz"),
    # Spine final multi-label segmentation
    (f"seg/spine/{SPINE_SUBJECT}/step2_output/input.nii.gz", "spine_multilabel.nii.gz"),
]


# ---------------------------------------------------------------------------
# 20-label CSF convention (from docs/manual-segmentation-guide.md).
# (label_id, name, (r,g,b) in 0–255)
# ---------------------------------------------------------------------------
CSF_LABEL_SPEC = [
    (1,  "left_lateral_ventricle",        (120,  18, 134)),
    (2,  "right_lateral_ventricle",       (236,  13, 176)),
    (3,  "third_ventricle",               (204, 182, 142)),
    (4,  "cerebral_aqueduct",             (  0, 255, 255)),
    (5,  "fourth_ventricle",              (196,  58, 250)),
    (6,  "left_foramen_of_monro",         (255, 165,   0)),
    (7,  "right_foramen_of_monro",        (255, 200,   0)),
    (8,  "foramen_of_magendie",           (255,   0,   0)),
    (9,  "left_foramen_of_luschka",       (  0, 255,   0)),
    (10, "right_foramen_of_luschka",      (  0, 200,   0)),
    (11, "cisterna_magna",                (255, 218, 185)),
    (12, "prepontine_cistern",            (180, 210, 255)),
    (13, "ambient_cistern",               (210, 180, 140)),
    (14, "quadrigeminal_cistern",         (100, 200, 200)),
    (15, "interpeduncular_cistern",       (200, 150, 200)),
    (16, "sylvian_cistern",               (150, 200, 150)),
    (17, "cerebral_subarachnoid_space",   ( 60,  60, 220)),
    (18, "spinal_subarachnoid_space",     (220, 100,  60)),
    (19, "foramen_magnum_junction",       (128, 128,   0)),
    (20, "choroid_plexus",                (100, 100, 100)),
]


# ---------------------------------------------------------------------------
# Logic
# ---------------------------------------------------------------------------

def _preflight_run_id() -> None:
    """Sanity-check that the configured NEUROBOTIKA_RUN_ID actually points
    at data in S3 before we try to launch Slicer against it.

    A common failure mode: the user copies the Step Functions *execution
    name* (fresh per execution) from the AWS console instead of the
    pipeline *run_id* (stable across executions for the same S3 data).
    Those usually differ — resumes, retries, and phase-specific re-
    launches all get new execution names while reusing the same run_id.
    When the two are confused, this script previously ran to completion
    but loaded nothing visible in Slicer.

    Check here that at least one expected upstream output (the Phase 2
    brain seg or the Phase 3 spine seg) exists under the run_id prefix.
    If not, list sibling run_ids in S3 so the user can pick the right one.
    """
    import subprocess

    key_prefix = f"runs/{RUN_ID}/seg/"
    probe = subprocess.run(
        ["aws", "s3", "ls", f"s3://{BUCKET}/{key_prefix}", "--recursive"],
        capture_output=True, text=True,
    )

    if probe.returncode == 0 and probe.stdout.strip():
        return  # looks good

    print("")
    print("=" * 64)
    print(f"  ERROR: no Phase 2/3 outputs under s3://{BUCKET}/{key_prefix}")
    print(f"  NEUROBOTIKA_RUN_ID='{RUN_ID}' is probably wrong.")
    print("")
    print("  Common cause: you copied the Step Functions *execution name*")
    print("  from the AWS console (fresh per execution) instead of the")
    print("  pipeline *run_id* from the SNS email body. The run_id is")
    print("  stable across executions; the execution name is not.")
    print("")
    print("  Existing run_ids in S3 (pick the one whose seg/ has your data):")
    ls = subprocess.run(
        ["aws", "s3", "ls", f"s3://{BUCKET}/runs/"],
        capture_output=True, text=True,
    )
    for line in ls.stdout.splitlines():
        parts = line.strip().split()
        if parts and parts[0] == "PRE":
            print(f"    {parts[1].rstrip('/')}")
    print("=" * 64)
    raise SystemExit(1)


def download_from_s3() -> dict:
    """Fetch all required files from S3 into LOCAL_DIR.

    Uses the `aws` CLI instead of boto3 so this script runs fine inside
    Slicer's embedded Python without extra pip installs. The user just
    needs aws CLI on PATH.

    Returns a dict mapping local filename (str) to absolute local path.
    """
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    resolved = {}

    for s3_rel, local_name in FILES_TO_FETCH:
        src = f"{S3_RUN}/{s3_rel}"
        dst = LOCAL_DIR / local_name
        if dst.exists():
            print(f"  [cached] {local_name}")
            resolved[local_name] = str(dst)
            continue

        print(f"  [fetch]  {local_name}  <-  {src}")
        try:
            subprocess.run(
                ["aws", "s3", "cp", src, str(dst)],
                check=True, capture_output=True, text=True,
            )
            resolved[local_name] = str(dst)
        except subprocess.CalledProcessError as e:
            print(f"  [MISS]   {local_name}: {e.stderr.strip()}")
            # Non-fatal — the run might not have this file (e.g. spine
            # skipped). Downstream setup handles missing entries.

    return resolved


def setup_slicer_workspace(files: dict):
    """Load volumes into Slicer and configure the viewer + segmentation node."""
    import slicer
    import vtk

    # ---- Load background image(s) --------------------------------------------------

    brain_node = None
    if "brain_T2w.nii.gz" in files:
        print("Loading brain T2 SPACE (bright CSF)...")
        brain_node = slicer.util.loadVolume(files["brain_T2w.nii.gz"])
        if brain_node is None:
            print("  WARN: brain T2w volume failed to load")

    # T1w as a secondary reference (useful for cortical/nuclear anatomy)
    if "brain_T1w.nii.gz" in files:
        print("Loading brain T1w (co-registered reference)...")
        slicer.util.loadVolume(files["brain_T1w.nii.gz"])

    # Phase 2 seg as a label overlay (so the user knows what's already segmented)
    brain_label_node = None
    if "brain_seg.nii.gz" in files:
        print("Loading brain segmentation as label overlay...")
        brain_label_node = slicer.util.loadLabelVolume(files["brain_seg.nii.gz"])

    # Phase 3 cord + canal as secondary volumes (visible via the Data tab)
    for key in ("spine_cord.nii.gz", "spine_canal.nii.gz", "spine_multilabel.nii.gz", "spine_T2w.nii.gz"):
        if key in files:
            print(f"Loading {key}...")
            slicer.util.loadVolume(files[key])

    # ---- Wire the brain volume as the background on all slice views ----------------

    if brain_node is not None:
        layout_manager = slicer.app.layoutManager()
        for view_name in ["Red", "Green", "Yellow"]:
            widget = layout_manager.sliceWidget(view_name)
            if widget is None:
                continue
            logic = widget.sliceLogic()
            composite = logic.GetSliceCompositeNode()
            composite.SetBackgroundVolumeID(brain_node.GetID())
            if brain_label_node is not None:
                composite.SetLabelVolumeID(brain_label_node.GetID())
                composite.SetLabelOpacity(0.3)

    # ---- Create the manual segmentation node with the 20-label schema ready --------

    seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    seg_node.SetName(f"CSF_Manual_{RUN_ID}")
    if brain_node is not None:
        seg_node.SetReferenceImageGeometryParameterFromVolumeNode(brain_node)

    segmentation = seg_node.GetSegmentation()
    for label_id, name, rgb in CSF_LABEL_SPEC:
        color = (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
        # Segment is named after the structure; the label integer is
        # recorded as a tag so export can preserve it.
        segment = slicer.vtkSegment()
        segment.SetName(name)
        segment.SetColor(*color)
        segment.SetTag("LabelValue", str(label_id))
        segmentation.AddSegment(segment, name)

    # Switch to Segment Editor
    slicer.util.selectModule("SegmentEditor")

    # Set the Segment Editor's active segmentation + source volume
    # (mostly a convenience — user still has to click into the module)
    seg_editor = slicer.modules.segmenteditor.widgetRepresentation().self()
    if seg_editor is not None:
        seg_editor.setSegmentationNode(seg_node)
        if brain_node is not None:
            seg_editor.setSourceVolumeNode(brain_node)

    # ---- Summary -----------------------------------------------------------------

    print("")
    print("=" * 64)
    print(f"  Workspace ready for run_id={RUN_ID}")
    print(f"  Brain subject: {BRAIN_SUBJECT} | Spine subject: {SPINE_SUBJECT}")
    print(f"  Local staging dir: {LOCAL_DIR}")
    print("")
    print("  Background   : Lüsebrink 450 µm T2 SPACE (CSF bright)")
    print("  Label overlay: Phase 2 SynthSeg output (30 % opacity)")
    print("  Other loaded : brain_T1w, spine_cord, spine_canal, spine_multilabel, spine_T2w")
    print(f"  Segmentation : {seg_node.GetName()}  (20 empty segments pre-configured)")
    print("")
    print("  NEXT:")
    print("    1. Refine missing structures using the Segment Editor.")
    print("       See docs/manual-segmentation-guide.md for per-structure strategy.")
    print("    2. When finished, save Slicer scene, then from a terminal run:")
    print("         python push_merged.py \\")
    print(f"             --run-id {RUN_ID} \\")
    print(f"             --input \"$HOME/neurobotika-slicer/merged_labels.nii.gz\" \\")
    print("             --task-token \"$NEUROBOTIKA_TASK_TOKEN\"")
    print("=" * 64)


# Entry point when exec'd inside Slicer's console
_preflight_run_id()
files = download_from_s3()
setup_slicer_workspace(files)
