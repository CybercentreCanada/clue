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
  pluginId?: string;
  result: FetcherResult;
}

export interface RenderActionResultProps extends RenderResultProps {
  pluginId?: string;
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
      this.pluginStore.addFunction(`${this.name}.${_function}`, this[_function]);
      this.functionsToRemove.push(`${this.name}.${_function}`);
    });

    this.pluginStore.addFunction(`${this.name}.${'getPluginName'}`, this.getPluginName);
    // explicityly add render functions to plugin store if they have been implemented
    if (this.actionResult) {
      this.pluginStore.addFunction(`${this.name}.${'actionResult'}`, this.actionResult);
    }
    if (this.fetcherResult) {
      this.pluginStore.addFunction(`${this.name}.${'fetcherResult'}`, this.fetcherResult);
    }

    this.localization(i18nInstance);
  }

  deactivate() {
    difference(Object.getOwnPropertyNames(ClueUIPlugin.prototype), INTERNAL_FUNCTIONS).forEach(_function =>
      this.pluginStore.removeFunction(`${this.name}.${_function}`)
    );

    // explicityly remove render functions to plugin store if they have been implemented
    if (this.actionResult) {
      this.pluginStore.removeFunction(`${this.name}.${'actionResult'}`);
    }
    if (this.fetcherResult) {
      this.pluginStore.removeFunction(`${this.name}.${'fetcherResult'}`);
    }

    this.functionsToRemove.forEach(name => this.pluginStore.removeFunction(name));
  }

  actionResult?(_props: RenderActionResultProps): ReactNode;

  fetcherResult?(_props: RenderFetcherResultProps): ReactNode;

  localization(_i18n: I18N): void {}

  exampleInput(): any {
    return undefined;
  }

  editorLanguage(): string {
    /**
     * Editor language
     */
    return undefined;
  }

  documentation(): string {
    return null;
  }
}

export default ClueUIPlugin;
