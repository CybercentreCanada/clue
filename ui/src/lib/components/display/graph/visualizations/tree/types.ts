import type { RawEntry } from 'lib/types/graph';

export interface Node extends RawEntry {
  level: number;
  parents: string[];
}

export interface Bundle {
  id: string;
  sources: Node[];
  destinations: Node[];
}
