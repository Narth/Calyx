## Safe remote desktop workflow

- Keep Calyx node offline from external networks; allow only LAN.
- Use jump laptop on same LAN; RDP/remote tool restricted to local subnet.
- Enforce firewall rules: block internet egress on Calyx node; allow only necessary local ports.
- No clipboard/file redirection to internet-facing devices; log access times.
- Optional: SSH tunnel within LAN with key auth; no port forwards to WAN.
- Monitor sessions via local telemetry; keep append-only access logs.
