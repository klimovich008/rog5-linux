# Bounded Wayland debug records

Upstream Wayland 1.26.0, commit
`87cc8a8728a923fc57938faa81ba0e74f34ecdc7`, is the source baseline.
The unmodified `src/connection.c` SHA-256 is
`2db8435dfd051ee3f8b7fae5c37eb35d22c21cc158fc21f77bcf3d4b920a4f1f`.
Upstream [source](https://github.com/wayland-mirror/wayland/blob/87cc8a8728a923fc57938faa81ba0e74f34ecdc7/src/connection.c)
retains its MIT license and copyright. This does not choose a repository-wide
license or establish equality with every distribution packaging patch.

`wl_closure_print()` writes string arguments without escaping embedded newlines
or quotes. The GTK caret VM emitted surrounding text `line-50\nline-51` as two
physical log lines. Its next genuine cursor request was `(92, 1070, 0, 20)`, but
the strict host oracle had already rejected the split record. Guessing boundaries
in the host is unsafe: document text can imitate a closing quote followed by a
complete protocol request. The original VM result remains FAIL.

The patch escapes string arguments where their boundaries are still known:
quotes, backslashes, newline, carriage return, tab, other C0 bytes and DEL.
Null remains `nil`; ordinary printable ASCII and UTF-8 bytes are preserved.
This changes diagnostic formatting only, not protocol wire data. Do not decode
escaped strings into new evidence records. Existing line/log limits remain;
expansion beyond a limit must fail explicitly rather than truncate or pass.

The test compiles the actual production `WL_ARG_STRING` case and its helper.
It verifies exact bytes and feeds output through the unchanged caret parser,
including hostile-looking document strings and genuine neighboring requests.
It does not execute the full Wayland client, KMS, EGL or the phone.

```sh
python3 scripts/host/test-wayland-debug-strings.py \
  --source /absolute/unmodified/connection.c --output /new/control-directory
python3 scripts/host/test-wayland-debug-strings.py \
  --source /absolute/unmodified/connection.c --output /new/patched-directory --patched
```

The control must fail; fixed and Python `-O` runs must pass. Missing exact source
cannot become a passing source test. The compiler and case processes use the
existing repository deadline/process-group supervisor. VM activation requires
separate exact-library identity, ABI/dependency checks and a scoped read-only
runtime override; this patch itself activates nothing and grants no phone
operation authority.
