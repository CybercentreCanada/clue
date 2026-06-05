/* eslint-disable no-console */

import { createPluginStore } from 'react-pluggable';
import type ClueUIPlugin from './ClueUIPlugin';

class ClueUIPluginStore {
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

    if (plugin.actionIds) {
      plugin.actionIds.forEach(actionId => {
        this.pluginsByActionId[actionId] = [...(this.pluginsByActionId[actionId] ?? []), plugin.name];
      });
    }

    if (plugin.fetcherIds) {
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

  getPlugin(format: string, resultType: 'action' | 'fetcher', actionId?: string, fetcherId?: string) {
    let pluginsById: string[] = [];
    let pluginsByFormat: string[] = [];
    let pluginsByResultType: string[] = [];

    if (resultType === 'action' && actionId) {
      pluginsById = this.pluginsByActionId[actionId];
    } else if (resultType === 'fetcher' && fetcherId) {
      pluginsById = this.pluginsByFetcherId[fetcherId];
    }

    pluginsByResultType = resultType === 'action' ? this.actionPlugins : this.fetcherPlugins;

    pluginsByFormat = this.pluginsByFormat[format] ?? [];

    const availablePlugins = pluginsByFormat.filter(plugin => {
      if (pluginsById) {
        return pluginsById.includes(plugin);
      }
      return pluginsByResultType.includes(plugin);
    });

    return availablePlugins.length > 0 ? availablePlugins[0] : undefined;
  }
  public get pluginStore() {
    return this._pluginStore;
  }
}

const clueUIPluginStore = new ClueUIPluginStore();

export default clueUIPluginStore;
