# [Server Submission]: Beancount.io hosted MCP

## GitHub Repository URL

https://github.com/bex-co/beancount-io/tree/main/backend-cluster/backend-v2

Setup README for this remote connector:
https://github.com/bex-co/beancount-io/blob/main/backend-cluster/backend-v2/docs/marketplace-submissions/cline/README.md

## Logo Image

https://raw.githubusercontent.com/bex-co/beancount-io/main/backend-cluster/backend-v2/docs/marketplace-submissions/cline/logo-400.png

## Installation Testing

- [ ] I have tested that Cline can successfully set up this server using only the README.md and/or llms-install.md file
- [ ] The server is stable and ready for public use

These confirmations remain unchecked until the actual Cline installation and
synthetic QA rehearsal is recorded. Do not submit this preparation as a tested
installation.

## Additional Information

Beancount.io exposes one existing hosted endpoint:
`https://beancount.io/api-gateway/mcp`, Streamable HTTP with OAuth. It queries and
edits hosted Beancount ledgers, including BQL, reports, files and bank imports.
It does not read local ledger files. Canonical official registry identity:
`io.beancount/beancount`; the official record and authorization guide are linked
from the setup README. Users approve their own ledger permissions. Use a
dedicated QA account and synthetic ledger for review; credentials are supplied
only through the platform's supported private channel if requested.

Fresh native Cline version/date, OAuth, known query, supported write-preview
result and deployment revision availability must be added after the rehearsal.
No publication or review receipt yet.
