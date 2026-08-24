#!/usr/bin/env bash
# POSIX parity for install_deps.ps1 (for later Linux/WSL/CI use).
#
# torch is deliberately absent from requirements.txt. It still gets installed
# transitively (docling -> torchvision -> torch), which matters: torchvision's
# compiled extensions are ABI-matched to a specific torch version, so we let
# pip's resolver pick that pairing first from the default index (a CPU-only
# build), then swap ONLY torch for the CUDA build of that *same* version from
# PyTorch's own index. Installing the CUDA build first and requirements.txt
# second does NOT work: pip's resolver silently re-installs a different
# (CPU-only, version-mismatched) torch to satisfy docling's constraint,
# clobbering the CUDA build.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
# See the matching comment in install_deps.ps1: this index name goes stale as
# new CUDA/torch versions ship. Check https://pytorch.org/get-started/locally/
# (or probe https://download.pytorch.org/whl/<cuXXX>/torch/ directly) if Step 2 fails.
TORCH_INDEX_URL="https://download.pytorch.org/whl/cu130"

if [ ! -x "$PYTHON" ]; then
    echo "No .venv found at $PYTHON. This project expects an existing .venv - see README.md." >&2
    exit 1
fi

echo "=== Using interpreter: $PYTHON ==="
"$PYTHON" --version

echo
echo "=== Step 0: upgrade pip ==="
"$PYTHON" -m pip install --upgrade pip

echo
echo "=== Step 1: requirements.txt (resolves a CPU-only torch as a side effect) ==="
if ! "$PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"; then
    echo "ERROR: requirements.txt install failed - see output above." >&2
    exit 1
fi

echo
echo "=== Step 2: swap torch for the CUDA build of the SAME version ==="
TORCH_VERSION="$("$PYTHON" -c "import torch; print(torch.__version__.split('+')[0])" | tr -d '[:space:]')"
if [ -z "$TORCH_VERSION" ]; then
    echo "WARNING: could not detect an installed torch version - installing latest CUDA torch with no pin." >&2
    "$PYTHON" -m pip install torch --index-url "$TORCH_INDEX_URL"
else
    echo "Detected torch $TORCH_VERSION from Step 1. Reinstalling that exact version from $TORCH_INDEX_URL ..."
    # --force-reinstall is required: PEP 440 treats a bare "==2.13.0" requirement
    # as satisfied by ANY local version (e.g. an already-installed "2.13.0+cpu"),
    # so a plain install silently no-ops instead of swapping in the CUDA-tagged
    # build. --no-deps avoids touching the already-correct torchvision/etc.
    if ! "$PYTHON" -m pip install "torch==$TORCH_VERSION" --index-url "$TORCH_INDEX_URL" --force-reinstall --no-deps; then
        echo "WARNING: no CUDA build of torch==$TORCH_VERSION was found on $TORCH_INDEX_URL." >&2
        echo "Check https://pytorch.org/get-started/locally/ for the current index-url for this torch version and re-run:" >&2
        echo "  $PYTHON -m pip install torch==$TORCH_VERSION --index-url <correct-url>" >&2
        echo "torchvision was installed against torch $TORCH_VERSION - do not install a DIFFERENT torch version here, it will break torchvision's compiled extensions." >&2
        exit 1
    fi
fi

echo
echo "=== Step 3: crawl4ai browser setup (downloads Chromium via Playwright) ==="
CRAWL4AI_SETUP="$PROJECT_ROOT/.venv/bin/crawl4ai-setup"
if [ -x "$CRAWL4AI_SETUP" ]; then
    "$CRAWL4AI_SETUP" || echo "WARNING: crawl4ai browser setup did not complete cleanly. Run '$PROJECT_ROOT/.venv/bin/crawl4ai-doctor' for diagnostics. Only live web crawling needs this." >&2
else
    echo "WARNING: crawl4ai-setup not found in .venv/bin - check 'pip show crawl4ai'." >&2
fi

echo
echo "=== Step 4: GPU verification ==="
"$PYTHON" "$PROJECT_ROOT/scripts/verify_gpu.py"

echo
echo "=== Done. ==="
