#!/usr/bin/env bash
# Check AWS service quotas required for the Neurobotika pipeline.
#
# Reads instance types from .env and checks whether your account has
# sufficient vCPU quota to run them. Prints a clear pass/fail summary
# and exits non-zero if any quota is insufficient.
#
# Usage:
#   cd infra
#   source .env
#   ./check-quotas.sh
#
# Or directly:
#   cd infra
#   ./check-quotas.sh          # reads .env automatically
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

: "${AWS_REGION:=eu-central-1}"
: "${AWS_PROFILE:=neurobotika}"
: "${GPU_INSTANCE_TYPES:=g4dn.xlarge,g5.xlarge,g6.xlarge}"
: "${CPU_INSTANCE_TYPES:=c6i.4xlarge,c7i.4xlarge,c6i.2xlarge}"
: "${DOWNLOAD_INSTANCE_TYPES:=c6gn.xlarge,c6gn.4xlarge,c6i.xlarge}"
: "${GPU_MAX_VCPUS:=8}"
: "${CPU_MAX_VCPUS:=32}"

export AWS_PROFILE AWS_REGION

# Service Quotas codes for EC2 vCPU limits
# See: https://docs.aws.amazon.com/ec2/latest/instancetypes/ec2-instance-quotas.html
declare -A QUOTA_CODES=(
  # On-Demand
  ["G and VT On-Demand"]="L-DB2E81BA"
  ["Standard On-Demand"]="L-1216C47A"
  ["P On-Demand"]="L-417A185B"
  # Spot
  ["G and VT Spot"]="L-3819A6DF"
  ["Standard Spot"]="L-34B43A08"
  ["P Spot"]="L-7212CCBC"
)

# What each instance family maps to
declare -A FAMILY_QUOTA=(
  ["g4dn"]="G and VT"
  ["g5"]="G and VT"
  ["g6"]="G and VT"
  ["p3"]="P"
  ["p4"]="P"
  ["c6i"]="Standard"
  ["c7i"]="Standard"
  ["c7a"]="Standard"
  ["c6gn"]="Standard"
  ["m5"]="Standard"
  ["t3"]="Standard"
)

# vCPU counts for common instance sizes
declare -A INSTANCE_VCPUS=(
  ["g4dn.xlarge"]=4
  ["g5.xlarge"]=4
  ["g5.2xlarge"]=8
  ["g6.xlarge"]=4
  ["p3.2xlarge"]=8
  ["c6i.xlarge"]=4
  ["c6i.2xlarge"]=8
  ["c6i.4xlarge"]=16
  ["c6i.8xlarge"]=32
  ["c7i.4xlarge"]=16
  ["c7i.8xlarge"]=32
  ["c7a.4xlarge"]=16
  ["c7a.8xlarge"]=32
  ["c6gn.xlarge"]=4
  ["c6gn.4xlarge"]=16
  ["c6gn.8xlarge"]=32
  ["m5.xlarge"]=4
  ["t3.xlarge"]=4
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}Neurobotika Pipeline — AWS Quota Check${NC}"
echo -e "Region:  ${AWS_REGION}"
echo -e "Profile: ${AWS_PROFILE}"
echo ""

# --- Verify credentials ---
echo -n "Checking AWS credentials... "
if ! IDENTITY=$(aws sts get-caller-identity --output json 2>&1); then
  echo -e "${RED}FAILED${NC}"
  echo "$IDENTITY"
  echo ""
  echo "Make sure your AWS profile '${AWS_PROFILE}' is configured:"
  echo "  aws configure --profile ${AWS_PROFILE}"
  exit 1
fi

