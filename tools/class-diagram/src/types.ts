export type NodeKind =
  | 'protocol'
  | 'abstract'
  | 'op'
  | 'op-leaf'
  | 'space'
  | 'space-leaf'
  | 'registry'
  | 'types';

export type EdgeType = 'inherits' | 'composes' | 'uses' | 'registers';

export interface FieldDef {
  name: string;
  type: string;
}

export interface NodeDef {
  id: string;
  kind: NodeKind;
  file: string;
  badge: string;
  desc: string;
  fields: FieldDef[];
  width?: number;
}

export interface EdgeDef {
  source: string;
  target: string;
  type: EdgeType;
}

export interface GroupState {
  id: string;
  memberIds: string[];
  position: { x: number; y: number };
  originPosition: { x: number; y: number };
  memberPositions: Record<string, { x: number; y: number }>;
}
