import { TuiPhraseToken } from '../..';
import PhraseConsumer from '../../TuiPhraseConsumer';
import LuceneLexer from '../LuceneLexer';

const TERM_GROUP_TYPE = {
  0: 'term',
  1: 'term.field',
  2: 'term.separator',
  3: 'whitespace',
  4: 'term.value'
};

export const SINGLE_TERM = /^(\S+)(:)(\s*)([^"\s]*)$/;
export const PHRASE_TERM = /^(\S+)(:)(\s*)("[^"]+")$/;

// https://lucene.apache.org/core/2_9_4/queryparsersyntax.html
export default class TermConsumer extends PhraseConsumer<LuceneLexer> {
  public lock(lexer: LuceneLexer): boolean {
    if (lexer.testBehind(/\S+:$/)) {
      return true;
    }
    return false;
  }

  public consume(lexer: LuceneLexer): TuiPhraseToken {
    let regex = null;
    if (lexer.testBehind(PHRASE_TERM)) {
      regex = PHRASE_TERM;
    } else if (lexer.testBehind(SINGLE_TERM) && (lexer.aheadStartsWithAny(false, ' ') || lexer.aheadIsEmpty(true))) {
      regex = SINGLE_TERM;
    }

    if (regex) {
      const result = regex.exec(lexer.bufferValue());

      let startIndex = lexer.start();
      let endIndex = lexer.end();
      const tokens = result
        .map((value, i) => {
          if (!value) {
            return null;
          }
          if (i > 0) {
            endIndex = startIndex + value.length - 1;
          }
          const token = {
            type: TERM_GROUP_TYPE[i],
            value,
            startIndex,
            endIndex
          };
          if (i > 0) {
            startIndex = endIndex + 1;
          }
          return token;
        })
        .filter(t => t);

      return {
        ...tokens.at(0),
        children: tokens.slice(1)
      };
    }

    return null;
  }
}
