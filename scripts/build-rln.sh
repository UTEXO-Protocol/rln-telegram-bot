#!/usr/bin/env bash
# Build the exact supported RLN revision in a dedicated local checkout.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
revision="$(cat "$root/rln-revision")"
source_dir="$root/.rln"
if [[ ! -d "$source_dir/.git" ]]; then
    git clone --filter=blob:none \
        https://github.com/UTEXO-Protocol/rgb-lightning-node.git "$source_dir"
fi
if [[ -n "$(git -C "$source_dir" status --porcelain)" ]]; then
    echo "Refusing to change a dirty RLN checkout: $source_dir" >&2
    exit 1
fi
git -C "$source_dir" fetch --depth=1 origin "$revision"
git -C "$source_dir" checkout --detach "$revision"
cd "$source_dir"
exec cargo build --locked --release --bin rgb-lightning-node
