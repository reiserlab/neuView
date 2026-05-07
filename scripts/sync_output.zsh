#!/usr/bin/env zsh
# Sync output/ to a target directory, removing orphan files in target,
# but never touching dotfiles (.files / .dirs) that exist only in target.
#
# Usage: scripts/sync_output.zsh [-n] <target-dir>
#   -n   dry run (show what would change without modifying anything)

set -euo pipefail

dry_run=()
if [[ ${1:-} == "-n" ]]; then
    dry_run=(--dry-run --verbose)
    shift
fi

if [[ $# -ne 1 ]]; then
    print -u2 "Usage: $0 [-n] <target-dir>"
    exit 1
fi

target=$1
source_dir=output

if [[ ! -d $source_dir ]]; then
    print -u2 "Source directory '$source_dir' does not exist"
    exit 1
fi

mkdir -p -- "$target"

# 'P .*'      protects top-level dotfiles in target from --delete
# 'P .*/**'   protects everything inside a dotted directory (e.g. .cache/x)
rsync -a --delete "${dry_run[@]}" \
    --filter='P .*' \
    --filter='P .*/**' \
    -- "$source_dir/" "$target/"
