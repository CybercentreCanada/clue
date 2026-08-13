import { render, waitFor } from '@testing-library/react';
import { ClueUIPluginProvider } from 'lib/hooks/ClueUIPluginContext';
import type { ReactNode } from 'react';
import { describe, it } from 'vitest';
import ClueUIPlugin from './ClueUIPlugin';
import type { ClueUIPluginDefinition } from './registry';
import clueUIPluginStore from './store';

type TestPluginOptions = {
  name: string;
  format?: string;
  actionIds?: string[];
  fetcherIds?: string[];
  withActionResult?: boolean;
  withFetcherResult?: boolean;
  version?: string;
  author?: string;
};

const makeTestPlugin = ({
  name,
  format = 'test-format',
  actionIds,
  fetcherIds,
  withActionResult = true,
  withFetcherResult = false,
  version = '1.0.0',
  author = 'test author'
}: TestPluginOptions) => {
  class TestPlugin extends ClueUIPlugin {
    name = name;
    format = format;
    version = version;
    author = author;
    description = 'Test plugin';
    actionIds = actionIds;
    fetcherIds = fetcherIds;

    actionResult = withActionResult ? () => null : undefined;
    fetcherResult = withFetcherResult ? () => null : undefined;
  }

  return new TestPlugin();
};

const resetPluginStore = () => {
  clueUIPluginStore.reset();
};

