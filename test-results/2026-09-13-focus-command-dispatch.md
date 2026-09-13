# Early window-command dispatch — 2026-09-13

**The scheduling defect is fixed and the ARM64 build passes, but the VM still
fails app switching.** A single changed-binary treatment again visibly returns
to Mousepad while native keyboard focus stays with Foot. The correction is not
sufficient to resolve the runtime failure. This is offline ARM64 VirGL evidence;
all phone physical rows remain NOT RUN, and historical S06/R01 remain FAIL.

## Correction and executable regression

Patch `0009-service-window-commands-before-background-yield.patch` services up
to 64 decoded commands immediately after the platform-event batch, before the
two later background time-slice yields. It applies the authentication boundary
first and discards commands while locked. Native-plugin and Wayland routing
share the original implementation. `drain(..count)` preserves the remainder.
Ordinary window management and engine replacement retain their full final drain;
64 is the early-batch bound, not a new limit for an entire iteration.

The regression extracts the actual pinned event-loop segment, wire/runtime queue
methods and command-routing blocks. Engine, clock, background services,
authentication and native endpoints are adapters. Before correction, six required
properties fail and two controls pass. After correction, all nine cases pass:
input work exceeding the slice, slow settings, a non-service iteration, retained
commands without new messages, locked discard, ordinary focus exactly once,
early-batch remainder/order, native-plugin routing, and final replacement drain
with more than 64 commands plus newly decoded final messages.

Review caught a regression in the first draft: removing the shared full drain
would have lost final commands during bundle reload and topology replacement.
That draft was corrected before the ARM64 build. The final test executes the
retained production late-dispatch block. An initial fixture compilation failure
from private adapter methods was also corrected; its log remains private.

These tests cover the two post-message yields. Earlier loop continuations,
including output reconfiguration and waiting for reload scanout completion, are
outside their proof. They do not establish whole-loop starvation freedom or the
cause of the previously observed VM failure.

## Results and identities

| Executed check | Result | Wall seconds |
| --- | --- | ---: |
| Final baseline extracted unit | 2 PASS, 6 expected FAIL | 0.603 build + 0.002 execution |
| Final corrected extracted unit | 9 PASS | 0.604 build + 0.002 execution |
| All nine patches applied to pinned Denial | PASS | 0.247 |
| ARM64 release compositor, Flutter feature | PASS | 212.575 |
| One changed-binary app-switch VM | FAIL | 102.908 |
| Frozen active host tier | 92 PASS, 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 137.532 |

Starting repository commit `d751f7365fef949da0fb859490bf19fdc7184872`, tree
`5bd53ef7cee16f51f3a2fcf65a22345e582d5eea`. Frozen source/build/test commit
`2ba6b1826d55f22aece5d202ec017448d050b37b`, tree
`692bf47123d1635f097d535275bdaf92ff8868e8`.

Pinned Denial remains `85b2303e2f09ae7b7b993641f90061a200f03d53`. All nine patches
were checked and applied in filename order to a fresh archive of that exact
commit. The private manifest hashes all 701 resulting source files. Patch 0009
SHA256 is `28a6c2ab628d173ffce458cbb60887a924874ff674845cd0f517721fe08f8d46`.
New ARM64 binary SHA256 is
`02212bcd6dbf4827e0a7226b94c1cdb929f0c16df5d51b6bd3413f93d3cbbf9c`.
The previous native binary and all previous evidence remain retained.

The native build used the retained immutable builder image, locked/offline Cargo,
one build job, two CPUs, 3 GiB memory/no swap and a 600-second deadline. It built
the compositor and its Rust engine-binding crate; the external Flutter engine,
shell AOT, assets and generic kernel were reused. The build log reports no
warnings. Minimum observed free disk was 3,460,390,912 bytes. Container removal
was verified after build and VM execution.

The VM input check verifies 34 retained inputs: only the native binary changed.
The same kernel, runtime, corrected AOT, engine, inspected launcher reference,
observer and resource limits were used. No phone kernel rebuild or new phone
candidate was generated. Exact build/test/VM commands, source and artifact hashes,
raw-result identities, and JSON/JUnit report hashes are in the
[qualification JSON](2026-09-13-focus-command-dispatch-qualification.json).
Three declared optional subchecks remain SKIPPED separately. The active tier ran
once on the frozen source with two workers and a 1 GiB/no-swap limit. It does not
include the manually invoked exact-Denial-source regression or the VM. Peak
active-tier memory was 343.6 MiB. Final metadata validation passed: five checker
cases (0.913 s), eight status cases (0.080 s), artifact inventory (0.066 s),
generated status (0.040 s), and diff whitespace (0.028 s). Commands and results
are retained in the private `metadata-result.json`.
No new GitHub CI execution is claimed.

The treatment produced 85 frames and 85 page flips without reported render
errors. Direct inspection confirms Mousepad, Foot's prompt, then Mousepad again.
Raw client logs show only Mousepad enter at 61.961101 seconds, Mousepad leave at
70.286706, and Foot enter at 70.483020. No later focus transfer occurs. The second
return to Foot is NOT RUN. Shell exit, owned launcher cleanup and container
removal pass; those results do not replace app-switch FAIL.

Final serial SHA256:
`1ec2f5908e59aceee9291fc68f020938e5e8dec0ff693e2e14e583ae7713e642`.
Final initramfs SHA256:
`1adef959dd13b23e18fca61f6a0a9b78cad02a7e187b4b2f444a3b29ee97e2b0`.

## Remaining boundary and next experiment

Source review disproved a wire enum/channel mismatch: `FocusWindow = 3` and
`denial/wire/to_native` agree across Dart, generated Rust and the schema.
Two unresolved boundaries remain especially relevant:

- The slide paints the incoming app before `AnimationStatus.completed` invokes
  `completeAdjacentWindowSwitch()` and the bridge. A visible target does not
  prove that its focus request was sent. The bridge currently discards asynchronous
  send errors.
- Smithay routes `set_focus` through keyboard grabs. Denial then publishes
  activation without checking the resulting native focus. The retained trace
  contains no supporting popup/grab evidence, so this remains a hypothesis.

The next smallest useful experiment needs bounded correlated markers for Dart
animation completion/target ID/send result, native enqueue/drain, and native
focus before/after with grab state. Do not repeat this unchanged VM or increase
its timeout. The corrected scheduling path can remain; another speculative
scheduler rewrite is not justified by this failed treatment.

Changed source files: patch 0009, `scripts/host/test-window-command-dispatch.py`,
`tools/denial-modifier-tests/window-dispatch-fixture.rs`, `docs/development.md`,
and `docs/development-lessons.md`. Evidence changes add this report and its JSON,
append one fixture artifact set, update the current artifact pointer and canonical
project status, and regenerate only the current-state header. Contracts,
historical current-state content and all prior 502 artifact sets are preserved.
Private evidence: `/home/deck/.local/state/rog5-focus-dispatch-20260913-r1`.
No phone, signing, admission, claim, protected-storage or installed-image operation
occurred. The long-term phone goal remains incomplete.
