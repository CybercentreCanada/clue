# Assemblyline

Maintaining Team/Organization: CCCS

Status: Stable

This plugin enriches selectors based on their presence in Assemblyline alerts.

## Authentication

This plugin supports two methods of authenticating with Assemblyline:
- OAuth2: This takes a token from the Clue API and uses it to authenticate with Assemblyline. This is the recommended method for production use.
- API Key: You can provide your Assemblyline API key in the plugin configuration. This is for development and testing purposes or if you have an Assemblyline instance that does not support OAuth2.

### OAuth2

The plugin assumes that token provided by Clue will grant the following roles in Assemblyline:
- `submission_create`: Required to submit selectors to Assemblyline.
- `alert_view`: Required to view alerts in Assemblyline.
- `badlist_view`: Required to view badlists in Assemblyline.
- `safelist_view`: Required to view safelists in Assemblyline.
- `submission_view`: Required to view submissions in Assemblyline.

**Developer's Note**: Any extension of this plugin that requires additional roles should be discussed with the Clue team before implementation and documented for deployment references.
