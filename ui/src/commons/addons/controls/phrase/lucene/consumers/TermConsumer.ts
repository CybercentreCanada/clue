import { TuiPhraseBuffer, TuiPhraseToken } from '../..';
import PhraseConsumer from '../../TuiPhraseConsumer';
import LuceneLexer from '../LuceneLexer';

// https://lucene.apache.org/core/2_9_4/queryparsersyntax.html
export default class TermConsumer extends PhraseConsumer<LuceneLexer> {
  private term: 'single' | 'phrase' = 'single';

  private complete: boolean;

  private context: 'field' | 'separator' | 'whitespace' | 'value';

  private buffers: { field: TuiPhraseBuffer; separator: TuiPhraseBuffer; value: TuiPhraseBuffer };

  public init(buffer: string[], lexer: LuceneLexer): void {
    super.init(buffer);
    this.complete = false;
    this.term = 'single';
    this.context = 'field';
    this.buffers = {
      field: new TuiPhraseBuffer('term.field'),
      separator: new TuiPhraseBuffer('term.separator'),
      value: new TuiPhraseBuffer('term.value')
    };
    this.buffers.field.init(lexer.start(), buffer);
  }

  public append(next: string, lexer: LuceneLexer): void {
    super.append(next);

    // track context switch.
    let newContext = false;

    // track context switch into phrase value.
    let newPhrase = false;

    // determine which buffer to write to.
    if (next === ':') {
      this.context = 'separator';
      newContext = true;
    } else if (this.context === 'separator') {
      this.context = 'value';
      newContext = true;
      if (next === '"') {
        this.term = 'phrase';
        newPhrase = true;
      }
    }

    // keep track of position for each buffer.
    if (newContext) {
      this.buffers[this.context].init(lexer.end());
    }

    // write to selected buffer.
    this.buffers[this.context].append(next);

    // determine if the term is complete.
    if (this.term === 'single') {
      // single term
      this.complete = lexer.aheadStartsWithAny(false, ' ');
    } else if (!newPhrase) {
      // phrase term.
      this.complete = next === '"' && !lexer.testBehind(/\\"$/);
    }
  }

  public lock(lexer: LuceneLexer): boolean {
    if (lexer.testBehind(/\S+/) && lexer.aheadStartsWithAny(false, ':')) {
      return true;
    }
    return false;
  }

  public consume(lexer: LuceneLexer): TuiPhraseToken {
    if (lexer.aheadIsEmpty() || this.complete) {
      return {
        type: 'term',
        startIndex: lexer.start(),
        endIndex: lexer.end(),
        value: this.bufferValue(),
        children: [
          this.buffers.field.token(), //
          this.buffers.separator.token(),
          this.buffers.value.token()
        ].filter(t => !!t)
      };
    }
    return null;
  }
}
