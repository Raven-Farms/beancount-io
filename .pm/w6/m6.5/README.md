# w6 · m6.5 — Distribute the Beancount.io customer skills as one suite

**Worker:** worker1 **Goal:** A user discovers, installs and updates the customer ledger workflows through one versioned Beancount.io suite entry on each supported host. **Status:** in progress (t001–t002 done; Hermes t005 blocked; publication and other independent work continue)

## Scope and decisions

- Explicit owner request, 2026-10-22: create **m6.5** and execute the suite consolidation described in this conversation. The decimal milestone ID is explicitly requested; every task keeps the same ID and path.
- Preserve completed [m6](../done/m6/README.md) and the thirteen immutable standalone ClawHub release histories. Consolidate distribution and version management while preserving individual skill triggers, responsibilities and canonical source files.
- Reuse existing Claude Code/Codex suite manifests. Confirm the real ClawHub/OpenClaw/Hermes package contracts before selecting a format; no new runtime dependency is authorized.
- Ship directly to main under the owner's standing instruction. Existing protected publishing credentials may be used; do not create new credentials, alter retained OAuth grants, send external messages or bypass host scanners.
- Existing Hermes init policy and filtered-search findings remain [039](../blocked/039.md) and [040](../blocked/040.md); this milestone records their actual effect on a supported suite route.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](done/t001.md) | Confirm supported suite formats and existing ownership — **DONE** | 45m | — |
| [t002](done/t002.md) | Build one versioned customer-suite artifact — **DONE** | 60m | t001 |
| [t003](t003.md) | Publish the suite through the protected release workflow | 45m | t002 |
| [t004](t004.md) | Verify native OpenClaw suite install and update | 45m | t003 |
| [t005](t005.md) | Verify the supported Hermes suite route — **BLOCKED** | 45m | t002 |
| [t006](t006.md) | Preserve legacy standalone installation compatibility | 30m | t002 |
| [t007](t007.md) | Adoption surface | 30m | t003, t004, t005, t006 |
| [t008](t008.md) | Simplify | 20m | t007 |
| [t009](t009.md) | Test coverage | 45m | t007, t008 |
| [t010](t010.md) | Closeout | 15m | t009 |

## Definition of done

- One versioned suite package is accepted and publicly available through the selected supported registry route, built from canonical customer skill sources with matching provenance and MIT-0 licensing.
- A single native OpenClaw install exposes all thirteen intended workflows; supported discovery, update and transition from individual installs are verified in an isolated profile.
- Hermes has an exercised suite setup/update route using the same source inventory, with its native policy restrictions explicitly retained and no force-install or scanner bypass. An unavailable upstream route remains open with its unblock condition rather than being called delivered.
- Existing Claude Code and Codex suite installs remain valid, and legacy standalone ClawHub releases stay available without continuing routine fragmented publication.
- Suite-first public documentation agrees with exact exercised commands and host limits; meaningful regression tests and owning-package checks pass.
- Standing closing tasks are complete; /pm moves all tasks and this milestone into their done locations with consistent links and statuses.

## Source + Goal linkage

- **Source:** owner direction after m6 closeout, 2026-10-22: consolidate scattered skill distribution into one suite, then explicit “pm for m6.5 and execute it”.
- **Goal linkage:** **A3 — Community & distribution:** one product entry and release history. **A2 — Frictionless onboarding:** install and update the suite once. **A1 — Agent-native accounting:** sibling workflow handoffs retain their contracts and discovery.
- **Expected outcome:** a newcomer selects Beancount.io once and obtains the supported ledger workflows without assembling thirteen separately versioned installations.
- **Why now:** m6's verified standalone releases establish working source content and host baselines; the owner now selects suite distribution for subsequent publication. Reuse existing suite packaging and preserve that completed history. Adoption surface is included because install, update, discovery and release guidance change.

## Out of scope

- New accounting behavior, reworking skill descriptions/routing, MCP marketplace submissions, deleting existing listings, new credentials, paid platform fees, and unsolicited upstream outreach.

## Hermes admission finding — 2026-10-22 UTC

The selected suite artifact is supported for ClawHub publication and OpenClaw content loading. Hermes's complete-suite route has the actual upstream admission gates in [t005](t005.md#blocked--2026-10-22-utc). Native publication, OpenClaw checks, compatibility guidance and regression tests continue; m6 remains done. No additional owner input is needed for these independent steps.
