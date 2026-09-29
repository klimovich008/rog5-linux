# GodShell evaluation

Evaluated source: `Raulgooo/godshell` commit `4530e0fdee0dc98bea20b268273d7a3e438ceb37`.

## What it contributes

GodShell is an eBPF observability daemon and TUI. It records process, file-open, exit, and network-connect events into SQLite and can send structured context to an OpenRouter-backed LLM. The repository already embeds ARM64 BPF objects, so the architecture is relevant to this phone-server.

It is useful for the project as:

- an acceptance workload for BTF/eBPF support;
- a way to retain short-lived process/network history;
- a possible structured diagnostics source for a remote agent;
- a concrete reason to enable tracepoints, kprobes, uprobes, BPF JIT, and BTF in the new kernel.

## Why it is not installed yet

- Upstream requires kernel 5.8+ and `/sys/kernel/btf/vmlinux`.
- The current 5.4.210 baseline has BPF/JIT/uprobes but no BTF vmlinux.
- The Arch target uses systemd, but Linux 7.1 and its BTF runtime have not passed the live recovery gate.
- It is explicitly experimental, and its own test-strategy document describes several recommended tests rather than completed coverage.
- Kernel observability does not grant safe access to email/CV data; those are separate application permissions.

## Integration gate

After a 7.x kernel passes hardware tiers 1–5:

1. build GodShell from the pinned source for ARM64;
2. run its Go unit tests;
3. verify BPF verifier output and all four tracepoints;
4. harden its systemd service and run the UI client unprivileged;
5. keep the daemon API on a local Unix socket;
6. store the OpenRouter key in a root-readable secret store, never in Git;
7. benchmark idle CPU, RAM, SQLite growth, and battery impact;
8. disable SSL/memory probes by default because they can capture sensitive data.

GodShell can improve diagnostics, but it should not be on the critical boot path.
