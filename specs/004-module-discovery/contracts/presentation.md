# F-04 Reference Consumer and Presentation Contract

**Status**: Proposed JSON-consumer agreement, not a Next.js implementation or
screen accessibility result. The future console consumes the same public
contract client-side and remains statically exportable.

## Input and State Dimensions

The reference consumer reads only HTTP JSON/description examples, not Hosting
or provider types. Its output is a bounded semantic presentation record:
module identity, distinct textual state labels, support scope, observation/
assessment times, reason/corrective text, logical reading order and action state.
No raw markup, style, DOM, provider implementation or server-side UI runtime.

| Condition | Required text / behavior |
| --- | --- |
| Inclusion absent in complete inventory | Not included; custom package inclusion/registration, rebuild/redeploy/restart |
| Inclusion unknown in partial inventory | Inclusion unknown; inspect distribution records, do not invent absence |
| Included, unregistered | Included, not registered; register in a rebuilt custom host |
| Registered, disabled | Disabled; change validated selection and restart if desired |
| Unsupported or unverified | Unsupported / support unverified; hide action, retain explanatory inventory |
| Supported fixture operation | Fixture-tested only; never label production/native-client supported |
| Initializing or not-ready | Distinct temporary state, safe reason; supported action disabled |
| Stopping/stopped | Non-invocable, regardless of prior ready observation |
| Unknown future state or meaning | Unknown/uninterpretable, non-invocable; safe known inventory retained |
| Missing dependency/binding | Specific reason, no usable integration; unrelated operations remain independent |

Display inclusion, registration, enablement, support and readiness separately
instead of choosing one green/red module badge. Readiness text is explicitly
observed/assessed, not a claim of continuous monitoring. Empty is valid only
after a compatible successful response with a genuinely empty known array.
It is not equivalent to missing source, partial/unknown inventory or denial.

## Refresh and Action Rules

| View state | Data handling | Action eligibility |
| --- | --- | --- |
| Loading, no prior response | Explicit loading state | None |
| Refreshing with prior data | Mark retained observation non-current until success | None |
| Compatible successful observation | Present all independent dimensions/times | Only known supported usable operations, subject to separate permission |
| Denied (401/403) | Explicit denied state; discard sensitive retained inventory when access is lost | None |
| Transport/503/invalid response | Explicit failure; previously visible safe data may remain labelled stale | None |
| Receipt age over 30 seconds | Mark retained result stale | None until a successful new read |
| Genuine empty | Explicit empty state and completeness information | None |

Use a monotonically increasing client refresh generation and local monotonic
receipt timer. A response from an older attempt never replaces the latest
attempt, even if it completes later or contains a higher lifecycle revision.
Within the accepted current lifecycle, an older revision cannot regress state;
new lifecycle identity resets that comparison only for the latest refresh
generation. New reads show the reported assessment time; they do not invent a
new health assessment. Never infer freshness from wall-clock equality alone.

Unsupported actions are hidden. Known supported but unavailable, unknown,
loading or stale actions are visible only where useful and disabled with
textual explanation. Unknown operations and incompatible response versions
are never offered. Inspection permission is not execution permission: the
reference fixture carries an independent permission input to demonstrate that
management-read alone cannot enable an execution action. Future action APIs
must still authorize at execution time; no action is actually executed here.

## Semantic Accessibility and Safe Text

Each module, state, observation time and reason has a descriptive textual label
and deterministic reading order. Any future invocable action has an accessible
name; disabled explanations must be available without focus on an unfocusable
control, hover, color or animation. Loading/error/status changes have explicit
semantic status text. Repeated labels retain module/operation context.

Keyboard/assistive-technology review of the reference semantic output must find
all information in logical reading order without pointer-only affordances.
This is evidence of the presentation agreement, not proof of browser focus,
ARIA behavior, contrast, responsive layout or actual WCAG 2.2 AA compliance.
Those must be implemented and tested in SPEC-11/later rendered screens.

Treat all text as inert text. Do not interpolate strings as HTML/Markdown,
execute links/scripts, or interpret unknown fields as action definitions.
Unknown safe descriptive fields may be ignored; malformed required data or
unknown authorization/action meanings cannot silently become success.

## Corrective Guidance and Scope

Use closed host templates, not provider exception messages. Disabled bundled
choices require validated configuration and explicit restart. Missing custom
packages/registration require package references, rebuild/redeploy and restart.
Not-ready/failed states require configuration/runtime investigation; changing
configuration does not imply automatic data rollback. Discovery performs none
of those changes and supplies no live enable/install controls.

Reference examples always identify fixture support and observation/permission
limits. No real console, production provider, package-client compatibility,
category conformance or network/TLS certification is claimed.
