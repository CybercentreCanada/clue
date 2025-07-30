export type TuiPhraseAnalysis = {
  cursor: number;
  parentIndex: number;
  parent: TuiPhraseToken;
  currentIndex: number;
  current: TuiPhraseToken;
  suggest: {
    token: TuiPhraseToken;
    parent: TuiPhraseToken;
    value: string;
  };
  tokens?: TuiPhraseToken[];
};

export type TuiPhraseToken = {
  value: string;
  startIndex: number;
  endIndex: number;
  type?: string;
  children?: TuiPhraseToken[];
};

export type TuiPhraseSuggester = {
  suggest: (phrase: TuiPhraseAnalysis) => string[];
};

export type TuiPhraseSuggestorValue = {
  field: string;
  values: string[];
};

export class TuiPhraseBuffer {
  constructor(type?: string) {
    this.type = type;
  }

  private type: string;

  private startIndex: number = 0;

  private endIndex: number = -1;

  private buffer: string[] = [];

  public init(startIndex: number, buffer?: string[]): TuiPhraseBuffer {
    this.buffer = buffer ? [...buffer] : [];
    this.startIndex = startIndex;
    this.endIndex = startIndex + (buffer ? buffer.length : 0);
    return this;
  }

  public append(value: string): TuiPhraseBuffer {
    this.buffer.push(value);
    this.endIndex += value.length;
    return this;
  }

  public value(): string {
    return this.buffer.join('');
  }

  public start(index?: number): number {
    if (index !== undefined) {
      this.startIndex = index;
    }
    return this.startIndex;
  }

  public end(index?: number): number {
    if (index !== undefined) {
      this.endIndex = index;
    }
    return this.endIndex;
  }

  public token(): TuiPhraseToken {
    return this.endIndex > 0
      ? {
          type: this.type,
          value: this.value(),
          startIndex: this.startIndex,
          endIndex: this.endIndex - 1
        }
      : null;
  }
}
