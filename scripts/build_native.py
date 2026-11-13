"""Build the optional C++ scorer with an available local toolchain."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def build():
    source = ROOT / "native" / "page_scorer.cpp"
    suffix = ".dll" if sys.platform == "win32" else ".dylib" if sys.platform == "darwin" else ".so"
    target = ROOT / "backend" / "native" / f"thesis_scorer{suffix}"
    if target.exists() and target.stat().st_mtime >= max(source.stat().st_mtime, Path(__file__).stat().st_mtime):
        print(f"C++ scorer is up to date: {target.name}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which(os.getenv("CXX", "g++")) or shutil.which("clang++")
    if compiler:
        command = [compiler, "-std=c++17", "-O3", "-shared", str(source), "-o", str(target)]
        if sys.platform == "win32":
            command += ["-static-libgcc", "-static-libstdc++"]
        else:
            command += ["-fPIC"]
        subprocess.run(command, check=True)
    elif shutil.which("cmake"):
        build_dir = ROOT / "native" / "build"
        subprocess.run(["cmake", "-S", str(source.parent), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"], check=True)
        subprocess.run(["cmake", "--build", str(build_dir), "--config", "Release"], check=True)
    else:
        raise RuntimeError("Install a C++17 compiler (MinGW-w64, Clang, or MSVC with CMake).")
    print(f"Built C++ scorer: {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--optional", action="store_true")
    args = parser.parse_args()
    try:
        build()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Native scorer unavailable: {exc}", file=sys.stderr)
        if not args.optional:
            sys.exit(1)
        print("Continuing with the Python scorer.")
