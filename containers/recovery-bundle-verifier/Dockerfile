FROM --platform=linux/arm64 docker.io/library/alpine:3.24@sha256:e7a1a92a5bfeee40966aea60f0796b0e7917cc35591542701834f03a68fa3d18

RUN apk add --no-cache \
      binutils=2.45.1-r1 \
      build-base=0.5-r4 \
      file=5.47-r2 \
      fortify-headers=3.0.1-r2 \
      gcc=15.2.0-r5 \
      g++=15.2.0-r5 \
      make=4.4.1-r4 \
      musl-dev=1.2.6-r2 \
      openssl=3.5.7-r0 \
      openssl-dev=3.5.7-r0 \
      openssl-libs-static=3.5.7-r0 \
      patch=2.8-r0 \
      zlib-dev=1.3.2-r0 \
      zlib-static=1.3.2-r0 \
 && printf 'localhost\n' >/etc/hostname \
 && printf '127.0.0.1 localhost\n::1 localhost\n' >/etc/hosts \
 && : >/var/log/apk.log

WORKDIR /workspace
