FROM ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bc bison build-essential ca-certificates clang cpio device-tree-compiler \
      dwarves flex git gnupg iproute2 kmod libarchive-tools libelf-dev libssl-dev lld llvm make nftables \
      python3 qemu-user-static rsync wireguard-tools zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
