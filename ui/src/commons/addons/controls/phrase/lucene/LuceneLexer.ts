import TuiPhraseConsumer from '../TuiPhraseConsumer';
import { default as PhraseLexer, default as TuiPhraseLexer } from '../TuiPhraseLexer';
import WhitespaceConsumer from '../word/consumers/WhitespaceConsumer';
import WordConsumer from '../word/consumers/WordConsumer';
import OperatorConsumer from './consumers/OperatorConsumer';
import TermConsumer from './consumers/TermConsumer';

export default class LuceneLexer extends PhraseLexer {
  consumers(): TuiPhraseConsumer<TuiPhraseLexer>[] {
    return [new TermConsumer(), new OperatorConsumer(), new WordConsumer(), new WhitespaceConsumer()];
  }
}
