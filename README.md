# Clue: The Enrichment Engine

Elevate your Security Operations Center's efficiency with Clue, the cutting-edge enrichment tool tailored for today's SOC demands.

## 🚀 Do A Backflip

Clue allows tool developers to inter-connect their apps, allowing analysts to quickly identify and cross-reference indicators, as well as execute pre-defined actions on those indicators.

- **💾 Enriched Data Everywhere**: Enrich data everywhere by providing a quick visual indicator like an icon (⚠️) or even a flag, and provide more details in a popup when clicked.

- **🧩 Plugin Based Architecture**: Thanks to the plugin-based architecture, Clue is highly modular and can enrich from any number of sources.

- **🎬 Execute Actions On-The-Fly**: Execute any pre-defined action on an indicator by using Clue Actions.

- **🐶 Display Data Using Fetchers**: Using Clue Fetchers, data can be processed and displayed in any support format, such as Markdown, JSON or even Images.

- **🪄 Seamless Integration**: Clue is extremely easy to add to any UI application, simply initialize the provider and use the Clue components to automatically enrich your data.

- **🧰 Write Your Own Plugins**: Clue plugins are easy to write, allowing you to query, show and interact with your own apps from within any other app using Clue.

## 🔌 Available Plugins

Clue comes with several built-in plugins to enrich your security data:

- **🔍 AssemblyLine**: Integrates with AssemblyLine malware analysis platform to provide detailed analysis results and threat intelligence for file samples.

- **📜 Certificate Transparency (crt.sh)**: Looks up SSL/TLS certificates for domains using the crt.sh Certificate Transparency logs database.

- **📋 Example Plugin**: A sample plugin template that demonstrates how to create custom Clue plugins for developers.

- **🚨 Howler**: Integrates with Howler alert triage platform to check if selectors (indicators) are present in security alerts, helping analysts identify threats and targets.

- **🦠 MalwareBazaar**: Connects to MalwareBazaar to provide malware intelligence, including hash lookups and sample information.

- **🚪 Port Lookup**: Provides port number to service name mapping using IANA port assignments and service definitions.

- **🛡️ VirusTotal**: Integrates with VirusTotal API to perform reputation checks on files, URLs, domains, and IP addresses.

## Documentation

For documentation, see <https://cybercentrecanada.github.io/clue-docs/>

### Development

If you'd like to contribute to Clue, follow the [developer's guide](https://cybercentrecanada.github.io/clue-docs/developer/getting_started/), create a branch and get coding!
