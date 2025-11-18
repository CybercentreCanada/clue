const LUCENE_TERM_TYPE = ['term', 'term.field', 'term.separator', 'whitespace', 'term.value'];

export type LuceneTermType = (typeof LUCENE_TERM_TYPE)[number];

export const LUCENE_OPERATORS = ['AND', 'OR', 'NOT'] as const;

export type LuceneOperator = (typeof LUCENE_OPERATORS)[number];
