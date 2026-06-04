# AbuseIPDB

Maintaining Team/Organization: CCCS

Status: In Development

This plugin queries AbuseIPDB for IPv4 and IPv6 reputation information.

## Configuration

Set `ABUSEIPDB_API_KEY` or `ABUSEIPDB_KEY` to an AbuseIPDB API key.

Optional settings:

- `ABUSEIPDB_API_URL`: override the AbuseIPDB API endpoint. Defaults to `https://api.abuseipdb.com/api/v2/check`.
- `ABUSEIPDB_FRONTEND_URL`: override the AbuseIPDB web link. Defaults to `https://www.abuseipdb.com/check`.
- `ABUSEIPDB_MAX_AGE_IN_DAYS`: report lookback window. Defaults to `90`.
- `ABUSEIPDB_VERIFY`: TLS verification setting. Defaults to `true`.

The generic `API_URL`, `FRONTEND_URL`, and `MAX_AGE_IN_DAYS` names are still accepted as fallback values for local compatibility.

## Supported Types

- `ipv4`
- `ipv6`