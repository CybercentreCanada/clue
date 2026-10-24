# RIPE ASN Names

Status: In Development

Enriches `asn` selectors with the autonomous system name and country code from
the [RIPE NCC ASN names dataset](https://ftp.ripe.net/ripe/asnames/asn.txt).

Adapted from [clue-plugins commit
6adc2ca](https://github.com/CybercentreCanada/clue-plugins/commit/6adc2ca51eb7718faf36fe2223e8700766615a0a).

Values may be supplied as either a bare integer (for example, `15169`) or with
the conventional prefix (for example, `AS15169`). Whitespace and prefix case
are normalized. Unknown, malformed, and out-of-range ASNs return no matches.

A match returns one context annotation with the registered name and, when
available, country code. `include_raw=true` also returns the numeric ASN, name,
country code, and dataset source. `no_annotation=true` and `limit=0` suppress
annotations without changing the match count.

## Dataset and configuration

The dataset is fetched directly from RIPE while the Docker image is built. It
is not checked into this repository, and lookups do not make network requests.
Rebuild the image to refresh the dataset; the plugin's GitHub workflow disables
the Docker build cache to download a fresh snapshot on each build.

| Environment variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `ripe-asn-names` | Plugin application name. |
| `CLASSIFICATION` | `TLP:CLEAR` | Classification of returned data. |
| `ASN_DATA_PATH` | `asn.txt` beside `app.py` | Path to the local RIPE dataset, loaded at startup. |

If the dataset cannot be read, the plugin logs the error and returns no matches.

For local development, download the dataset before starting the interactive
harness (run from the repository root):

```bash
curl --fail --location https://ftp.ripe.net/ripe/asnames/asn.txt \
  --output plugins/ripe_asn_names/asn.txt
make test-plugin ripe_asn_names
```

The downloaded file is ignored by Git and Docker; the image always uses the
snapshot downloaded during its own build.

## Tests

Tests use synthetic records and do not require the dataset or network access:

```bash
cd api
poetry run python -m pytest ../plugins/ripe_asn_names -c ../plugins/pytest.ini
```

## Changelog

### 0.0.1

- Initial release of RIPE ASN name enrichment.
