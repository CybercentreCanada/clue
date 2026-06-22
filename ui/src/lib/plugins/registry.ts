import type ClueUIPlugin from './ClueUIPlugin';

export type ClueUIPluginDefinition = {
  name: string;
  id: string;
  loadPlugin: () => Promise<{ default: new () => ClueUIPlugin }>;
};

export default class ClueUIPluginsRegistry {
  private _plugins: ClueUIPluginDefinition[] = [
    // { name: 'TestPlugin', id: 'none', loadPlugin: () => import('./test') },
    { name: 'MarkdownPlugin', id: 'markdown', loadPlugin: () => import('./markdown') },
    { name: 'ImagePlugin', id: 'image', loadPlugin: () => import('./image') },
    { name: 'JsonPlugin', id: 'json', loadPlugin: () => import('./json') },
    { name: 'GraphPlugin', id: 'graph', loadPlugin: () => import('./graph') },
    { name: 'FilePlugin', id: 'file', loadPlugin: () => import('./file') }
  ];

  getPlugins() {
    // return shallow copy to preserve encapsulation
    return [...this._plugins];
  }
}
