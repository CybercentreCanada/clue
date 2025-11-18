# Getting Started

## Integrating Your Plugin into Clue - Responsibilities and Expectations

Since clue is a fairly complex project with a fair number of moving parts, it's important to outline the
responsibilities of the various stakeholders:

1. APA2B is the primary code-owner of the core clue-api code (i.e., all code inside the `clue/` folder).
2. Each respective team is responsible for maintenance and evolution of their specific plugin.
3. Each respective team is responsible for ensuring compatibiliy between their plugin and the central API.
   1. This includes adapting to breaking changes introduced during development of the core clue service.
   2. APA2B will try its best to limit these breaking changes as much as possible, and give plenty of notice.
4. APA2B is available for support with development (asking questions, fixing bugs in the central service, etc.).
5. APA2B is responsible for maintaining the stability of the service as a whole.

## Integrating Your Plugin into Clue - Hosting the Code

When building a plugin, the first step is to decide where the code will be stored you have two options for hosting the
code:

### Including the plugin in the repo

This approach allows you to develop the plugin, including it in the build process for clue, ensuring it is tightly
integrated with schema changes and feature updates top the base clue packages. This allows clue devs to test
your plugin for compatibility, and currently is the recommended approach.

**Note: Only python plugins are currently supported this way!**

The first step is to create a folder for your application in the
[plugins directory](https://github.com/CybercentreCanada/clue-api/tree/develop/plugins). You can use the
[clue example template](https://github.com/CybercentreCanada/clue-plugin-template/) to do so, or copy an
existing plugin depending on your preferences.

Once you have finished development of the core features, it is **strongly recommended** that you write at least very
basic unit tests for your plugin, with the gold standard being full integration testing against mock data. For
inspiration, check existing plugins and their test regimes.

You must additionally add an entry to the
[`azure-pipelines.yml`](https://github.com/CybercentreCanada/clue-api/blob/develop/azure-pipelines.yml#L277)
file in the root of the project for your application.

For detailed information on initializing tests, see our main [README](../README.md) file. For further support, reach
out to APA2B.

#### External dependencies

If you import external packages differing from the plugin template, you must specify them both in the `requirements.txt`
file of your plugin, and in plugin dependencies group of the poetry project. The following command can do so:

```bash
# Replace the dependencies here with yours
poetry add -G plugins azure-core 'azure-storage-blob>=12.2.0' 'azure-storage-file-datalake>=12.2.0'
```

#### Creating a Pull Request

Once you are satisfied with your plugin, create a pull request for a member of APA2B to review the plugin for final
approval. There are some code quality checks performed on the codebase - if issues are flagged, work with a member of
APA2B to resolve them. Only readability and compatibility checks are the responsibility of APA2B - we do not have any
say on the functionality of your plugin, and cannot assist in development of your plugin beyond questions about the base
clue codebase.

### Standalone repo

If you find our code standards too strict or insufficient, or want to develop the plugin in a language other than
python, or simply don't want to be included in the repository, you are welcome to host, test and build the plugin in
a standalone repository. We recommend running integration tests with a copy of the clue API to ensure
compatibility.

## Deploying the plugin

Currently, deployment of plugins in the enrichment namespace is the responsibility of APA2B - there are no resources to
allow developers to manually deploy and remove their plugins. However, the plugin can exist anywhere that the central
clue API can reach, so it's not a requirement to deploy it in that namespace.

If your code is hosted in this repo, APA2B will assist in configuring and deploying your plugin when it is ready for
production. There are plans to allow improved management of plugins, including deployment to the enrichment namespace
without the intervention of APA2B, but this will take some time to implement and the work is not currently scheduled.

## Registering the plugin

If you host your plugin's code in this repo, building the image and deploying it will be the responsibility of APA2B -
otherwise, it is the responsibility of the developers of the plugin.

Currently, registration of plugins with the central clue API is predominantly handled through configuration files
in the helm chart. There is support for registering plugins at runtime, but it is fairly basic - reach out to APA2B if
you are interested in runtime registration.
