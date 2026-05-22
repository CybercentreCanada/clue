export interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'select' | 'boolean';
  options?: string[];
  defaultValue?: unknown;
}

export interface BlockDefinition {
  id: string;
  label: string;
  category: string;
  icon?: string;
  description: string;
  configFields: ConfigField[];
  /** Python code template. Use {{key}} placeholders matching configField keys. */
  code: string;
  /**
   * If true this block is a control-flow wrapper (function def, if/elif/else,
   * try/except). Its `code` renders the opening statement and child steps are
   * indented inside the body. The code template should end with a `:` line.
   */
  isWrapper?: boolean;
}

export interface PipelineStep {
  instanceId: string;
  definitionId: string;
  config: Record<string, unknown>;
  /** Child steps that are indented inside this wrapper block. */
  children: PipelineStep[];
}

export interface PipelineState {
  indicatorType: string;
  steps: PipelineStep[];
  selectedStepId: string | null;
}
