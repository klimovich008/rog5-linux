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

## Boot composition boundary

The actual `build-persistent-root-standalone-initramfs.sh` was invoked with
`EXPECTED_RELEASE=7.1.4-rog5-production`, an intentionally absent base and a new
output path. It exited1 in0.006111s with
`FAIL invalid expected standalone kernel release`. No base was read or output
created. Source SHA256:
`1fa12860f9bddf716378647ece849e53f48593e726be8b11bd97aa3f3c2a92d1`.
This establishes an incompatibility between the existing builder and the selected
production release, not a failed full build or authority to broaden all guards.
Its refresh additionally requires four UFS and fifteen power/USB modules; the
14-module display payload is a different closure.

`build-native-wifi-persistent-trial-initramfs.py --successor --refresh-userspace`
can refresh current trial/radio userspace, but explicitly leaves kernel/init/storage
composition separate. `repack-android-boot-v3.sh` can wrap compatible inputs with
an unsigned AVB footer (`algorithm NONE`); it does not supply that missing base
or directly package the target DTB. Historical136f's raw outer Android image
contains a signed inner Image/DTB/initramfs bundle. Its historical preparation
command therefore must not be run as an unsigned shortcut. No signing command ran.

The next Pro follow-up must include these exact builder sources and counterexample
before adapting composition. The existing `rog5-trial-producer-r1` consultation
process is live but remains at browser navigation with submission/Pro selection
unconfirmed. Bounded page inspection and the previous owned-tab JavaScript recovery
both timed out; neither means the process is terminal. No duplicate request or
weaker model/API fallback was started. The owned-tab memory guard remains active.

## Exact production release-name correction

The release-name allowlist now additionally accepts the exact string
`7.1.4-rog5-production`; the existing legacy format and all module/base checks
are retained. This is a routine validation correction, separate from the complex
source/input and complete boot composition still awaiting Pro. No production
ramdisk, input lock, seal, signature or execution authority was created.

The new real-archive regression failed against the previous builder in0.091392s.
After the initial correction, all four composition methods passed in0.489005s
under Python-O. They exercise the real shell/cpio builder, confirm the selected
release is embedded and the exact current shutdown script is included, preserve
legacy archive checks and reject five other/malformed release names before input.
The module-refresh fixture additionally passes with both legacy and production
release names; its wrong-vermagic, unsafe and changed-inventory refusals remain.
That suite passed in0.092223s. Artifact effects use tiny disposable nonbootable
archives; no kernel modules execute. The applicable active tier will run once
on the frozen result; previous132-suite evidence is not claimed for this edit.

A final adversarial case caught line-oriented grep accepting a production release
followed by a newline and extra data (failed-before0.123921s). The production
addition now uses shell string equality; the legacy regex is unchanged. The
final four composition methods pass in0.484806s, including six invalid production
or malformed release values. Final builder SHA256
`cbeb8453b8a4a2b4e4ec7edca20be0721bf11b3b90cb224ac661064527c0c2fb`.
This follow-up supersedes the intermediate builder hash without deleting its
failing/passing evidence. No other module function changed after its focused pass.
