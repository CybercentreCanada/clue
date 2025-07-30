import { TuiPhraseToken } from '../..';
import PhraseConsumer from '../../TuiPhraseConsumer';
import PhraseLexer from '../../TuiPhraseLexer';

export default class WhitespaceConsumer extends PhraseConsumer<PhraseLexer> {
  public lock(lexer: PhraseLexer): boolean {
    return lexer.bufferValue().match(/\s/) && lexer.ahead(1) !== ' ';
  }

  public consume(lexer: PhraseLexer): TuiPhraseToken {
    if (lexer.ahead(1) !== ' ') {
      return {
        type: 'whitespace',
        startIndex: lexer.start(),
        endIndex: lexer.end(),
        value: this._buffer.join('')
      };
    }
    return null;
  }
}
