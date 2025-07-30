import { LUCENE_OPERATORS } from '..';
import { TuiPhraseToken } from '../..';
import PhraseConsumer from '../../TuiPhraseConsumer';
import LuceneLexer from '../LuceneLexer';

export const LUCENE_OPERATOR_REGEX = new RegExp(`^(${LUCENE_OPERATORS.join('|')})$`);

export default class OperatorConsumer extends PhraseConsumer<LuceneLexer> {
  lock(lexer: LuceneLexer): boolean {
    if (lexer.testBehind(LUCENE_OPERATOR_REGEX)) {
      return true;
    }
    return false;
  }

  consume(lexer: LuceneLexer): TuiPhraseToken {
    return {
      value: this.bufferValue(),
      startIndex: lexer.start(),
      endIndex: lexer.end(),
      type: 'operator'
    };
  }
}
