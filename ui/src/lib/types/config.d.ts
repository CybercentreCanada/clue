import type { ClassificationDefinition } from 'lib/utils/classificationParser';

export interface ApiType {
  configuration: {
    auth: {
      oauth_providers: string[];
    };
    system: {
      version: string;
      branch: string;
      commit: string;
    };
    ui: {
      apps: any[];
    };
  };
  c12nDef: ClassificationDefinition;
}
