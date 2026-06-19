/* eslint-disable no-console */

import { createPluginStore } from 'react-pluggable';
import type ClueUIPlugin from './ClueUIPlugin';

export class ClueUIPluginStore {
  private _pluginStore = createPluginStore();

  plugins: string[] = [];

  pluginsByFormat: { [format: string]: string[] } = {};
  pluginsByActionId: { [actionId: string]: string[] } = {};
  pluginsByFetcherId: { [fetcherId: string]: string[] } = {};
  actionPlugins: string[] = [];
  fetcherPlugins: string[] = [];

  install(plugin: ClueUIPlugin) {
    if (this.plugins.includes(plugin.name)) {
      return;
    }

    console.log(`Installing plugin ${plugin.getPluginName()} by ${plugin.author}`);

    this.plugins.push(plugin.name);

    if (plugin.format) {
      this.pluginsByFormat[plugin.format] = [...(this.pluginsByFormat[plugin.format] ?? []), plugin.name];
    }

    if (plugin.actionIds && plugin.actionResult) {
      plugin.actionIds.forEach(actionId => {
        this.pluginsByActionId[actionId] = [...(this.pluginsByActionId[actionId] ?? []), plugin.name];
      });
    }

    if (plugin.fetcherIds && plugin.fetcherResult) {
      plugin.fetcherIds.forEach(fetcherId => {
        this.pluginsByFetcherId[fetcherId] = [...(this.pluginsByFetcherId[fetcherId] ?? []), plugin.name];
      });
    }

    if (plugin.actionResult) {
      this.actionPlugins.push(plugin.name);
    }

    if (plugin.fetcherResult) {
      this.fetcherPlugins.push(plugin.name);
    }

    this.pluginStore.install(plugin);
  }

  /**
   * Get plugins based on the given criteria.
   *
   * Only plugins that match all criteria will be returned, which could be an empty list. The order of the plugins
   * matter, for example if a plugin specifies an action ID, it will be ordered before a plugin just specifies the
   * format or result type.
   *
   * @param format filter plugins by this format
   * @param resultType filter plugins by the result type that they accept (action or fetcher)
   * @param actionId filter plugins by this action ID
   * @param fetcherId filter plugins by this fetcher ID
   * @returns an array of plugin names that match the given criteria
   */
  getPlugins(format?: string, resultType?: 'action' | 'fetcher', actionId?: string, fetcherId?: string): string[] {
    let pluginsById: string[] | undefined = undefined;
    let pluginsByFormat: string[] = [];
    let pluginsByResultType: string[] | undefined = undefined;

    if (resultType === 'action' && actionId) {
      pluginsById = this.pluginsByActionId[actionId];
    } else if (resultType === 'fetcher' && fetcherId) {
      pluginsById = this.pluginsByFetcherId[fetcherId];
    }

    pluginsByResultType =
      resultType === 'action' ? this.actionPlugins : resultType === 'fetcher' ? this.fetcherPlugins : undefined;

    pluginsByFormat = format ? (this.pluginsByFormat[format] ?? []) : this.plugins;

    if (resultType && (pluginsByResultType?.length ?? 0) === 0) {
      return [];
    }

    const availablePlugins =
      pluginsById?.length || pluginsByResultType?.length
        ? [
            ...(pluginsById?.length
              ? pluginsByFormat.filter(plugin => {
                  return pluginsById.includes(plugin);
                })
              : []),
            ...(pluginsByResultType?.length
              ? pluginsByFormat.filter(plugin => pluginsByResultType.includes(plugin))
              : [])
          ]
        : pluginsByFormat;

    return [...new Set(availablePlugins ?? [])];
  }

  getPlugin(
    format: string,
    resultType: 'action' | 'fetcher',
    actionId?: string,
    fetcherId?: string
  ): string | undefined {
    const availablePlugins = this.getPlugins(format, resultType, actionId, fetcherId);

    return availablePlugins.length > 0 ? availablePlugins[0] : undefined;
  }

  public get pluginStore() {
    return this._pluginStore;
  }
}

const clueUIPluginStore = new ClueUIPluginStore();

export default clueUIPluginStore;
