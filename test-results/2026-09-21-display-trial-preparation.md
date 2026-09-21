# Isolated display-trial preparation — September 21

The user authorized one isolated trial package and read-only phone health/identity
checks. Signing, claims, boot, flashing, target mutation and physical trials remain
excluded. No Ready request or physical countdown is active.

Starting source is `d0f1830ac2e595aa0fcf08d07451771f2a60afae`, tree
`66d0c2a28aa4a41917ec0164bbc98c487bf7cf47`. Implementation remains82679758;
its previously recorded132-suite qualification was not rerun.

[Machine-readable results](2026-09-21-display-trial-preparation.json) retain
commands, durations, script identities and copied artifact hashes. In a new
private host directory,25 files totaling35,813,759bytes were copied from the
verified Image, composedDTB and22-file payload plus manifest. Each source was
stream-hashed with stable metadata; each destination was independently hashed.
Result PASS_ISOLATED_INGREDIENT_COPY in0.166980s. No rebuild, signing, boot image,
admission or claim was produced. This is the ingredient portion of the package;
the real controller/input binding remains incomplete, with runtime UNBOUND.

The existing pinned transport's host-only preflight ran as ordinaryUID1000 while
holding the existing display coordinator lock. Its source identity matched the
retained clean transport checkout. The exact approved USB path was absent;
BLOCKED_READONLY_PHONE_CHECK in0.111053s. No SSH/phone command was invoked, no
route or USB state changed, and no broader device search bypassed that guard.
The connection prompt remains pending. This observation does not establish that
the phone is powered off or unhealthy.

The previous Pro answer established historical input-lock incompatibility and
allowed reuse of the inert ingredients. The next review concerns a concrete
producer for the now-authorized successor package, using actual current source
and real data. Normalized test fixtures must not become deployable private inputs;
no old pin, seal, consumed claim, accepted image or historical evidence is replaced.

Physical results remain NOT RUN; S06/R01 and earlier VM failures remain unchanged.
The useful efficiency step was reusing the retained compiled artifacts: no kernel,
Denial or unchanged integration test rerun was needed for this preparation.
