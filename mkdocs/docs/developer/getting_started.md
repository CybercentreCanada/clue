# Getting Started

## Integrating Your Plugin into Clue - Responsibilities and Expectations

Since clue is a fairly complex project with a fair number of moving parts, it's important to outline the
responsibilities of the various stakeholders:

1. CCCS is the primary code-owner of the core clue-api code (i.e., all code inside the `clue/` folder).
2. Each respective team is responsible for maintenance and evolution of their specific plugin.
3. Each respective team is responsible for ensuring compatibiliy between their plugin and the central API.
   1. This includes adapting to breaking changes introduced during development of the core clue service.
   2. CCCS will try its best to limit these breaking changes as much as possible, and give plenty of notice.
4. CCCS is available for support with development (asking questions, fixing bugs in the central service, etc.).
5. CCCS is responsible for maintaining the stability of the service as a whole.

## Integrating Your Plugin into Clue - Hosting the Code

When building a plugin, the first step is to decide where the code will be stored you have two options for hosting the
code:

### Including the plugin in the repo

This approach allows you to develop the plugin, including it in the build process for clue, ensuring it is tightly
integrated with schema changes and feature updates top the base clue packages. This allows clue devs to test
your plugin for compatibility, and currently is the recommended approach.

**Note: Only python plugins are currently supported this way!**

The first step is to create a folder for your application in the
[plugins directory](https://github.com/CybercentreCanada/clue/tree/develop/plugins). You can use the
[`make create-plugin`](https://github.com/CybercentreCanada/clue/blob/develop/Makefile#L59) to do so, or copy an
existing plugin depending on your preferences.

Once you have finished development of the core features, it is **strongly recommended** that you write at least very
basic unit tests for your plugin, with the gold standard being full integration testing against mock data. For
inspiration, check existing plugins and their test regimes.

For detailed information on initializing tests, see our main [README](../README.md) file.

#### External dependencies

If you import external packages differing from the plugin template, you must specify them both in the `requirements.txt`
file of your plugin, and in plugin dependencies group of the poetry project. The following command can do so:

```bash
# Replace the dependencies here with yours
poetry add -G plugins azure-core 'azure-storage-blob>=12.2.0' 'azure-storage-file-datalake>=12.2.0'
```

#### Creating a Pull Request

Once you are satisfied with your plugin, create a pull request for a repository contributor to review the plugin for final
approval. There are some code quality checks performed on the codebase - if issues are flagged, work with a repository contributor
to resolve them. Only readability and compatibility checks are the responsibility of APA2B - we do not have any
say on the functionality of your plugin, and cannot assist in development of your plugin beyond questions about the base
clue codebase.

### Standalone repo

If you find our code standards too strict or insufficient, or want to develop the plugin in a language other than
python, or simply don't want to be included in the repository, you are welcome to host, test and build the plugin in
a standalone repository. We recommend running integration tests with a copy of the clue API to ensure
compatibility.
