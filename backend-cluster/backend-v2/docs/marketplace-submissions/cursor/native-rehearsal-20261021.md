# Cursor native rehearsal — 2026-10-21 UTC

This verifies local native-Agent compatibility with the hosted connector. It is
not a marketplace install, accepted submission or completed Cursor IDE agent
journey. At this earlier run both publisher submissions were unsent. Later community publication, native desktop OAuth/query/preview and retained authorization are recorded in the [2026-10-22 follow-through](./native-desktop-rehearsal-20261022.md).

## Package and client provenance

- Root `.cursor-plugin/marketplace.json` indexes only `beancount-mcp`, sourced
  from this directory's `official/` package. Its existing three files are
  unchanged. The official [multi-plugin layout](https://github.com/cursor/community-plugins)
  resolves the monorepo package shape; actual publisher intake remains untested.
- The unmodified [template validator](https://github.com/cursor/plugin-template/blob/46216072ac5750f782f95bb325b4d12b7c3ae9c9/scripts/validate-template.mjs)
  passes against a fresh fixture and the actual repository. Node 24.16.0; only
  the expected no-hooks warning. Published schemas inspected at
  `190d28736eff128ec94f502a22c7fe0c4b56cd37`; no separate JSON Schema engine was run.
- Cursor IDE 3.24.18, stable Apple Silicon, build
  `be4c9e5350d77747b42cd467cbd3370a753d4640`, was downloaded through the official
  vendor stable download. Disk-image verification, deep/strict code-signature
  verification and Gatekeeper acceptance as a notarized Developer ID all pass.
  A fresh task profile opens the workbench, but native accessibility inspection
  subsequently times out. No IDE agent conversation is claimed.
- Cursor Agent starts at `2026.09.15-d2fe57e` and updates through its own normal
  updater to `2026.10.19-6bbf2c4` before the successful rehearsal. The native
  account sign-in succeeds. No model override is supplied; the run uses `Auto`.

## Actual local plugin and OAuth flow

The interactive Agent loads the real nested package with `--plugin-dir` and
`--workspace`. Its interactive `/mcp list` shows the Beancount plugin and initiates
native discovery/DCR. The separate `mcp list` management subcommand does not
load this local plugin in the observed invocation; it is not used as proof.

Default discovery requests broader scopes, so that grant is not approved. A
private QA-only copy uses Cursor's documented [static OAuth configuration](https://prod.cursor.com/docs/mcp):
the public client ID from its own native registration plus
`ledger.read ledger.write`. This is an explicit QA configuration difference;
the public URL-only package contains no embedded client ID, credentials or
automatic approvals. No unsupported scope field is invented.

The operator authorizes only the dedicated synthetic ledger. Native callback
completion succeeds and the Agent reports **44 tools, 8 resources and 4 prompts**
against `https://beancount.io/api-gateway/mcp`. No admin or offline-access scope
is granted; no refresh token is issued. Account IDs, native registration IDs,
tokens and private ledger commit identifiers remain outside public evidence.

## Query, preview and state evidence

The native Agent's bounded Ask run completes at 19:09 UTC with exit 0 in 187.1
seconds, using sandbox mode and a task-local MCP tool allowlist. It discovers the
pinned ledger identifier, context and source names before calling ledger tools.

```sql
SELECT account, sum(position)
WHERE account = "Assets:Cash"
GROUP BY account
```

The structured query returns **49.75 USD**, both before and after the preview.
The Agent calls `appendLedgerText` exactly once, with `dry_run: true` and
`allowInvalid: false`, for a balanced synthetic transaction: Cash −1.00 USD and
Coffee +1.00 USD. The response reports one proposed directive, a displayed diff,
zero errors before/after, no new errors and an empty `wrote` array. A later query
finds no booked preview transaction. No actual write or commit is requested.

The full structured `checkLedger` results immediately before and after the
preview are identical, including the latest commit and entry counts: 12 Open,
16 Transaction and 1 Balance; zero errors. These fields are confirmed by an
external trace reviewer. The native model's text view only displays the short
check summary, so it is not credited with seeing every structured field.

Concurrent QA activity changed an unrelated sidecar during the run. The Agent
reads all 88 main-source lines before the preview, but its post-read covers only
the first 5 and last 8 lines; those match. A separate full read at 19:21 UTC finds
93 lines after another concurrent QA change and no preview payee/note. Therefore
whole-file equality across the entire session is **not** claimed. The identical
immediate check results, balance and empty write result are the preview's state
evidence. Server/deployment revision is not exposed by the host and remains
unavailable.

Large file results retain full `structuredContent`, while the host's text view
shows only an item-count summary; this causes extra paginated reads. It is a
host visibility limitation observed here, not proof that structured content is
missing from the server response.

## Cleanup and remaining gates

At 19:22 UTC the exact temporary client completes the provider's client-specific
end-session flow; the page confirms “Your sign-out with Cursor was successful.”
The matching local MCP credential entry is removed, other local entries are
verified unchanged, and the task's interactive Agent is stopped. The provider's
client-only branch preserves other sessions. No refresh capability exists;
already-issued self-contained JWT access remains valid until its 20:03:29 UTC
expiry rather than being immediately invalidated by this cleanup.

Remaining: finish the IDE journey owned by w1/m34/t003, obtain action-time
approval for official Publisher Terms, send the separate official/community
submissions, and verify actual review/publication and gallery discovery. The
root index and native Agent rehearsal clear preparation substeps only.
