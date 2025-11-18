import { TuiPhraseToken } from '../..';
import PhraseConsumer from '../../TuiPhraseConsumer';
import PhraseLexer from '../../TuiPhraseLexer';

export default class WordConsumer extends PhraseConsumer<PhraseLexer> {
  public lock(lexer: PhraseLexer): boolean {
    return !lexer.bufferValue().match(/\s/) && (lexer.ahead(1) === ' ' || lexer.ahead(1) === '');
  }

  public consume(lexer: PhraseLexer): TuiPhraseToken {
    if (lexer.ahead(1) === ' ' || lexer.aheadIsEmpty(true)) {
      return {
        type: 'word',
        startIndex: lexer.start(),
        endIndex: lexer.end(),
        value: this._buffer.join('')
      };
    }
    return null;
  }
}
