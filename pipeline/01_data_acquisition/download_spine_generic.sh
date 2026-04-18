#!/usr/bin/env bash
# Fetch one subject's worth of spine-generic single-subject data and upload
# it to S3.
#
# Source: https://github.com/spine-generic/data-single-subject
#         (git-annex backed; the Zenodo zip at 10.5281/zenodo.4299148 is only
#          a 215 KB annex shim, not the data, so we use the upstream repo
#          directly.)
# Paper:  Cohen-Adad et al., Scientific Data 2021
#
# The repo name "single-subject" is misleading: it contains ~20 directories,
# each one the same person scanned at a different site. We grab just one
# by default. Pass a different --subject to override.

set -euo pipefail

SUBJECT="sub-douglas"
S3_DEST=""
WORK_DIR="${WORK_DIR:-/tmp/spine_download}"
REPO_URL="https://github.com/spine-generic/data-single-subject.git"

while [[ $# -gt 0 ]]; do
    case $1 in
        --subject)  SUBJECT="$2"; shift 2 ;;
        --s3-dest)  S3_DEST="$2"; shift 2 ;;
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $0 --subject SUB --s3-dest s3://bucket/prefix [--work-dir DIR]

Clones the spine-generic data-single-subject repo, runs git-annex to
fetch the binary payload for SUB only, and uploads the subject's files
plus the top-level BIDS metadata to s3://bucket/prefix/SUB/.
EOF
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$S3_DEST" ]; then
    echo "Error: --s3-dest is required" >&2
    exit 1
fi

DST_BASE="${S3_DEST%/}/${SUBJECT}"
REPO_DIR="${WORK_DIR}/data-single-subject"

echo "=== spine-generic single-subject → S3 ==="
echo "Subject:   ${SUBJECT}"
echo "Upstream:  ${REPO_URL}"
echo "Dest:      ${DST_BASE}"
echo "Work dir:  ${WORK_DIR}"
echo ""

mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

# Clone master *and* the git-annex branch explicitly. The git-annex branch
# carries the metadata mapping each annex key to the remotes that hold it
# (computecanada-public / amazon-private for spine-generic). Without it
# every `git annex get` returns "0 copies". --depth 1 or --single-branch
# on master both strip this branch, so we fetch both refs directly.
if [ ! -d "$REPO_DIR/.git" ]; then
    git clone --branch master "$REPO_URL" "$REPO_DIR"
    git -C "$REPO_DIR" fetch origin git-annex:refs/remotes/origin/git-annex
fi

cd "$REPO_DIR"

# Verify the subject directory exists before trying to fetch it
if [ ! -d "$SUBJECT" ] && [ ! -d "derivatives/labels/$SUBJECT" ]; then
    echo "Error: subject '${SUBJECT}' not found in repo" >&2
    echo "Available subjects:" >&2
    ls -d sub-* 2>&1 | head -30 >&2
    exit 1
fi

# git-annex init needs a user identity configured; provide a throwaway one
# for the ephemeral Batch container.
git config user.email "neurobotika-download@example.invalid"
git config user.name "neurobotika-download"
git annex init --quiet

# Fetch this subject's files (raw + derivatives if present). Let errors
# propagate — silent `|| true` once caused shims to land in S3 undetected.
echo "Fetching binary payload for ${SUBJECT}..."
GET_TARGETS=("$SUBJECT")
[ -d "derivatives/labels/${SUBJECT}" ] && GET_TARGETS+=("derivatives/labels/${SUBJECT}")
git annex get --jobs 4 "${GET_TARGETS[@]}"

# Sanity check: any .nii.gz file still at annex-shim size (< 4 KiB) means a
# fetch silently failed. Refuse to upload shims to S3.
SHIMS=$(find "$SUBJECT" derivatives/labels/${SUBJECT} 2>/dev/null \
        -name "*.nii.gz" -size -4k | head -5 || true)
if [ -n "$SHIMS" ]; then
    echo "Error: git-annex fetch left ≥1 file at annex-shim size:" >&2
    echo "$SHIMS" >&2
    exit 1
fi

# Upload to S3, resolving git-annex symlinks so we copy actual blobs.
# Include the subject dir, its derivatives, and top-level BIDS metadata.
echo ""
echo "Uploading to ${DST_BASE}..."

# BIDS root files (tiny but needed for downstream tools to parse the dataset)
for metadata in dataset_description.json participants.tsv participants.json README; do
    [ -f "$metadata" ] && aws s3 cp "$metadata" "${DST_BASE}/${metadata}"
done

# Subject's raw files (follow symlinks so git-annex blobs get copied)
aws s3 sync --follow-symlinks "$SUBJECT/" "${DST_BASE}/${SUBJECT}/"

# Subject's derivative labels if present
if [ -d "derivatives/labels/${SUBJECT}" ]; then
    aws s3 sync --follow-symlinks \
        "derivatives/labels/${SUBJECT}/" \
        "${DST_BASE}/derivatives/labels/${SUBJECT}/"
fi

echo ""
echo "=== spine-generic download complete ==="
aws s3 ls --recursive --summarize "${DST_BASE}/" | tail -2
