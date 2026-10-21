#!/usr/bin/env bash
# Run MemBrain-seg on every refined tomogram, two at a time (one per GPU).
# Each GPU works through its own queue sequentially.
#
# Usage:
#   DRY_RUN=1 ./membrain_queue.sh            # print the expanded commands only
#   nohup ./membrain_queue.sh > membrain_run.log 2>&1 & # actual run

set -o pipefail
shopt -s nullglob

CKPT=/nethome/adrian/software/membrain/MemBrain_seg_v10_beta.ckpt
GPUS=(0 1)
LOGDIR=membrain_logs
DRY_RUN=${DRY_RUN:-0}

TOMOS=(../Tomograms/*_refined/tomograms/*.mrc)
if (( ${#TOMOS[@]} == 0 )); then
    echo "No tomograms matched ../Tomograms/*_refined/tomograms/*.mrc" >&2
    exit 1
fi
echo "Found ${#TOMOS[@]} tomograms"
mkdir -p "$LOGDIR"

run_queue() {
    local gpu=$1; shift
    local tomo tag
    for tomo in "$@"; do
        # Log name: <refined dir>_<tomogram basename>, avoids clashes between dirs
        tag="$(basename "$(dirname "$(dirname "$tomo")")")_$(basename "$tomo" .mrc)"
        local cmd=(membrain segment
                   --tomogram-path "$tomo"
                   --ckpt-path "$CKPT"
                   --rescale-patches)

        if [[ $DRY_RUN == 1 ]]; then
            echo "CUDA_VISIBLE_DEVICES=$gpu ${cmd[*]}"
            continue
        fi

        echo "[$(date '+%F %T')] GPU $gpu start:  $tomo"
        if CUDA_VISIBLE_DEVICES=$gpu "${cmd[@]}" > "$LOGDIR/$tag.log" 2>&1; then
            echo "[$(date '+%F %T')] GPU $gpu done:   $tomo"
        else
            echo "[$(date '+%F %T')] GPU $gpu FAILED: $tomo (see $LOGDIR/$tag.log)" >&2
        fi
    done
}

# even indices -> GPU 0, odd indices -> GPU 1
Q0=(); Q1=()
for i in "${!TOMOS[@]}"; do
    if (( i % 2 == 0 )); then Q0+=("${TOMOS[i]}"); else Q1+=("${TOMOS[i]}"); fi
done

run_queue "${GPUS[0]}" "${Q0[@]}" &
run_queue "${GPUS[1]}" "${Q1[@]}" &
wait
echo "[$(date '+%F %T')] All done"
