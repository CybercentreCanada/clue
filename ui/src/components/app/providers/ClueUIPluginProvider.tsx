import { createContext, useEffect, type FC, type PropsWithChildren } from 'react';
import { PluginProvider } from 'react-pluggable';
import type ClueUIPlugin from '../../../plugins/ClueUIPlugin';
import type { ClueUIPluginDefinition } from '../../../plugins/registry';
import ClueUIPluginsRegistry from '../../../plugins/registry';
import type { ClueUIPluginStore } from '../../../plugins/store';
import clueUIPluginStore from '../../../plugins/store';

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

export type ClueUIPluginContextType = {
  clueUIPluginStore: ClueUIPluginStore;
};

export const ClueUIPluginContext = createContext<ClueUIPluginContextType | null>({
  clueUIPluginStore: clueUIPluginStore
});

export const ClueUIPluginProvider: FC<PropsWithChildren<ClueUIPluginProviderProps>> = ({
  plugins,
  excludePlugins,
  excludeBuiltInPlugins,
  children
}) => {
  useEffect(() => {
    const loadPlugins = async () => {
      // load plugins passed in via props first, so they take precedence over built-in plugins
      if (plugins && Array.isArray(plugins)) {
        for (const pluginDef of plugins) {
          if (!excludePlugins?.includes(pluginDef.id)) {
            const pluginModule = await pluginDef.loadPlugin();
            const plugin = new pluginModule.default() as ClueUIPlugin;
            clueUIPluginStore.install(plugin);
          }
        }
      }

      if (!excludeBuiltInPlugins) {
        const builtInPlugins = new ClueUIPluginsRegistry().getPlugins();
        for (const pluginDef of builtInPlugins) {
          if (!excludePlugins?.includes(pluginDef.id)) {
            const pluginModule = await pluginDef.loadPlugin();
            const plugin = new pluginModule.default() as ClueUIPlugin;
            clueUIPluginStore.install(plugin);
          }
        }
      }
    };
    loadPlugins();
  }, [excludeBuiltInPlugins, excludePlugins, plugins]);

  return (
    <ClueUIPluginContext.Provider value={{ clueUIPluginStore }}>
      <PluginProvider pluginStore={clueUIPluginStore.pluginStore}>{children}</PluginProvider>
    </ClueUIPluginContext.Provider>
  );
};
