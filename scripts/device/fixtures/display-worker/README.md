# Offline worker source fixtures

These four baseline modules are sanitized retained sources, never a live entry
point. Worker credential/host-key/serial constants are redacted; receiver and
network addresses use documentation values, with unit topology/profile/anchor
strings normalized. Preserve their exact bytes for the historical comparisons.
The account name in host policy is unchanged. No credential, input lock, claim
registry or complete private consultation packet is included.

The wrapper reuses the existing ten-source cohort assembler, its actual test
module, and the exact public `scripts/host/release-acceptance.py`. It constructs
only the source packet consumed by the retained tests. Patch 0012 composes the
reviewed worker/deployed-source binding, actual acceptance identity reader and
finalizer corrections. `finalization.patch` reverses only the final correction
to reconstruct the intermediate worker for two historical negative controls;
it is not a second patch to apply after 0012. All composed bytes and strict
forward/reverse application are checked before execution.

The original 58 cases exercise actual source with explicit external fixtures: 22 binding
and route-ownership cases, 20 real Git/process-lifetime cases, and 16 finalizer
cases including two old-code failure controls. The finalizer tests extract the
actual function and pidfd starter, not a duplicate model. Source authentication
is a synthetic checked-loader boundary using the real bounded source reader;
network, root role, credentials and device effects remain inert adapters.

Real-child checks require ordinary UID1000, Python pidfd APIs, a host kernel
supporting pidfd process-group signaling, Git and `/usr/bin/prlimit`. Unsupported
hosts fail; these mandatory tests do not silently skip. One descendant fixture
uses a separate ordinary-user subreaper process. Production code never changes
process-wide SIGCHLD/subreaper policy and does not use Python `preexec_fn`.

The worker retains its pidfd through leader reap and group cleanup. Finalization
attempts all remaining owned closes before propagating the first selected error.
A handled timeout is not a propagating error. Raw descriptor closes with uncertain
outcomes are not retried against a potentially reused number; uncertainty remains
failure. This does not promise safety at arbitrary bytecode interruptions,
resource-acquisition gaps, escaped process groups or host power loss.

The original ten-path source pins and private-worker refusal remain unchanged.
No admission, runtime pin/seal, signed artifact or claim is issued. The original
runtime remains UNBOUND; phone and VM results are NOT RUN.

Patch 0013 adds an optional fixed five-source loader after 0012. Its 33 cases
exercise actual admission input/schema/digest definitions and all five source
modules, bringing this mandatory suite to 91 cases. The wrapper reconstructs
admission from the existing fixture and patches 0010/0011; the retained test
receives only its required source packet. No private review packet is committed.

The bootstrap must already authenticate the session, admission implementation,
its dependencies and INPUTS_SHA. Module/function identity checks preserve that
trust; they do not establish it. The fixture supplies the input bytes and anchor,
preloaded dependency graph, decoder and two historical custody rows. It never
issues a lock, seal, claim or runtime binding. Full initialization still refuses
at the unchanged health boundary; the default path still refuses the worker.

The loader checks all source files before executing captured compiled code,
rechecks before cache publication, shares one worker between transport/logger,
and refuses reuse after a validation failure. Failed partial attachment detaches
its own references. Failure at the first check of an already attached handle can
leave references in place, but guarded reuse still refuses the failed handle.
Neither the import filter nor these tests claim to sandbox hostile Python or
qualify the unreviewed bootstrap/health dependency graph.
