import TuiPhraseConsumer from 'commons/addons/controls/phrase/TuiPhraseConsumer';
import PhraseLexer from 'commons/addons/controls/phrase/TuiPhraseLexer';
import MatcherConsumer from './consumers/MatcherConsumer';
import SeparatorConsumer from './consumers/SeparatorConsumer';

export default class SearchPhraseLexer extends PhraseLexer {
  public consumers(): TuiPhraseConsumer<PhraseLexer>[] {
    return [new MatcherConsumer(), new SeparatorConsumer()];
  }
}
