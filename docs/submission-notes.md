# ExecuTV submission notes

The live MCP endpoint is the Application Load Balancer from `infra/` (`terraform output mcp_url`). The bearer token is the `MCP_BEARER_TOKEN` field in the Secrets Manager secret (`terraform output mcp_bearer_secret_arn`). Do not put the token in the Fire TV bundle.

## Judge setup

1. Point MCP Inspector and Claude Desktop at `http://<alb-dns>/mcp` (or HTTPS once a certificate is attached).
2. Send `Authorization: Bearer <token>` and `protocol-version: 2025-11-25`.
3. `initialize` must negotiate `2025-11-25`.
4. Call `get_executive_brief` with a `session_id`.
5. Between judges, `POST /admin/reset-scenario` with the same bearer token. That restores margin to 18.3% and `dec_004` to `PENDING`.

## Evidence still captured on the AWS URL

- MCP Inspector session against the ALB, including the protocol negotiation.
- Claude Desktop connected as a remote MCP server and calling `get_executive_brief`.
- Two consecutive runs of the three-minute script with no code change between them.
- The demo video recorded from that URL, not from localhost.

`scripts/demo_dry_run.py` is the local stand-in for the two-run check until those images are pushed.

## Repository access

Keep the GitHub repository private. Grant `testing@devpost.com` and the named reviewers: `chris-trag`, `knmeiss`, `giolaq`, `anishamalde`, `mosesroth`, `emersonsklar`.

## Tear-down

After judging, `terraform destroy` in `infra/` so the NAT gateway and RDS instance stop billing.
