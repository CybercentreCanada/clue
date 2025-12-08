import type { JSONSchema7 } from 'json-schema';

export interface ActionContextInformation {
  url?: string;
  timestamp?: string;
  [key: string]: any;
}

export interface ActionDefinition {
  accept_multiple?: boolean;
  action_icon?: string;
  classification: string;
  extra_schema?: JSON;
  format?: string;
  id: string;
  name: string;
  params: JSONSchema7;
  summary?: string;
  supported_types?: string[];
}

export interface ActionResult<T = any> {
  outcome: 'success' | 'failure';
  summary?: string;
  output?: T;
  format?: string;
  link?: string;
}

export type ActionDefinitionsResponse = { [type: string]: ActionDefinition };
