# Cold-boot caller source fixtures

These are inert source inputs for `scripts/device/test-production-cold-boot.py`.
Do not import or execute their private module entrypoints. The test extracts
function/class definitions and selected constants, with explicit fixtures for
credentials, claims, custody, route policy and all external effects. It executes
the actual controller, caller, publication and fallback validation definitions.
Passing these checks creates no live authority. Private runtime remains UNBOUND;
physical and VM execution remain NOT RUN.

The public wrapper reuses the existing production-cohort assembler and applies
0010 to the existing caller fixtures. It creates a temporary packet containing
only the nine required caller/downstream sources and ten exact cohort sources,
then strictly applies 0011 through the retained tests. It does not retain the
large adviser packet, private path map or counterexample logs in Git.

Seven additional downstream fixtures came from the reviewed original packet.
Four private host-path strings in `live-driver.py.txt`'s `PATHS` assignment are
replaced with inert paths in this new fixture. The definitions loader excludes
that assignment; all other AST nodes are identical. The private original and
sealed evidence remain unchanged. `source-pins.json` records original and new
identities. Placeholder owners, boot identifiers and SSH destinations remain
placeholders; the all-zero rejected UUID remains unchanged.

The three test files are byte-identical to the reviewed proposals. Their hash
chain remains intact. The public wrapper runs exactly 28 base cases, 28 owned
publication cases and 14 finalization cases, in serial batches of at most four.
Each batch has a 90-second deadline and stays in the repository runner's process
group. The repository manifest sets the total deadline and serial resource
policy. Scratch is under the checkout's disk-backed `build` directory.

The second-close negative controls were executed separately against the previous
proposal and retained privately. The corrected source must preserve the original
trial FAIL and cancellation while permitting only already-authorized fallback
recovery with a valid exclusion witness. Missing/tampered witness, uncertain
closure and consumed recovery phases remain refusals. SIGKILL, process death,
power loss and interruptions outside the scoped publication boundary are not
qualified by these tests. No kernel, image, candidate or claim is produced.
