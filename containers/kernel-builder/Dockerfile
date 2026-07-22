FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bc bison build-essential ca-certificates clang cpio device-tree-compiler \
      dwarves flex git libelf-dev libssl-dev lld llvm make python3 rsync zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
