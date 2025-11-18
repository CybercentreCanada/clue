# Clue From The Integrator's Perspective

This tool is designed to be integrated into other Security Operations Center (SOC) tools, to enrich and inter-connect the different tools used and allow analysts to quickly assess and pivot from one tool to the other.

Clue allows tool developers to enrich indicators (such as potentially malicious IPs, Hostnames, Ports, etc.) by dynamically querying those indicators in all the other relevant tools and showing the results directly in your UI.

For example, say you were to use other CCCS open-source tools such as Howler (an Alert Triaging tool) and Assemblyline (a Malware Analysis tool). With Clue integration, while using Howler, if you were to look at an alert that contains a file hash indicator, the Clue enrichment would automatically search Assemblyline for the file hash, and tell you directly if it's known in Assemblyline, as well as additional info on the file hash.

This section is for tool developers that want to integrate Clue enrichments, actions or fetchers into their own app.

### Integrating Clue In Your UI

In order to enrich indicators in your UI, you will need to import the clue-ui npm package in your project, initialize the ClueProvider with some configuration values such as the url of the Clue API server, and simply use one of the Enriched components, or one of the hooks available to enrich the data in question.

### Enrichments

As mentioned before, Clue provides components and hooks that allow you to simply wrap your indicators, and enrich them by querying all the relevant plugins and displaying the information in the component.

### Actions

Clue also allows for pre-defined actions to be executed on any indicator. Each plugin will provide Clue with a list of available actions, and the clue-ui library provides functions that let you list those actions, as well as execute them. Some actions might also require additional parameters to be specified, so there's also components provided to create a form to provide those additional informations.

### Fetchers

Fetchers are another feature that allows plugin developers to render data in a more detailed way, such as generating a markdown file, JSON data or even an image. This could be useful to generate detailed reports on an indicator, render an email file and take a screenshot, or even show graphs.
