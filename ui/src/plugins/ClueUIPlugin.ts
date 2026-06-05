import i18nInstance from 'i18n';
import type { i18n as I18N } from 'i18next';
import type { ActionResult, FetcherResult } from 'lib/main';
import type { WithActionData } from 'lib/types/WithActionData';
import { difference } from 'lodash-es';
import type React from 'react';
import type { PropsWithChildren } from 'react';
import type { IPlugin, PluginStore } from 'react-pluggable';

const INTERNAL_FUNCTIONS = ['constructor', 'getPluginName', 'getDependencies', 'init', 'activate', 'deactivate'];

export type RenderResultProps = {
  result: WithActionData<ActionResult> | FetcherResult;
  setShowPreview?: (show: boolean) => void;
  // allow for any additional props to be passed in for flexibility, such as styling or event handlers
  [additionalProps: string]: any;
};

export interface RenderFetcherResultProps extends RenderResultProps {
  result: FetcherResult;
}

export interface RenderActionResultProps extends RenderResultProps {
  result: WithActionData<ActionResult>;
}

abstract class ClueUIPlugin implements IPlugin {
  abstract name: string;
  abstract version: string;
  abstract author: string;
  abstract description: string;

  abstract format: string;
  public actionIds?: string[];

  pluginStore: PluginStore;

  private functionsToRemove: string[] = [];

  getPluginName(): string {
    return `${this.name}@${this.version}`;
  }

  getPluginFormat(): string {
    return this.format;
  }

  getPluginActionIds(): string[] | undefined {
    return this.actionIds;
  }

  getDependencies(): string[] {
    return [];
  }

  init(pluginStore: PluginStore): void {
    this.pluginStore = pluginStore;
  }

  activate() {
    const functions = difference(Object.getOwnPropertyNames(ClueUIPlugin.prototype), INTERNAL_FUNCTIONS);
    functions.forEach(_function => {
      this.pluginStore.addFunction(`${this.name}.${_function}`, this[_function]);
      this.functionsToRemove.push(`${this.name}.${_function}`);
    });

    this.localization(i18nInstance);
  }

  deactivate() {
    difference(Object.getOwnPropertyNames(ClueUIPlugin.prototype), INTERNAL_FUNCTIONS).forEach(_function =>
      this.pluginStore.removeFunction(`${this.name}.${_function}`)
    );

    this.functionsToRemove.forEach(name => this.pluginStore.removeFunction(name));
  }

  renderActionResult(_props: RenderActionResultProps) {
    return null;
  }

  renderFetcherResult(_props: RenderFetcherResultProps) {
    return null;
  }

  provider(): React.FC<PropsWithChildren<{}>> | null {
    return null;
  }

  setup(): void {}

  localization(_i18n: I18N): void {}

  support(): React.ReactNode {
    return null;
  }

  help(): React.ReactNode {
    return null;
  }

  settings(_section: 'admin' | 'local' | 'profile' | 'security'): React.ReactNode {
    return null;
  }

  integrations(): [string, () => React.ReactNode][] {
    return [];
  }

  documentation(md: string): string {
    return md;
  }
}

export default ClueUIPlugin;
