# Architectural Decision Records

This file holds significant, load-bearing decisions whose rationale isn't
obvious from the code alone. Keep ADRs append-only: if a decision is
revised, add a new ADR explaining the revision, don't edit the old one.

Format loosely follows the [Michael Nygard ADR template][nygard]: context,
decision, consequences.

[nygard]: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

---

## ADR-001 — 2026-04-20 — Brain dataset strategy: Lüsebrink primary, MGH demoted to optional

### Context

The pipeline launched with the **MGH ds002179 ex-vivo 100 µm** brain
dataset as the sole brain input. MGH's spatial resolution is unmatched
(100 µm isotropic 7 T) but it is post-mortem: the brain was removed,
fixed, and rescanned. Fixation drains the subarachnoid space and
collapses the sulci, so the "CSF" compartment visible on MGH is a
deformation-artifact envelope, not a physiological fluid volume.

For Neurobotika's downstream needs:

- **Phase 2 segmentation**: SynthSeg on MGH recovered ~185 mL of label 24
  (extraventricular CSF) — but that value reflects pia-to-dura distance
  minus cortex under fixation, not in-vivo SAS width.
- **Phase 4 manual refinement**: cisterns collapse more dramatically than
  ventricles under fixation. Manually drawing the prepontine, ambient,
  and quadrigeminal cisterns on MGH would produce structures that look
  anatomically correct but are geometrically wrong by 1–3 mm.
- **Phase 8 LBM permeability calibration**: requires realistic SAS width
  and sulcal CSF distribution to produce defensible κ values against
  the Rossinelli 2023 SRµCT ONSAS morphometrics. MGH's fixation-distorted
  geometry would bias the entire permeability tensor.

Options considered:

- **Augment**: MGH + Lüsebrink, reconcile via dual non-linear registration
  to MNI. Explicitly rejected — ex-vivo fixation shrinkage produces
  registration errors on the order of 2–5 mm, which exceeds the 450 µm
  resolution gain Lüsebrink provides. The two-deformation-field approach
  introduces more error than it resolves.
- **Replace**: drop MGH entirely, keep only Lüsebrink. Simplest. Loses
  MGH's cortical-ribbon detail permanently.
- **Augment-lite** (selected): Lüsebrink primary for the default pipeline;
  MGH retained in the dataset catalogue and tooling but not wired into
  the default Step Functions Phase 1. Available via ad-hoc Batch job for
  future cortical-ribbon / OCT-SLAM validation work where its 200 µm pial
  surface geometry will be the deciding factor.

### Decision

**Lüsebrink 2021 ds003563 (450 µm T2 SPACE, `sub-yv98` `ses-3777`) is the
default brain input for Neurobotika.** The state machine's Phase 1
Parallel state downloads it, Phase 2 segments it, Phase 4 manually refines
on it, and Phase 8 derives SAS widths from it.

**MGH ds002179 is retained as an optional, non-default dataset.** The
`download-mgh` Batch job definition still exists and `run_downloads.sh
--dataset mgh` still works, but the state machine does not call it.
Users who need MGH for cortical-ribbon / OCT-SLAM work submit it as a
separate Batch job against a separate `run_id`.

**Two-brain coregistration is explicitly rejected** for the reasons
above. Do not re-propose this approach without new evidence that ex-vivo
fixation distortion has been modelled or corrected.

### Consequences

- Phase 8 permeability calibration against Rossinelli/Yiallourou targets
  becomes physiologically defensible. This is the core scientific
  motivation for the change.
- Phase 4 manual work becomes dramatically easier: T2 SPACE is bright-CSF,
  where MGH's synthesized FLASH25 is dark-CSF. Fewer reversed-contrast
  orientation mistakes, smaller time-to-fluency for the human annotator.
- Lüsebrink ds003563 sub-yv98 is a single subject — same n=1 statistical
  posture as MGH. Neurobotika's "reference viewer + microrobotics
  substrate" goal doesn't require population stats, but document this
  explicitly in any future publications: all macro-anatomical claims
  derive from a single in-vivo subject.
- Downstream pipeline paths change from `raw/mgh_100um/sub-EXC004/MNI/
  Synthesized_FLASH25_in_MNI_v2_200um.nii.gz` to `raw/lusebrink_2021/
  sub-yv98/anat/sub-yv98_T2w_biasCorrected.nii.gz`. Existing runs in S3
  (`run-2026-04-18-125403`, `run-2026-04-19-supersynth`) retain their
  MGH-based outputs and become historical baselines only.
- Phase 8's raycast-based SAS-width calibration approach stays valid,
  but the surface normals now originate from Lüsebrink's pial surface
  (from SynthSeg on the T2 SPACE) rather than MGH's. Resolution is
  lower (450 µm vs 200 µm) but for SAS widths of 1–5 mm over cortex
  and larger in cisterns, 450 µm resolves the width to the ~10 % level
  required for the LBM κ calibration. Morphometric fine-structure
  targets still come from Rossinelli SRµCT, not from MRI at any scale.
