import { TuiPhraseToken } from '.';
import TuiPhraseLexer from './TuiPhraseLexer';

export default abstract class TuiPhraseConsumer<L extends TuiPhraseLexer> {
  protected _buffer = [];

  public reset(): void {
    this._buffer = [];
  }

  public init(buffer: string[], lexer?: L): void {
    this._buffer = [...buffer];
  }

  public append(next: string, lexer?: L): void {
    this._buffer.push(next);
  }

  public bufferValue(): string {
    return this._buffer.join('');
  }

  public endsWithAny(...values: string[]): boolean {
    const _bufferValue = this.bufferValue();
    return values.some(v => _bufferValue.endsWith(v));
  }

  public test(regex: RegExp): boolean {
    return regex.test(this.bufferValue());
  }

  abstract lock(lexer: L): boolean;

  abstract consume(lexer: L): TuiPhraseToken;
}
