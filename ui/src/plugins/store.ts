/* eslint-disable no-console */

import { createPluginStore } from 'react-pluggable';
import type ClueUIPlugin from './ClueUIPlugin';

class ClueUIPluginStore {
  private _pluginStore = createPluginStore();

  plugins: string[] = [];

  pluginsByFormat: { [format: string]: string[] } = {};
  pluginsByActionId: { [action: string]: string[] } = {};

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

    this.pluginStore.install(plugin);
  }

  getPluginsByFormat(format: string) {
    return this.pluginsByFormat[format] ?? [];
  }

  getPluginsByActionId(actionId: string) {
    return this.pluginsByActionId[actionId] ?? [];
  }

  public get pluginStore() {
    return this._pluginStore;
  }
}

const clueUIPluginStore = new ClueUIPluginStore();

export default clueUIPluginStore;
