"""Standalone GPU verification.

Run after installing the CUDA build of torch to confirm the setup actually
sees the GPU. Deliberately avoids importing project config — torch may be the
only thing installed yet when this is run as a fresh-install sanity check.
"""

from __future__ import annotations

import subprocess
import sys


def _print_nvidia_smi() -> None:
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        print(result.stdout if result.returncode == 0 else f"nvidia-smi failed:\n{result.stderr}")
    except FileNotFoundError:
        print("nvidia-smi not found on PATH — skipping (fine on a CPU-only machine).")


def main() -> int:
    print("=== nvidia-smi ===")
    _print_nvidia_smi()

    print("\n=== torch / CUDA ===")
    try:
        import torch
    except ImportError:
        print("torch is not installed yet. Run scripts/install_deps.ps1 (or .sh) first.")
        return 1

    print(f"torch version:   {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available:  {cuda_available}")
    if cuda_available:
        print(f"CUDA device:     {torch.cuda.get_device_name(0)}")
        print(f"CUDA capability: {torch.cuda.get_device_capability(0)}")
    else:
        print("Running on CPU. EMBED_DEVICE=auto will select cpu automatically in that case,")
        print("but if a GPU was expected, check the driver and the torch install step.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
