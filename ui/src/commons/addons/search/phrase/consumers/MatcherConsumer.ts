import { TuiPhraseToken } from 'commons/addons/controls/phrase';
import PhraseConsumer from 'commons/addons/controls/phrase/TuiPhraseConsumer';
import { MATCHERS, SEPARATORS } from '../../models/TuiSearchTerms';
import SearchPhraseLexer from '../SearchPhraseLexer';

const MATCHER_GROUP_TYPES = {
  0: 'matcher',
  1: 'matcher.column',
  2: 'whitespace',
  3: 'matcher.operator',
  4: 'whitespace',
  5: 'matcher.value'
};

const MATCHER_REGEX = new RegExp(`([^\\s]+)(\\s+)(${MATCHERS.join('|')})(\\s+)(.*)`);

export default class MatcherConsumer extends PhraseConsumer<SearchPhraseLexer> {
  private matcherValue: string[] = [];

  public init(buffer: string[]): void {
    super.init(buffer);
    this.matcherValue = [];
  }

  public append(next: string): void {
    this.matcherValue.push(next);
  }

  public lock(lexer: SearchPhraseLexer): boolean {
    if (lexer.behindEndsWithAny(false, ...MATCHERS.map(m => ` ${m} `))) {
      return true;
    }
    return false;
  }

  public consume(lexer: SearchPhraseLexer): TuiPhraseToken {
    if (lexer.aheadStartsWithAny(true, ...SEPARATORS) || lexer.aheadIsEmpty(true)) {
      const input = this.bufferValue() + this.matcherValue.join('');
      const result = MATCHER_REGEX.exec(input);

      // TODO: use match index to parse out extranuous text from input.
      // TODO: parse it out as a Word.

      let startIndex = lexer.start();
      let endIndex = lexer.end();
      const tokens = result.map((value, i) => {
        if (i > 0) {
          endIndex = startIndex + value.length - 1;
        }
        const token = {
          type: MATCHER_GROUP_TYPES[i],
          value,
          startIndex: startIndex,
          endIndex: endIndex
        };
        if (i > 0) {
          startIndex = endIndex + 1;
        }
        return token;
      });

      const token = tokens.at(0);
      return { ...token, children: tokens.slice(1) };
    }
    return null;
  }
}
