# Dependency install for Prabhu Sahayogi.
#
# torch is deliberately absent from requirements.txt. It still gets installed
# transitively (docling -> torchvision -> torch), which matters: torchvision's
# compiled extensions are ABI-matched to a specific torch version, so we let
# pip's resolver pick that pairing first from the default index (a CPU-only
# build), then swap ONLY torch for the CUDA build of that *same* version from
# PyTorch's own index. Installing the CUDA build first and requirements.txt
# second does NOT work: pip's resolver silently re-installs a different
# (CPU-only, version-mismatched) torch to satisfy docling's constraint,
# clobbering the CUDA build - this is exactly what happened on the first
# implementation of this script, caught by inspecting the install log rather
# than assuming success.
#
# Run from anywhere; this script calls .venv's python.exe directly by path,
# so the venv does not need to be activated first.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
# PyTorch's CUDA index folder name (cu124, cu128, cu130, ...) changes as new
# CUDA/torch versions ship and old ones stop being updated - cu124 turned out
# to be frozen at torch 2.6.0 when this was last checked (2026-08-22), so
# cu130 was the one actually carrying a win_amd64/cp313 build of the torch
# version requirements.txt resolves. If Step 2 below reports no matching
# distribution, check https://pytorch.org/get-started/locally/ (or probe
# https://download.pytorch.org/whl/<cuXXX>/torch/ directly) for the current name.
$TorchIndexUrl = "https://download.pytorch.org/whl/cu130"

if (-not (Test-Path $Python)) {
    Write-Error "No .venv found at $Python. This project expects an existing .venv - see README.md."
    exit 1
}

Write-Host "=== Using interpreter: $Python ===" -ForegroundColor Cyan
& $Python --version

Write-Host "`n=== Step 0: upgrade pip ===" -ForegroundColor Cyan
& $Python -m pip install --upgrade pip

Write-Host "`n=== Step 1: requirements.txt (resolves a CPU-only torch as a side effect) ===" -ForegroundColor Cyan
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
if (-not $?) {
    Write-Error "requirements.txt install failed - see output above."
    exit 1
}

Write-Host "`n=== Step 2: swap torch for the CUDA build of the SAME version ===" -ForegroundColor Cyan
$TorchVersion = (& $Python -c "import torch; print(torch.__version__.split('+')[0])").Trim()
if (-not $TorchVersion) {
    Write-Warning "Could not detect an installed torch version - installing latest CUDA torch with no pin."
    & $Python -m pip install torch --index-url $TorchIndexUrl
} else {
    Write-Host "Detected torch $TorchVersion from Step 1. Reinstalling that exact version from $TorchIndexUrl ..."
    # --force-reinstall is required: PEP 440 treats a bare "==2.13.0" requirement
    # as satisfied by ANY local version (e.g. an already-installed "2.13.0+cpu"),
    # so a plain `pip install torch==$TorchVersion` silently no-ops instead of
    # swapping in the CUDA-tagged build. --no-deps avoids touching the
    # already-correct torchvision/etc. that pip resolved in Step 1.
    & $Python -m pip install "torch==$TorchVersion" --index-url $TorchIndexUrl --force-reinstall --no-deps
    if (-not $?) {
        Write-Warning "No CUDA build of torch==$TorchVersion was found on $TorchIndexUrl."
        Write-Warning "Check https://pytorch.org/get-started/locally/ for the current index-url for this torch version and re-run:"
        Write-Warning "  $Python -m pip install torch==$TorchVersion --index-url <correct-url>"
        Write-Warning "torchvision was installed against torch $TorchVersion - do not install a DIFFERENT torch version here, it will break torchvision's compiled extensions."
        exit 1
    }
}

Write-Host "`n=== Step 3: crawl4ai browser setup (downloads Chromium via Playwright) ===" -ForegroundColor Cyan
$Crawl4aiSetup = Join-Path $ProjectRoot ".venv\Scripts\crawl4ai-setup.exe"
if (Test-Path $Crawl4aiSetup) {
    & $Crawl4aiSetup
    if (-not $?) {
        Write-Warning "crawl4ai browser setup did not complete cleanly."
        Write-Warning "If a proxy/AV is blocking the Chromium download, run '.venv\Scripts\crawl4ai-doctor.exe' for diagnostics."
        Write-Warning "Only live web crawling needs this step - the rest of the app is unaffected."
    }
} else {
    Write-Warning "crawl4ai-setup.exe not found in .venv\Scripts - check pip show crawl4ai."
}

Write-Host "`n=== Step 4: GPU verification ===" -ForegroundColor Cyan
& $Python (Join-Path $ProjectRoot "scripts\verify_gpu.py")

Write-Host "`n=== Done. ===" -ForegroundColor Green
