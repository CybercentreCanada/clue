export type ClueUIPluginDefinition = {
  name: string;
  id: string;
  loadPlugin: () => Promise<{ default: any }>;
};

export default class ClueUIPluginsRegistry {
  private _plugins: ClueUIPluginDefinition[] = [
    // { name: 'TestPlugin', id: 'none', loadPlugin: () => import('./test') },
    { name: 'MarkdownPlugin', id: 'markdown', loadPlugin: () => import('./markdown') },
    { name: 'ImagePlugin', id: 'image', loadPlugin: () => import('./image') },
    { name: 'JSONPlugin', id: 'json', loadPlugin: () => import('./json') },
    { name: 'GraphPlugin', id: 'graph', loadPlugin: () => import('./graph') },
    { name: 'FilePlugin', id: 'file', loadPlugin: () => import('./file') }
  ];

  getPlugins() {
    return this._plugins;
  }
}
