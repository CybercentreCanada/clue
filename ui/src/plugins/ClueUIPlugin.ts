import i18nInstance from 'i18n';
import type { i18n as I18N } from 'i18next';
import type { ActionResult, FetcherResult } from 'lib/main';
import type { WithActionData } from 'lib/types/WithActionData';
import { difference } from 'lodash-es';
import type { ReactNode } from 'react';
import type { IPlugin, PluginStore } from 'react-pluggable';

const INTERNAL_FUNCTIONS = ['constructor', 'getPluginName', 'getDependencies', 'init', 'activate', 'deactivate'];

export type RenderResultProps = {
  result: WithActionData<ActionResult> | FetcherResult;
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
  public fetcherIds?: string[];

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
  getPluginFetcherIds(): string[] | undefined {
    return this.fetcherIds;
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
      const fn = (this as any)[_function];
      if (typeof fn === 'function') {
        this.pluginStore.addFunction(`${this.name}.${_function}`, fn.bind(this));
        this.functionsToRemove.push(`${this.name}.${_function}`);
      }
    });
    // explicitly add render functions to plugin store if they have been implemented
    if (this.actionResult) {
      this.pluginStore.addFunction(`${this.name}.actionResult`, this.actionResult.bind(this));
      this.functionsToRemove.push(`${this.name}.actionResult`);
    }
    if (this.fetcherResult) {
      this.pluginStore.addFunction(`${this.name}.fetcherResult`, this.fetcherResult.bind(this));
      this.functionsToRemove.push(`${this.name}.fetcherResult`);
    }

    this.localization(i18nInstance);
  }

  deactivate() {
    this.functionsToRemove.forEach(name => this.pluginStore.removeFunction(name));
    this.functionsToRemove = [];
  }

  actionResult?(_props: RenderActionResultProps): ReactNode;

  fetcherResult?(_props: RenderFetcherResultProps): ReactNode;

  localization(_i18n: I18N): void {}

  documentation(md: string): string {
    return md;
  }
}

export default ClueUIPlugin;