ACCOUNT_ID=$(echo "$IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
echo -e "${GREEN}OK${NC} (account: ${ACCOUNT_ID})"
echo ""

# --- Gather all instance types from config ---
ALL_GPU_INSTANCES="${GPU_INSTANCE_TYPES}"
ALL_CPU_INSTANCES="${CPU_INSTANCE_TYPES},${DOWNLOAD_INSTANCE_TYPES}"

# Deduplicate
ALL_INSTANCES=$(echo "${ALL_GPU_INSTANCES},${ALL_CPU_INSTANCES}" | tr ',' '\n' | sort -u)

echo -e "${BOLD}Configured instance types:${NC}"
echo ""
echo "  GPU (Phases 2,3,7): ${GPU_INSTANCE_TYPES}"
echo "  CPU (Phases 5,6):   ${CPU_INSTANCE_TYPES}"
echo "  Download (Phase 1): ${DOWNLOAD_INSTANCE_TYPES}"
echo "  Max GPU vCPUs:      ${GPU_MAX_VCPUS}"
echo "  Max CPU vCPUs:      ${CPU_MAX_VCPUS}"
echo ""

# --- Determine required quotas ---
# We need: max vCPU of largest configured instance in each family, for both spot and on-demand
declare -A REQUIRED_SPOT
declare -A REQUIRED_ONDEMAND

for inst in $ALL_INSTANCES; do
  family=$(echo "$inst" | sed 's/\.[a-z0-9]*$//')
  vcpus=${INSTANCE_VCPUS[$inst]:-0}
  quota_family=${FAMILY_QUOTA[$family]:-""}

  if [ -z "$quota_family" ]; then
    echo -e "${YELLOW}WARN${NC}: Unknown instance family '${family}' for ${inst}, skipping quota check"
    continue
  fi

  # Spot: need at least this many vCPUs
  current=${REQUIRED_SPOT[$quota_family]:-0}
  if [ "$vcpus" -gt "$current" ]; then
    REQUIRED_SPOT[$quota_family]=$vcpus
  fi

  # On-Demand (fallback): same requirement
  current=${REQUIRED_ONDEMAND[$quota_family]:-0}
  if [ "$vcpus" -gt "$current" ]; then
    REQUIRED_ONDEMAND[$quota_family]=$vcpus
  fi
done

# GPU phases run on spot with on-demand fallback; need at least max single instance vCPUs
# CPU phases may run concurrently; we use the configured max_vcpus as the requirement
if [ "${REQUIRED_SPOT["Standard"]:-0}" -lt "$CPU_MAX_VCPUS" ]; then
  REQUIRED_SPOT["Standard"]=$CPU_MAX_VCPUS
fi
if [ "${REQUIRED_SPOT["G and VT"]:-0}" -lt "$GPU_MAX_VCPUS" ]; then
  REQUIRED_SPOT["G and VT"]=$GPU_MAX_VCPUS
fi

# --- Fetch current quotas and compare ---
echo -e "${BOLD}Checking quotas...${NC}"
echo ""

FAILURES=0
WARNINGS=0

check_quota() {
  local label="$1"
  local code="$2"
  local required="$3"

  local raw current

  # get-service-quota returns the applied value (including any increases you've been granted)
  raw=$(aws service-quotas get-service-quota \
    --service-code ec2 \
    --quota-code "$code" \
    --query 'Quota.Value' \
    --output text 2>/dev/null) || raw=""

  # Fallback to the default quota if applied quota not found
  if [ -z "$raw" ] || [ "$raw" = "None" ]; then
    raw=$(aws service-quotas get-aws-default-service-quota \
      --service-code ec2 \
      --quota-code "$code" \
      --query 'Quota.Value' \
      --output text 2>/dev/null) || raw=""
  fi

  # Convert float to int (AWS returns e.g. "5.0")
  # Use LC_NUMERIC=C to ensure "." is the decimal separator regardless of locale
  current=$(LC_NUMERIC=C printf "%.0f" "$raw" 2>/dev/null) || current=""
  if ! [[ "$current" =~ ^[0-9]+$ ]]; then
    current="?"
  fi

  if [ "$current" = "?" ]; then
    printf "  %-30s  quota: %-6s  need: %-6s  " "$label" "???" "$required"
    echo -e "${YELLOW}UNKNOWN${NC} (could not fetch quota)"
    WARNINGS=$((WARNINGS + 1))
  elif [ "$current" -ge "$required" ]; then
    printf "  %-30s  quota: %-6s  need: %-6s  " "$label" "$current" "$required"
    echo -e "${GREEN}OK${NC}"
  else
    printf "  %-30s  quota: %-6s  need: %-6s  " "$label" "$current" "$required"
    echo -e "${RED}INSUFFICIENT${NC}"
    FAILURES=$((FAILURES + 1))
  fi
}

# Check each relevant quota
for family in "G and VT" "Standard" "P"; do
  spot_needed=${REQUIRED_SPOT[$family]:-0}
  od_needed=${REQUIRED_ONDEMAND[$family]:-0}

  # Skip families with no requirements
  if [ "$spot_needed" -eq 0 ] && [ "$od_needed" -eq 0 ]; then
    continue
  fi

  spot_code=${QUOTA_CODES["${family} Spot"]:-""}
  od_code=${QUOTA_CODES["${family} On-Demand"]:-""}

  if [ -n "$spot_code" ] && [ "$spot_needed" -gt 0 ]; then
    check_quota "${family} Spot" "$spot_code" "$spot_needed"
  fi

  if [ -n "$od_code" ] && [ "$od_needed" -gt 0 ]; then
    check_quota "${family} On-Demand" "$od_code" "$od_needed"
  fi
done

# --- Summary ---
echo ""
echo "──────────────────────────────────────────"

if [ "$FAILURES" -gt 0 ]; then
  echo ""
  echo -e "${RED}${BOLD}$FAILURES quota(s) are insufficient.${NC}"
  echo ""
  echo "Request increases at:"
  echo "  https://${AWS_REGION}.console.aws.amazon.com/servicequotas/home/services/ec2/quotas"
  echo ""
  echo "Recommended requests:"

  for family in "G and VT" "Standard" "P"; do
    spot_needed=${REQUIRED_SPOT[$family]:-0}
    od_needed=${REQUIRED_ONDEMAND[$family]:-0}
    [ "$spot_needed" -eq 0 ] && [ "$od_needed" -eq 0 ] && continue

    if [ "$spot_needed" -gt 0 ]; then
      echo "  - '${family} Spot':      request ${spot_needed} vCPUs"
    fi
    if [ "$od_needed" -gt 0 ]; then
      echo "  - '${family} On-Demand': request ${od_needed} vCPUs"
    fi
  done

  echo ""
  echo "After requesting, re-run this script to verify:"
  echo "  ./check-quotas.sh"
  exit 1
fi

if [ "$WARNINGS" -gt 0 ]; then
  echo -e "${YELLOW}${BOLD}All fetchable quotas are OK, but $WARNINGS could not be checked.${NC}"
  echo "You may proceed, but verify manually if needed."
  exit 0
fi

echo -e "${GREEN}${BOLD}All quotas are sufficient. Ready to deploy the pipeline.${NC}"
exit 0
