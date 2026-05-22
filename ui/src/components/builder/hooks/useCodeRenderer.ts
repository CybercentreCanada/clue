import { BLOCK_DEFINITIONS } from '../data/blockDefinitions';
import type { PipelineStep } from '../types';

/**
 * Render a single block's code template, substituting `{{key}}` placeholders
 * with the step's configured values.
 */
export const renderBlockCode = (step: PipelineStep): string => {
  const def = BLOCK_DEFINITIONS.find(b => b.id === step.definitionId);
  if (!def) return `# Unknown block: ${step.definitionId}`;

  let code = def.code;

  for (const field of def.configFields) {
    const raw = step.config[field.key] ?? field.defaultValue ?? '';
    let rendered: string;

    if (field.type === 'boolean') {
      rendered = raw ? 'True' : 'False';
    } else if (field.key === 'supported_types') {
      rendered = String(raw)
        .split(',')
        .map(s => `"${s.trim()}"`)
        .join(', ');
    } else if (field.key === 'vars') {
      rendered = String(raw)
        .split('\n')
        .filter(Boolean)
        .map(line => {
          const [name, ...rest] = line.split('=');
          const defaultVal = rest.join('=');
          return `${name.trim()} = os.environ.get("${name.trim()}", "${defaultVal.trim()}")`;
        })
        .join('\n');
    } else if (field.key === 'types') {
      rendered = String(raw)
        .split(',')
        .map(s => `    "${s.trim()}": _enrich_default,`)
        .join('\n');
    } else if (field.key === 'return_type') {
      const val = String(raw).trim();
      rendered = val ? ` -> ${val}` : '';
    } else {
      rendered = String(raw);
    }

    code = code.replaceAll(`{{${field.key}}}`, rendered);
  }

  return code;
};

/**
 * Indent every line of `text` by `depth` levels (4 spaces each).
 */
const indent = (text: string, depth: number): string => {
  if (depth <= 0) return text;
  const prefix = '    '.repeat(depth);
  return text
    .split('\n')
    .map(line => (line.trim() ? prefix + line : line))
    .join('\n');
};

/**
 * Recursively render a step and its children, respecting indentation depth.
 */
const renderStep = (step: PipelineStep, depth: number): string => {
  const def = BLOCK_DEFINITIONS.find(b => b.id === step.definitionId);
  const code = renderBlockCode(step);
  const indented = indent(code, depth);

  if (def?.isWrapper && step.children.length > 0) {
    const childCode = step.children.map(child => renderStep(child, depth + 1)).join('\n\n');
    return `${indented}\n${childCode}`;
  }

  if (def?.isWrapper) {
    // Wrapper with no children yet — emit a pass placeholder
    return `${indented}\n${indent('pass', depth + 1)}`;
  }

  return indented;
};

/**
 * Render all pipeline steps into a single combined Python file.
 */
export const renderFullFile = (steps: PipelineStep[]): string => {
  if (steps.length === 0) return '# Empty pipeline — drag blocks from the catalogue to begin.\n';

  return steps
    .map((step, i) => {
      const def = BLOCK_DEFINITIONS.find(b => b.id === step.definitionId);
      const header = `# ── Step ${i + 1}: ${def?.label ?? step.definitionId} ${'─'.repeat(40)}`;
      return `${header}\n${renderStep(step, 0)}`;
    })
    .join('\n\n\n');
};
