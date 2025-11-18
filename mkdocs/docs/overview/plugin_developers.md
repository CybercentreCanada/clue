# Clue From The Plugin Developer's Perspective

In order for Clue to enrich data from a tool, it needs a plugin to be developed that will interface with the tool in question. The Clue central API server is a simple flask server that typically runs in a pod on a cluster, and the plugins are separate servers that usually run in pods in the same namespace, and communication between the two would rely on internal cluster networking, although the plugins could be hosted anywhere that is accessible by the central server.

## Getting Started

Each plugin is registered on the central server by configuration, so all that's needed to connect a plugin to the central server is the plugin name, which types are supported by the plugin and where it can be found (url/port).

The clue-api python library contains everything you need to get started on plugin development, and there's also a template plugin repository that can be used to quick start development.
