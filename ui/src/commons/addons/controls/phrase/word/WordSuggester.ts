import { TuiPhraseAnalysis, TuiPhraseSuggester } from '..';

export default class WordSuggestor implements TuiPhraseSuggester {
  constructor(private suggestions: string[]) {}

  public suggest(phrase: TuiPhraseAnalysis): string[] {
    return this.suggestions.filter(s => s.indexOf(phrase.suggest.value) > -1);
  }
}
