# Reproducible build/boot environment for the xv6-x86 honeypot prototype.
#
# Pinned to Debian bullseye, which ships a gcc/binutils that builds the
# 32-bit (-m32) xv6 kernel and a qemu that provides qemu-system-i386.
# For a fully reproducible pin, replace the tag with a digest, e.g.:
#   FROM debian:bullseye-slim@sha256:<digest>
FROM debian:bullseye-slim

# - build-essential / gcc-multilib: 32-bit xv6 kernel + user programs
# - qemu-system-x86: provides qemu-system-i386 for headless boot
# - perl: xv6 Makefile uses sign.pl and vectors.pl
# - python3: drives the headless boot acceptance tests
# - gdb: kernel debugging (qemu-nox-gdb)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc-multilib \
        qemu-system-x86 \
        perl \
        python3 \
        gdb \
        make \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /xv6

# The repository is bind-mounted at /xv6 at run time (see run.ps1 / run.sh),
# so build artifacts land back in the working tree and stay out of the image.
CMD ["bash"]