describe('ClueUIPlugin framework', () => {
  beforeEach(() => {
    resetPluginStore();
    vi.spyOn(console, 'log').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('ClueUIPlugin base class lifecycle', () => {
    it('should register and unregister render functions during activate and deactivate', () => {
      const addFunction = vi.fn();
      const removeFunction = vi.fn();
      const localization = vi.fn();

      class LifecyclePlugin extends ClueUIPlugin {
        name = 'LifecyclePlugin';
        format = 'lifecycle';
        version = '1.0.0';
        author = 'Lifecycle Tester';
        description = 'Lifecycle test plugin';

        actionResult() {
          return null;
        }

        fetcherResult() {
          return null;
        }

        localization = localization;
      }

      const plugin = new LifecyclePlugin();
      plugin.init({ addFunction, removeFunction } as any);

      plugin.activate();
      expect(addFunction).toHaveBeenCalledWith('LifecyclePlugin.actionResult', expect.any(Function));
      expect(addFunction).toHaveBeenCalledWith('LifecyclePlugin.fetcherResult', expect.any(Function));
      expect(localization).toHaveBeenCalledOnce();

      plugin.deactivate();
      expect(removeFunction).toHaveBeenCalledWith('LifecyclePlugin.actionResult');
      expect(removeFunction).toHaveBeenCalledWith('LifecyclePlugin.fetcherResult');
    });
  });

  describe('ClueUIPluginStore', () => {
    it('should install and index plugins by format, action id, and fetcher id', () => {
      const plugin = makeTestPlugin({
        name: 'IndexedPlugin',
        format: 'indexed-format',
        actionIds: ['example.action'],
        fetcherIds: ['example.fetcher'],
        withActionResult: true,
        withFetcherResult: true
      });

      clueUIPluginStore.install(plugin);

      expect(clueUIPluginStore.plugins).toEqual(['IndexedPlugin']);
      expect(clueUIPluginStore.pluginsByFormat['indexed-format']).toEqual(['IndexedPlugin']);
      expect(clueUIPluginStore.pluginsByActionId['example.action']).toEqual(['IndexedPlugin']);
      expect(clueUIPluginStore.pluginsByFetcherId['example.fetcher']).toEqual(['IndexedPlugin']);
      expect(clueUIPluginStore.actionPlugins).toEqual(['IndexedPlugin']);
      expect(clueUIPluginStore.fetcherPlugins).toEqual(['IndexedPlugin']);
    });

    it('should not install the same plugin twice', () => {
      const plugin = makeTestPlugin({ name: 'UniquePlugin', format: 'unique-format' });
      const installSpy = vi.spyOn(clueUIPluginStore.pluginStore, 'install');

      clueUIPluginStore.install(plugin);
      clueUIPluginStore.install(plugin);

      expect(clueUIPluginStore.plugins).toEqual(['UniquePlugin']);
      expect(installSpy).toHaveBeenCalledOnce();
    });

    it('should resolve an action plugin using format and action id', () => {
      const actionPlugin = makeTestPlugin({
        name: 'ActionPlugin',
        format: 'shared-format',
        actionIds: ['specific.action'],
        withActionResult: true
      });
      const otherPlugin = makeTestPlugin({
        name: 'OtherPlugin',
        format: 'shared-format',
        actionIds: ['other.action'],
        withActionResult: true
      });

      clueUIPluginStore.install(actionPlugin);
      clueUIPluginStore.install(otherPlugin);

      const selected = clueUIPluginStore.getPlugin('shared-format', 'action', 'specific.action');
      expect(selected).toBe('ActionPlugin');
    });

    it('should resolve a fetcher plugin using format and fetcher id', () => {
      const fetcherPlugin = makeTestPlugin({
        name: 'FetcherPlugin',
        format: 'fetcher-format',
        fetcherIds: ['specific.fetcher'],
        withActionResult: false,
        withFetcherResult: true
      });

      clueUIPluginStore.install(fetcherPlugin);

      const selected = clueUIPluginStore.getPlugin('fetcher-format', 'fetcher', undefined, 'specific.fetcher');
      expect(selected).toBe('FetcherPlugin');
    });

    it('should fall back to type-compatible plugins when id-specific mapping is missing', () => {
      const plugin = makeTestPlugin({
        name: 'FallbackPlugin',
        format: 'fallback-format',
        withActionResult: true
      });

      clueUIPluginStore.install(plugin);

      const selected = clueUIPluginStore.getPlugin('fallback-format', 'action', 'unknown.action');
      expect(selected).toBe('FallbackPlugin');
    });

    it('should prefer generic plugins over id-specific plugins that do not match the requested id', () => {
      const nonMatchingSpecific = makeTestPlugin({
        name: 'NonMatchingSpecificPlugin',
        format: 'mixed-format',
        actionIds: ['other.action'],
        withActionResult: true
      });
      const generic = makeTestPlugin({
        name: 'GenericPlugin',
        format: 'mixed-format',
        withActionResult: true
      });

      clueUIPluginStore.install(nonMatchingSpecific);
      clueUIPluginStore.install(generic);

      const selected = clueUIPluginStore.getPlugin('mixed-format', 'action', 'unknown.action');
      expect(selected).toBe('GenericPlugin');
    });
    it('should return undefined when no compatible plugin is found', () => {
      const plugin = makeTestPlugin({ name: 'SinglePlugin', format: 'only-format', withActionResult: true });
      clueUIPluginStore.install(plugin);

      const selected = clueUIPluginStore.getPlugin('missing-format', 'action', 'any.action');
      expect(selected).toBeUndefined();
    });

    it('reset should empty the plugin store', () => {
      const plugin = makeTestPlugin({ name: 'TemporaryPlugin', format: 'temp-format', withActionResult: true });
      clueUIPluginStore.install(plugin);

      expect(clueUIPluginStore.plugins).toEqual(['TemporaryPlugin']);

      clueUIPluginStore.reset();

      expect(clueUIPluginStore.plugins).toEqual([]);
    });

    it('getAvailableFormats should return all registered formats when no plugin id is provided', () => {
      const firstPlugin = makeTestPlugin({
        name: 'FormatPluginOne',
        format: 'format-one',
        withActionResult: true
      });
      const secondPlugin = makeTestPlugin({
        name: 'FormatPluginTwo',
        format: 'format-two',
        withActionResult: true
      });

      clueUIPluginStore.install(firstPlugin);
      clueUIPluginStore.install(secondPlugin);

      expect(clueUIPluginStore.getAvailableFormats()).toEqual(['format-one', 'format-two']);
    });

    it('getAvailableFormats should return only formats supported by the given plugin id', () => {
      const sharedOne = makeTestPlugin({
        name: 'SharedFormatPluginOne',
        format: 'shared-format',
        withActionResult: true
      });
      const sharedTwo = makeTestPlugin({
        name: 'SharedFormatPluginTwo',
        format: 'shared-format',
        withActionResult: true
      });
      const uniquePlugin = makeTestPlugin({
        name: 'UniqueFormatPlugin',
        format: 'unique-format',
        withActionResult: true
      });

      clueUIPluginStore.install(sharedOne);
      clueUIPluginStore.install(sharedTwo);
      clueUIPluginStore.install(uniquePlugin);

      expect(clueUIPluginStore.getAvailableFormats('SharedFormatPluginOne')).toEqual(['shared-format']);
      expect(clueUIPluginStore.getAvailableFormats('UniqueFormatPlugin')).toEqual(['unique-format']);
    });

    it('getAvailableFormats should return an empty list for unknown plugin id', () => {
      const plugin = makeTestPlugin({ name: 'KnownPlugin', format: 'known-format', withActionResult: true });
      clueUIPluginStore.install(plugin);

      expect(clueUIPluginStore.getAvailableFormats('UnknownPlugin')).toEqual([]);
    });
  });

  describe('ClueUIPluginProvider', () => {
    const renderProvider = (props: {
      plugins?: ClueUIPluginDefinition[];
      excludePlugins?: string[];
      excludeBuiltInPlugins?: boolean;
    }) => {
      return render(
        <ClueUIPluginProvider {...props}>
          <div data-testid="child">child</div>
        </ClueUIPluginProvider>
      );
    };

    it('should load plugins provided via props', async () => {
      const CustomPluginClass = class CustomPlugin extends ClueUIPlugin {
        name = 'CustomPlugin';
        format = 'custom-format';
        version = '1.0.0';
        author = 'Custom Author';
        description = 'Custom provider plugin';

        actionResult(): ReactNode {
          return null;
        }
      };

      const plugins: ClueUIPluginDefinition[] = [
        {
          id: 'custom-plugin',
          name: 'CustomPlugin',
          loadPlugin: async () => ({ default: CustomPluginClass })
        }
      ];

      renderProvider({ plugins, excludeBuiltInPlugins: true });

      await waitFor(() => {
        expect(clueUIPluginStore.plugins).toContain('CustomPlugin');
      });
    });

    it('should skip plugins listed in excludePlugins', async () => {
      const ExcludedPluginClass = class ExcludedPlugin extends ClueUIPlugin {
        name = 'ExcludedPlugin';
        format = 'excluded-format';
        version = '1.0.0';
        author = 'Excluded Author';
        description = 'Excluded plugin';

        actionResult(): ReactNode {
          return null;
        }
      };

      const plugins: ClueUIPluginDefinition[] = [
        {
          id: 'excluded-plugin',
          name: 'ExcludedPlugin',
          loadPlugin: async () => ({ default: ExcludedPluginClass })
        }
      ];

      renderProvider({ plugins, excludeBuiltInPlugins: true, excludePlugins: ['excluded-plugin'] });

      await waitFor(() => {
        expect(clueUIPluginStore.plugins).not.toContain('ExcludedPlugin');
      });
    });

    it('should load prop plugins before built-ins so they take precedence', async () => {
      const CustomMarkdownPlugin = class CustomMarkdownPlugin extends ClueUIPlugin {
        name = 'MarkdownPlugin';
        format = 'markdown';
        version = '9.9.9';
        author = 'Custom Markdown Author';
        description = 'Overrides built-in markdown plugin';

        actionResult(): ReactNode {
          return null;
        }
      };

      const plugins: ClueUIPluginDefinition[] = [
        {
          id: 'custom-markdown',
          name: 'CustomMarkdownPlugin',
          loadPlugin: async () => ({ default: CustomMarkdownPlugin })
        }
      ];

      renderProvider({
        plugins,
        excludePlugins: ['image', 'json', 'graph', 'file'],
        excludeBuiltInPlugins: false
      });

      await waitFor(() => {
        expect(clueUIPluginStore.plugins.filter(plugin => plugin === 'MarkdownPlugin')).toHaveLength(1);
      });

      expect(clueUIPluginStore.pluginStore.getInstalledPluginNameWithVersion('MarkdownPlugin')).toBe(
        'MarkdownPlugin@9.9.9'
      );
    });
  });
});
