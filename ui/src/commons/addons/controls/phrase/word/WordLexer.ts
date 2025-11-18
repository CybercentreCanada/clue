import TuiPhraseConsumer from '../TuiPhraseConsumer';
import { default as PhraseLexer, default as TuiPhraseLexer } from '../TuiPhraseLexer';
import WhitespaceConsumer from './consumers/WhitespaceConsumer';
import WordConsumer from './consumers/WordConsumer';

export default class WordLexer extends PhraseLexer {
  public consumers(): TuiPhraseConsumer<TuiPhraseLexer>[] {
    return [new WordConsumer(), new WhitespaceConsumer()];
  }
}
