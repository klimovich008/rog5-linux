# GTK 3 Wayland caret publication

Upstream source: GNOME GTK commit
`6a0b360d473f7c546314738c0c8dd9829eb9d3c2` (3.24.52).
`modules/input/imwayland.c` SHA-256:
`7f5bf63f9ad71da36d625d0870692f49bc6351a71757c0f8ac1fcec38c613c37`.
The original source carries its LGPL notice; this patch does not change it.
This is a local downstream patch, not an upstream acceptance claim.

The setter previously only cached a changed rectangle. A large cursor move can
also reset the press gesture, so its release callback need not publish the new
position. Publish through the existing input-method change path after caching:
retrieve current surrounding text, publish content/geometry and commit together.
Keep duplicate suppression, gesture reset and inactive-context caching. Do not
wait for an earlier `done`: a pure acknowledgement does not flush cached geometry.

Run the source-function regression using an unmodified pinned source file and
fresh disk-backed output directories:

```sh
python3 scripts/host/test-gtk-wayland-caret.py --source /PATH/imwayland.c --output /NEW/control --unpatched
python3 scripts/host/test-gtk-wayland-caret.py --source /PATH/imwayland.c --output /NEW/fixed
python3 -O scripts/host/test-gtk-wayland-caret.py --source /PATH/imwayland.c --output /NEW/optimized
```

The control is supposed to exit nonzero; failing behavior remains recorded as
FAIL. The test applies this patch and executes nine extracted production C
functions, with protocol/window/widget-signal adapters. It covers the observed
reset→large move, small moves, unchanged geometry, surrounding text, inactive
contexts, delayed acknowledgements, same-rectangle reentry, and context loss or
disabling during retrieval. Pending preedit/commit application and UTF-8 clipping
are outside this seam. It does not run a GTK widget or prove phone behavior.

The full ARM64 module also needs the exact `gtk/gtkintl.h` and vendored
`modules/input/text-input-unstable-v3.xml`. Generate client-header/private-code
with wayland-scanner. Use the authenticated Arch GTK headers and libraries,
`-fPIC -O2 -shared`, and strict undefined-symbol checking. Do not define
`INCLUDE_IM_wayland`; the shared module must export `im_module_*`. The installed
GDK header layout is flat: an include alias for `gdk/wayland/gdkwayland.h` must
contain the exact installed `gdk/gdkwayland.h` bytes. The mapped VM filesystem
view encodes symlinks and is not a compiler sysroot; use the original materialized
runtime. Keep the existing runtime immutable.

Standalone ARM64 compilation and module discovery are separate from a corrected
interactive VM session. See the dated GTK caret evidence for commands, binary
identity and remaining qualification. A VM-only module override still needs
explicit staging, identity checks and read-only binding before GTK cache creation.
No production package or phone image is replaced by this patch.
