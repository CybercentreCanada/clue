import { TuiPhraseAnalysis, TuiPhraseSuggester, TuiPhraseSuggestorValue } from '..';

export default class LuceneSuggester implements TuiPhraseSuggester {
  private hasValues = false;

  constructor(
    private fields: string[],
    private values: TuiPhraseSuggestorValue[] = []
  ) {
    this.hasValues = values && values.length > 0;
  }

  suggest(phrase: TuiPhraseAnalysis): string[] {
    const filter = phrase.suggest.value.toLocaleLowerCase();
    const token = phrase.suggest.token;
    const parent = phrase.suggest.parent;
    const hasChildren = parent.children && parent.children.length > 0;

    if (token.type === 'word') {
      return this.fields.filter(f => f.toLocaleLowerCase().indexOf(filter) > -1);
    }

    if (token.type === 'term.field') {
      return this.fields.filter(f => f.toLocaleLowerCase().indexOf(filter) > -1);
    }

    if ((token.type === 'term.value' || token.type === 'term.separator') && this.hasValues && hasChildren) {
      const _filter = token.type === 'term.separator' ? '' : filter;
      const _field = parent.children.find(c => c.type === 'term.field');
      const _values = this.values.find(v => v.field.toLocaleLowerCase() === _field.value.toLocaleLowerCase());
      const _sugg = _values ? _values.values.filter(v => v.toLocaleLowerCase().indexOf(_filter) > -1) : [];
      return _sugg;
    }

    return this.fields;
  }
}
