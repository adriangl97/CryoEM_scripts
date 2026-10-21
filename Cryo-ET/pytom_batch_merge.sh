#!/usr/bin/env bash
# Run in the root of the pytom folder to prepare files to run all pytom commands
# Merge ./submission/*/*.sh into merged.sh (SLURM header, module lines and
# trailing "\" removed), then split the commands into g0.sh and g1.sh.
# g1.sh gets "-g 0" -> "-g 1".
# Refuses to overwrite existing outputs unless run with -f.
set -euo pipefail
shopt -s nullglob
 
force=0
[[ "${1:-}" == "-f" ]] && force=1
 
merged=merged.sh
g0=g0.sh
g1=g1.sh
 
for out in "$merged" "$g0" "$g1"; do
    if [[ -e $out && $force -eq 0 ]]; then
        echo "Error: $out already exists. Rerun with -f to overwrite." >&2
        exit 1
    fi
done
 
files=()
while IFS= read -r f; do
    [[ -n $f ]] && files+=("$f")
done < <(printf '%s\n' ./submission/*/*.sh | sort -V)
 
n=${#files[@]}
if (( n == 0 )); then
    echo "Error: no files matched ./submission/*/*.sh" >&2
    exit 1
fi
half=$(( (n + 1) / 2 ))   # g0 gets the extra command if n is odd
 
# Strip shebang, #SBATCH lines, ml purge / ml pytom-match-pick, CRs,
# leading/trailing blank lines, and the dangling "\" on the last line.
clean() {
    awk '
    { sub(/\r$/, "") }
    /^#!/ || /^#SBATCH/ { next }
    /^[[:space:]]*ml[[:space:]]+(purge|pytom-match-pick)[[:space:]]*$/ { next }
    { lines[++n] = $0 }
    END {
        s = 1; while (s <= n && lines[s] ~ /^[[:space:]]*$/) s++
        e = n; while (e >= s && lines[e] ~ /^[[:space:]]*$/) e--
        if (e >= s) sub(/[[:space:]]*\\[[:space:]]*$/, "", lines[e])
        for (i = s; i <= e; i++) print lines[i]
    }' "$1"
}
 
: > "$merged"
printf '#!/bin/bash\n\n' > "$g0"
printf '#!/bin/bash\n\n' > "$g1"
 
i=0
for f in "${files[@]}"; do
    block=$(clean "$f")
    printf '%s\n\n' "$block" >> "$merged"
    if (( i < half )); then
        printf '%s\n\n' "$block" >> "$g0"
    else
        printf '%s\n\n' "$block" | sed -E 's/-g 0([[:space:]]|$)/-g 1\1/g' >> "$g1"
    fi
    i=$(( i + 1 ))
done
 
chmod +x "$g0" "$g1"
echo "Merged $n files -> $merged; $half commands in $g0, $(( n - half )) in $g1"
