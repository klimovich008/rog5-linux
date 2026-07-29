FROM --platform=linux/amd64 docker.io/library/fedora:44@sha256:89f61a124414261868224666aa7fb8df1b78397a53623774bdfb105d1612b48b AS ca-bootstrap

RUN printf '%s  %s\n' \
      00411c197b16f659945fba3c2f970a26030f56eef5d445c913cb59a089c813b9 \
      /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem \
      | sha256sum -c -

FROM --platform=linux/amd64 docker.io/library/ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

ARG APT_CACHE_NAMESPACE=default
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C

COPY --from=ca-bootstrap \
    /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem \
    /etc/ssl/certs/ca-certificates.crt
COPY manifests/kernel-builder-packages.tsv \
    /usr/share/rog5/kernel-builder-packages.tsv

RUN --mount=type=cache,id=rog5-kernel-builder-apt-lists-${APT_CACHE_NAMESPACE},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=rog5-kernel-builder-apt-archives-${APT_CACHE_NAMESPACE},target=/var/cache/apt/archives,sharing=locked \
    printf '%s  %s\n' \
      00411c197b16f659945fba3c2f970a26030f56eef5d445c913cb59a089c813b9 \
      /etc/ssl/certs/ca-certificates.crt \
      | sha256sum -c - \
 && printf '%s  %s\n' \
	      9dce7979f2b55e0f56c6dd803986d127107e5a7ead15cd69e780aebaccacc101 \
	      /usr/share/rog5/kernel-builder-packages.tsv \
	      | sha256sum -c - \
 && printf '%s\n' \
	      'Types: deb' \
	      'URIs: https://snapshot.ubuntu.com/ubuntu/20260728T000000Z' \
	      'Suites: noble noble-updates noble-backports noble-security' \
	      'Components: main universe restricted multiverse' \
	      'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg' \
	      'Check-Valid-Until: no' \
	      > /etc/apt/sources.list.d/ubuntu.sources \
 && rm -f /etc/apt/apt.conf.d/docker-clean \
 && if ! apt-get -qq -o APT::Update::Error-Mode=any update \
      > /tmp/apt-update.log; then \
      cat /tmp/apt-update.log >&2; exit 1; \
    fi \
 && if ! apt-get install -y -qq --no-install-recommends \
      bc bison build-essential ca-certificates ccache clang cpio device-tree-compiler \
      dwarves flex git gnupg iproute2 kmod libarchive-tools libelf-dev libssl-dev lld llvm make nftables \
      python3 qemu-user-static rsync wireguard-tools zlib1g-dev \
      > /tmp/apt-install.log; then \
      cat /tmp/apt-install.log >&2; exit 1; \
	    fi \
 && printf 'package\tversion\n' > /tmp/installed-packages.tsv \
 && dpkg-query -W -f='${db:Status-Abbrev}\t${binary:Package}\t${Version}\n' \
	      | awk -F '\t' '$1 == "ii " { print $2 "\t" $3 }' \
	      | LC_ALL=C sort >> /tmp/installed-packages.tsv \
 && cmp /usr/share/rog5/kernel-builder-packages.tsv \
      /tmp/installed-packages.tsv \
 && rm -f /tmp/apt-install.log /tmp/apt-update.log \
      /tmp/installed-packages.tsv /var/cache/apt/*.bin \
      /var/cache/ldconfig/aux-cache \
 && find /var/log -type f -delete

LABEL org.rog5.kernel-builder.snapshot="20260728T000000Z" \
      org.rog5.kernel-builder.package-lock-sha256="9dce7979f2b55e0f56c6dd803986d127107e5a7ead15cd69e780aebaccacc101" \
      org.rog5.kernel-builder.ca-bootstrap-sha256="00411c197b16f659945fba3c2f970a26030f56eef5d445c913cb59a089c813b9"

WORKDIR /workspace
