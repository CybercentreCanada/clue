/* eslint-disable no-console */

import { createPluginStore } from 'react-pluggable';
import type CluePlugin from './CluePlugin';

class CluePluginStore {
  private _pluginStore = createPluginStore();

  plugins: string[] = [];

  install(plugin: CluePlugin) {
    if (this.plugins.includes(plugin.name)) {
      return;
    }

    console.log(`Installing plugin ${plugin.getPluginName()} by ${plugin.author}`);

    this.plugins.push(plugin.name);

    this.pluginStore.install(plugin);
  }

  public get pluginStore() {
    return this._pluginStore;
  }
}

const cluePluginStore = new CluePluginStore();

export default cluePluginStore;
