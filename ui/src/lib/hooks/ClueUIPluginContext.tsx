import type { ClueUIPlugin, ClueUIPluginDefinition } from 'lib/main';
import ClueUIPluginsRegistry from 'lib/plugins/registry';
import clueUIPluginStore from 'lib/plugins/store';
import { useEffect, useState, type FC, type PropsWithChildren } from 'react';
import type { PluginStore } from 'react-pluggable';
import { PluginProvider } from 'react-pluggable';

export type ClueUIPluginProviderProps = {
  /**
   * List of additional custom plugins to load.
   * Plugins passed in via this prop will take precedence over built-in plugins.
   */
  plugins?: ClueUIPluginDefinition[];
  /**
   * List of plugin ids to exclude from loading, including built-in plugins from ClueUIPluginsRegistry
   * and plugins passed in via props
   */
  excludePlugins?: string[];
  /**
   * If true, do not load any plugins from the ClueUIPluginsRegistry, only load plugins passed in via props
   */
  excludeBuiltInPlugins?: boolean;
};

const ClueUIPluginProvider: FC<PropsWithChildren<ClueUIPluginProviderProps>> = ({
  plugins,
  excludePlugins,
  excludeBuiltInPlugins,
  children
}) => {
  const [pluginStore, setPluginStore] = useState<PluginStore>(() => clueUIPluginStore.pluginStore);

  useEffect(() => {
    const abortController = new AbortController();

    const loadPlugin = async (pluginDef: ClueUIPluginDefinition) => {
      try {
        const pluginModule = await pluginDef.loadPlugin();
        if (abortController.signal.aborted) return; // Exit if effect was cancelled

        const plugin = new pluginModule.default() as ClueUIPlugin;
        clueUIPluginStore.install(plugin);
      } catch (err) {
        if (abortController.signal.aborted) return;
        // eslint-disable-next-line no-console
        console.error(`[ClueUIPluginProvider] Failed to load plugin: ${pluginDef.name ?? pluginDef.id}`, err);
      }
    };

    const loadPlugins = async () => {
      // load plugins passed in via props first, so they take precedence over built-in plugins
      if (plugins && Array.isArray(plugins)) {
        for (const pluginDef of plugins) {
          if (abortController.signal.aborted) return;
          if (!excludePlugins?.includes(pluginDef.id)) {
            await loadPlugin(pluginDef);
          }
        }
      }

      if (!excludeBuiltInPlugins) {
        const builtInPlugins = new ClueUIPluginsRegistry().getPlugins();
        for (const pluginDef of builtInPlugins) {
          if (abortController.signal.aborted) return;
          if (!excludePlugins?.includes(pluginDef.id)) {
            await loadPlugin(pluginDef);
          }
        }
      }
    };

    clueUIPluginStore.reset();
    setPluginStore(clueUIPluginStore.pluginStore);

    // eslint-disable-next-line no-console
    void loadPlugins().catch(err => {
      if (!abortController.signal.aborted) {
        // eslint-disable-next-line no-console
        console.error('[ClueUIPluginProvider] Failed to load plugins', err);
      }
    });

    return () => abortController.abort(); // Cleanup: abort on unmount or re-run
  }, [excludeBuiltInPlugins, excludePlugins, plugins]);

  return <PluginProvider pluginStore={pluginStore}>{children}</PluginProvider>;
};

export { ClueUIPluginProvider as ClueUIPluginProvider };
