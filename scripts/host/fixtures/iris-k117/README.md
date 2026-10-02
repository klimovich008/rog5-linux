# Iris k117 test source

These GPL-2.0-only files come from the retained k117 production source after
patch 0171 (repository commit 553ca155). They allow focused tests to replay
0172-0178 without a private Linux checkout or a whole kernel extraction.
Tests compile actual patched functions with inert hardware/API adapters;
they do not load a module or establish phone behavior. The k120 build applies
the entire production series independently to the exact Linux base.
