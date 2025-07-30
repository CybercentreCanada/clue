import { TuiPhraseToken } from 'commons/addons/controls/phrase';
import PhraseConsumer from 'commons/addons/controls/phrase/TuiPhraseConsumer';
import { SEPARATORS } from '../../models/TuiSearchTerms';
import SearchPhraseLexer from '../SearchPhraseLexer';

// const SEPARATOR_REGEX = new RegExp(SEPARATORS.map(s => s))

export default class SeparatorConsumer extends PhraseConsumer<SearchPhraseLexer> {
  public lock(lexer: SearchPhraseLexer): boolean {
    if (lexer.behindEndsWithAny(false, ...SEPARATORS.map(s => ` ${s}`)) && lexer.ahead(1) === ' ') {
      return true;
    }
    return false;
  }

  public consume(lexer: SearchPhraseLexer): TuiPhraseToken {
    return {
      type: 'separator',
      value: lexer.bufferValue(),
      startIndex: lexer.start(),
      endIndex: lexer.end()
    };
  }
}
