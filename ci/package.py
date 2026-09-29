#!/usr/bin/env python3
"""Package PhysX build outputs into the zips SAPIEN consumes.

Canonical zip contract (layout normalized regardless of upstream renames):
  linux-release.zip            include/ + bin/linux.clang/release/*.a
  linux-checked.zip             include/ + bin/linux.clang/checked/*.a
  linux-so.zip                 libPhysXGpu_64.so at the zip root
  windows-release.zip          include/ + bin/win.x86_64.vc143.mt/release/*.lib
  windows-dll.zip              PhysXGpu_64.dll at the zip root
  macOS-universal-release.zip  include/ + bin/universal/release/*.a
"""
import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

CONTRACT = {
    "linux": {
        "release": ("linux-release.zip", "bin/linux.clang/release"),
        "checked": ("linux-checked.zip", "bin/linux.clang/checked"),
    },
    "windows": {
        "release": ("windows-release.zip", "bin/win.x86_64.vc143.mt/release"),
    },
    "macos": {
        "release": ("macOS-universal-release.zip", "bin/universal/release"),
    },
}

GPU_LIB = {
    "linux": "libPhysXGpu_64.so",
    "windows": "PhysXGpu_64.dll",
}

# GPU-side intermediates ship inside the shared GPU library; consumers link
# only the CPU-side static libs, so these are excluded to match the contract.
INTERMEDIATE_LIB_PATTERNS = ("*Gpu_static_64", "*CudaContextManager_static_64")


def _lib_files(physx_root: Path, pattern: str):
    # the packman-generated layout puts outputs under physx/bin/... while the
    # standalone CMake entry puts them under physx/lib/bin/... — scan both
    for base in (physx_root, physx_root / "lib"):
        yield from base.glob(f"bin/**/{pattern}")


def find_static_libs(physx_root: Path, config: str, libext: str):
    for f in _lib_files(physx_root, f"*{libext}"):
        if not (f.is_file() and f.parent.name == config):
            continue
        if any(fnmatch.fnmatch(f.stem, p) for p in INTERMEDIATE_LIB_PATTERNS):
            continue
        yield f


def add_tree(zf: zipfile.ZipFile, base: Path, arc_prefix: str, skip):
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(base).as_posix()
        if any(fnmatch.fnmatch(rel, p) for p in skip):
            continue
        zf.write(f, f"{arc_prefix}/{rel}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--physx-root", required=True, help="the physx/ source root")
    ap.add_argument("--platform", required=True, choices=["linux", "windows", "macos"])
    ap.add_argument("--config", required=True, choices=["release", "checked"])
    ap.add_argument("--dist", required=True, help="output directory for zips")
    args = ap.parse_args()

    root = Path(args.physx_root)
    dist = Path(args.dist)
    dist.mkdir(parents=True, exist_ok=True)

    include = root / "include"
    if not include.is_dir():
        sys.exit(f"error: {include} not found")

    libext = ".lib" if args.platform == "windows" else ".a"
    zip_name, arc_dir = CONTRACT[args.platform][args.config]
    libs = list(find_static_libs(root, args.config, libext))
    if not libs:
        sys.exit(f"error: no {libext} files found for config {args.config}")

    out = dist / zip_name
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        add_tree(zf, include, "include", skip=["*.xml", "*.bat", "*.sh"])
        for lib in libs:
            zf.write(lib, f"{arc_dir}/{lib.name}")
    print(f"wrote {out} ({out.stat().st_size // (1 << 20)} MB) with {len(libs)} libs:")
    for lib in libs:
        print(f"  {arc_dir}/{lib.name}")

    if args.config == "release":
        gpu_name = GPU_LIB[args.platform]
        candidates = [c for c in _lib_files(root, gpu_name) if c.is_file()]
        gpu = next((c for c in candidates if c.parent.name == "release"), None)
        if gpu is None:
            gpu = candidates[0] if candidates else None
        if gpu is None:
            print(f"note: {gpu_name} not found; skipping GPU zip")
        else:
            gpu_zip_name = {"linux": "linux-so.zip", "windows": "windows-dll.zip"}[args.platform]
            out = dist / gpu_zip_name
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(gpu, gpu_name)
            print(f"wrote {out} ({out.stat().st_size // (1 << 20)} MB) with {gpu_name} at zip root")


if __name__ == "__main__":
    main()
