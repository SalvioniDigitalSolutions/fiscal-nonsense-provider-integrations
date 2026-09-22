# Security and private data

Report suspected vulnerabilities or accidentally exposed credentials privately to info@fiscalnonsense.com. Do not include the credential itself in the initial message; arrange a secure exchange.

Never commit API keys, passwords, customer inputs, customer quotes, identity documents or private contracts. If a secret was committed, revoke/rotate it immediately; deleting the file does not erase Git history. Ask maintainers to coordinate history cleanup where needed.

Public CI runs offline with read-only repository permissions and no provider secrets. Do not use `pull_request_target` to execute contributor code. An approved integration must receive credentials separately in a server-side deployment, with restricted access and an explicit production allowlist.
