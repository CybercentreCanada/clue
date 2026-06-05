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
      replicate?: boolean;
      apps: any[];
    };
  };
  c12nDef: ClassificationDefinition;
}
