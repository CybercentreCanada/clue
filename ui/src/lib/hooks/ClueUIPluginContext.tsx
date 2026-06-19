import type { ClueUIPlugin, ClueUIPluginDefinition } from 'lib/main';
import ClueUIPluginsRegistry from 'lib/plugins/registry';
import clueUIPluginStore from 'lib/plugins/store';
import { useEffect, type FC, type PropsWithChildren } from 'react';
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
  useEffect(() => {
    const loadPlugin = async (pluginDef: ClueUIPluginDefinition) => {
      try {
        const pluginModule = await pluginDef.loadPlugin();
        const plugin = new pluginModule.default() as ClueUIPlugin;
        clueUIPluginStore.install(plugin);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(`[ClueUIPluginProvider] Failed to load plugin: ${pluginDef.name ?? pluginDef.id}`, err);
      }
    };

    const loadPlugins = async () => {
      // load plugins passed in via props first, so they take precedence over built-in plugins
      if (plugins && Array.isArray(plugins)) {
        for (const pluginDef of plugins) {
          if (!excludePlugins?.includes(pluginDef.id)) {
            await loadPlugin(pluginDef);
          }
        }
      }

      if (!excludeBuiltInPlugins) {
        const builtInPlugins = new ClueUIPluginsRegistry().getPlugins();
        for (const pluginDef of builtInPlugins) {
          if (!excludePlugins?.includes(pluginDef.id)) {
            await loadPlugin(pluginDef);
          }
        }
      }
    };
    // eslint-disable-next-line no-console
    void loadPlugins().catch(err => console.error('[ClueUIPluginProvider] Failed to load plugins', err));
  }, [excludeBuiltInPlugins, excludePlugins, plugins]);

  return <PluginProvider pluginStore={clueUIPluginStore.pluginStore}>{children}</PluginProvider>;
};

export { ClueUIPluginProvider as ClueUIPluginProvider };
