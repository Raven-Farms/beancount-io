# Docker MCP Catalog preparation

This is a preparation artifact for the hosted Beancount.io service at `https://beancount.io/api-gateway/mcp`. It does not package the service or a ledger engine in a Docker image. The three files under `servers/beancount-io/` are intended for the same directory in [docker/mcp-registry](https://github.com/docker/mcp-registry).

The entry uses Streamable HTTP, OAuth and dynamic tool discovery. `tools.json` is deliberately `[]`; its contents are discovered after the user authorizes the connection. `beancount-io.personal_access_token` and `BEANCOUNT_IO_PERSONAL_ACCESS_TOKEN` are Docker credential identifiers, not credentials or instructions to publish a key. The [MCP guide](../../mcp.md) explains scopes, the hosted-ledger boundary and confirmation requirements.

## Verified preparation

On 2026-10-21, the actual upstream Go commands passed against Docker MCP Registry revision `49b643ce3fc73e6ee80bb962719b6e2990e3d397`, using Go 1.26.4 and the existing Prettier 3.8.1. From a checkout of that upstream revision, copy this `servers/beancount-io/` directory into its `servers/`, then run:

```sh
go run -mod=readonly ./cmd/validate --name=beancount-io
go run -mod=readonly ./cmd/catalog beancount-io
```

The corresponding Taskfile commands are `task validate -- --name=beancount-io` and `task catalog -- beancount-io`. Generation writes `catalogs/beancount-io/catalog.yaml`. The authored registry entry uses an `oauth` list; the generated gateway catalog converts it to `oauth.providers`. These formats are related, but are not interchangeable.

The validator checked formatting, the public icon, remote transport and dynamic OAuth configuration. It did not authenticate or execute a ledger tool. Its license check explicitly skips remote entries without a source project. Beancount.io repository code uses MIT; the generated local test catalog's default owner/license metadata does not establish the hosted service's source license.

## Runtime and submission gates

Use the dedicated QA account with synthetic ledgers for the OAuth/tool rehearsal.
`DOCKER_CONFIG` alone does not isolate this gateway version's home-directory
catalog database; use uniquely named temporary catalog records and remove only
those records afterward. Keep credentials in the runtime secret store.

On 2026-10-21, digest-verified standalone v0.44.1, using a temporary OCI catalog
and `DOCKER_MCP_IN_CONTAINER=1`, completed OAuth discovery and dynamic client
registration. The first browser attempt had the wrong account and was canceled;
its Chrome-blocked cancellation redirect was not bypassed or counted as a
successful callback. Supported cleanup confirmed no OAuth token was present.

A later rehearsal established the dedicated QA browser session and selected
only its intended synthetic ledger on the real consent page. Authorization
explicitly requested `ledger.read ledger.write` through
`oauth authorize beancount-io --scopes 'ledger.read ledger.write'`; omitting
`--scopes` had requested only identity access, which would not prove ledger
access. No grant was approved or token obtained. The callback process has since
exited, so restart that same narrowly scoped native flow after approval. The
remaining gate is the specific temporary access decision, then authenticated
discovery, one known read, a supported `dry_run` preview, unchanged-state and
callback verification, followed by review. Docker Desktop and QA sign-in are
not the current gates. Consent alone does not establish an authorized journey.

Docker MCP Gateway v0.44.1 is a prerelease, published 2026-09-23. Its CLI has changed since the registry contribution guide: `catalog import` is absent, while current catalog commands support conversion from legacy catalogs. Inspect the chosen version's help and use its supported catalog/profile flow. The gateway README documents `DOCKER_MCP_IN_CONTAINER=1` for feature checks outside Docker Desktop; this alone does not prove that every OAuth service is available. No persistent Docker Desktop configuration is part of this preparation.

For this version, a successful legacy-catalog conversion produced an empty
server list with the generated fixture. The supported
`catalog server add <temporary-oci-reference> --server file://<entry-file>`
path accepted a single-server entry with the gateway's `oauth.providers`
shape and made the server available for OAuth. Local entry files must resolve
under `~/.docker/mcp/catalogs`. Inspect the actual catalog contents rather than
treating command exit status as proof that the server was imported; no remote
catalog was published by this local operation.

The [remote contribution guide](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md#-adding-a-remote-mcp-server) requires these three files and OAuth testing, followed by a Docker-team-reviewed upstream pull request. No submission is represented by this directory. Use the private credential-sharing channel linked by Docker only when the operator proceeds with review; never attach credentials to a commit, pull request, or public board.

## Primary references

- [Remote entry example](https://github.com/docker/mcp-registry/blob/49b643ce3fc73e6ee80bb962719b6e2990e3d397/servers/linear/server.yaml)
- [Registry validation command](https://github.com/docker/mcp-registry/blob/49b643ce3fc73e6ee80bb962719b6e2990e3d397/cmd/validate/main.go)
- [Registry catalog command](https://github.com/docker/mcp-registry/blob/49b643ce3fc73e6ee80bb962719b6e2990e3d397/cmd/catalog/main.go)
- [Gateway server-entry specification](https://github.com/docker/mcp-gateway/blob/main/docs/server-entry-spec.md)
- [Gateway standalone usage](https://github.com/docker/mcp-gateway#usage)
- [Gateway v0.44.1 prerelease assets](https://github.com/docker/mcp-gateway/releases/tag/v0.44.1)
