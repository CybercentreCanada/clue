# Clue: The Enrichment Engine

Elevate your Security Operations Center's efficiency with Clue, the cutting-edge enrichment tool tailored for today's SOC demands.

## 🚀 Core Capabilities 

Clue enables tool developers to interconnect their SOC applications by dynamically enriching security indicators. Analysts can quickly identify and correlate indicators across multiple tools, pivot between platforms, and execute pre-defined actions directly from the UI. 

- **💾 Real-Time Contextual Enrichment**: Automatically enrich indicators (IPs, domains, file hashes, ports) with assessments, opinions, and additional context from multiple sources. Enrichments display as visual icons, country flags, and interactive popovers containing detailed data from each plugin. 

- **🧩 Modular Plugin-Based Architecture**: Extensible plugin architecture enables integration with unlimited data sources. Each plugin operates as an independent service communicating with the central API server, providing scalability and flexibility to adapt to your SOC's specific needs. 

- **🎬 Plugin-Specific Executable Actions**: Execute pre-defined actions directly on indicators without leaving your workflow. Pivot to other applications, submit data for analysis, or trigger automated workflows. Actions can include dynamic forms to capture required additional parameters. 

- **🐶 Rich Data Fetchers**: Fetchers enable plugins to render enriched data in multiple formats, including formatted Markdown, structured JSON, visual graphs, and images. Generate detailed reports, visualize complex relationships, or display screenshots of rendered files directly within the Clue interface.

- **🪄 Simple UI Integration**: Integrate Clue into any UI application by importing the clue-ui npm package, initializing the ClueProvider with the API server URL, and using enriched components or React hooks. Enrichments happen automatically by replacing standard components with their enriched equivalents. 

- **🧰 Simplified Plugin Development **: Create custom plugins using the clue-api Python library and template plugin repository. Simply register your plugin with the central server by specifying its name, supported indicator types, and URL. Develop and deploy integrations to query, display, and interact with your own tools. 

## 🔌 Available Plugins

Clue comes with several built-in plugins to enrich your security data:

- **🔍 AssemblyLine**: Seamlessly integrates with the AssemblyLine malware analysis platform. Automatically correlates indicators (IPs, domains, hashes) against past analysis results, providing immediate visibility into previously analyzed threats and their verdicts. 

- **📜 Certificate Transparency (crt.sh)**: Leverages the crt.sh database to uncover SSL/TLS certificate history for domains. Helps analysts track certificate issuance, identify potential phishing infrastructure, and map related domains through Certificate Transparency logs. 

- **📋 Example Plugin**: A comprehensive reference implementation for developers. Demonstrates the complete plugin lifecycle, including enrichment logic, custom actions, and data formatting, serving as a perfect starting point for building custom internal integrations. 

- **🚨 Howler**: Connects directly with the Howler alert triage platform. Instantly verifies if an indicator has been seen in previous security alerts or hits, and provides one-click pivoting features to seamlessly transition from analysis to investigation within the Howler UI.

- **🦠 MalwareBazaar**: Taps into the MalwareBazaar community-driven intelligence. Enriches file hashes (MD5, SHA1, SHA256) with attribution data, malware family signatures, and vendor detection statistics to quickly identify known malicious payloads. 

- **🚪 Port Lookup**: Provides instant context for network ports and services. Automatically maps port numbers from raw inputs or URLs to their IANA service definitions and common usages, enhanced with visual service icons (e.g., SSH, HTTP, FTP) for faster recognition. 

- **🛡️ VirusTotal**: Unlocks global threat context via the VirusTotal API. Enriches IPs, domains, URLs, and file hashes with reputation scores, geographic ownership data (ASN/Country), and detailed threat intelligence attributes to accelerate decision-making. 

## Documentation

For documentation, see <https://cybercentrecanada.github.io/clue/>

### Development

If you'd like to contribute to Clue, follow the [developer's guide](https://cybercentrecanada.github.io/clue/developer/), create a branch and get coding!
