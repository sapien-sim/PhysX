# Unified build image for the SAPIEN PhysX forks, used by BOTH:
#   - internal artifact builds (git.sudoai.cc, sapien-developers/physx)
#   - public artifact builds  (github.com, sapien-sim/PhysX)
#
# Why manylinux_2_28 (AlmaLinux 8, glibc 2.28):
#   libPhysXGpu_64.so ships as a data file inside the sapien wheel. Built on
#   Ubuntu 22.04 it required GLIBC >= 2.34, which blocks the wheel from
#   honestly carrying the manylinux_2_28 tag (PEP 600). Building everything
#   here caps every artifact at glibc 2.28 - internal and public zips alike.
#
# Why CUDA 12.8 (not the 11.8 of sapien-build-env:3.8):
#   keeps sm_100/sm_120 (Blackwell) coverage identical to the previous
#   Ubuntu-22.04 artifact builds. CUDA 12.8 officially supports RHEL 8, which
#   is exactly what this base image is.
#
# Python: the manylinux base ships every maintained CPython (3.10-3.14).
# Python 3.15 is compiled from source here (manylinux-style: source build
# with the image toolchain, rpath'd, self-contained) so the image supports
# 3.15 from day one. Default is 3.15.0rc3: final is not on python.org yet
# and rc3 is ABI-frozen (identical cp315 ABI to the final). Bump the
# default to 3.15.0 once final is downloadable.
#
# How it is built: the "Build Build-Env Image" workflow in this repo
# (.github/workflows/docker-image.yml) builds this Dockerfile on a
# GitHub-hosted runner and stages the result on GHCR
# (ghcr.io/sapien-sim/physx-build-env:<tag>). This repo is the image's
# single source of truth (the internal artifact CI consumes the same image).
#
# Publishing to Docker Hub (what the public/internal artifact CIs pull) is
# done manually by the maintainer:
#   docker pull ghcr.io/sapien-sim/physx-build-env:1.0
#   docker tag  ghcr.io/sapien-sim/physx-build-env:1.0 fxiangucsd/sapien-physx-build-env:1.0
#   docker login && docker push fxiangucsd/sapien-physx-build-env:1.0

FROM quay.io/pypa/manylinux_2_28_x86_64:latest

# 3.15.0rc3 (ABI-frozen) until 3.15.0 final is on python.org
ARG PYTHON315_VERSION=3.15.0rc3

# build tools + CPython build dependencies + GL headers (physx links GLVND)
RUN yum install -y gcc-toolset-11 git make zip unzip \
      mesa-libGL-devel \
      openssl-devel zlib-devel libffi-devel bzip2-devel sqlite-devel \
      readline-devel xz-devel ncurses-devel gdbm-devel libuuid-devel \
    && yum clean all

# cmake and ninja ship with the base image via its own pipx
# (/opt/_internal/pipx). Do NOT install cmake via pipx here: pipx refuses
# to replace a venv it did not create in this session and the install fails.

# Python 3.15 from source (Alma 8 system OpenSSL 1.1.1 satisfies CPython)
RUN curl -fsSL "https://www.python.org/ftp/python/3.15.0/Python-${PYTHON315_VERSION}.tgz" -o /tmp/python.tgz \
    && tar -xzf /tmp/python.tgz -C /tmp \
    && cd /tmp/Python-${PYTHON315_VERSION} \
    && export PATH=/opt/rh/gcc-toolset-11/root/usr/bin:$PATH \
    && ./configure --prefix=/usr/local/python3.15 --enable-shared \
         --with-ensurepip=install \
         LDFLAGS="-Wl,-rpath,/usr/local/python3.15/lib" \
    && make -j"$(nproc)" && make install \
    && ln -sf /usr/local/python3.15/bin/python3.15 /usr/local/bin/python3.15 \
    && ln -sf /usr/local/python3.15/bin/pip3.15 /usr/local/bin/pip3.15 \
    && /usr/local/bin/python3.15 --version \
    && rm -rf /tmp/python.tgz /tmp/Python-${PYTHON315_VERSION}

# CUDA 12.8 compiler + runtime headers/static lib only (no driver, no full
# toolkit) via NVIDIA's RHEL8 repo. Write the repo file directly so we do not
# depend on dnf-utils' config-manager plugin.
RUN curl -fsSL -o /etc/yum.repos.d/cuda-rhel8.repo \
      https://developer.download.nvidia.com/compute/cuda/rhel8/x86_64/cuda-rhel8.repo \
    && dnf install -y cuda-nvcc-12-8 cuda-cudart-devel-12-8 cuda-cudart-static-12-8 cuda-cuobjdump-12-8 \
    && dnf clean all

ENV CUDA_PATH=/usr/local/cuda-12.8
ENV PATH="${CUDA_PATH}/bin:/usr/local/python3.15/bin:/opt/_internal/pipx/bin:/root/.local/bin:/opt/rh/gcc-toolset-11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ENV LD_LIBRARY_PATH="/opt/rh/gcc-toolset-11/root/usr/lib64:/opt/rh/gcc-toolset-11/root/usr/lib:${LD_LIBRARY_PATH}"

# sanity: the toolchain must resolve from the final image PATH
RUN cmake --version && python3.15 --version && nvcc --version
