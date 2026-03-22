import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { GroupState } from './types';
import { computeLayout, type LayoutDirection } from './layout';

interface DiagramState {
  // Persisted
  positionOverrides: Record<string, { x: number; y: number }>;
  groups: GroupState[];
  hiddenFilters: string[];
  viewport: { x: number; y: number; zoom: number } | null;

  // Transient
  selectedNodeId: string | null;
  multiSelectedIds: string[];
  layoutVersion: number;

  // Actions
  setNodePosition: (id: string, pos: { x: number; y: number }) => void;
  setViewport: (vp: { x: number; y: number; zoom: number }) => void;
  toggleFilter: (filter: string) => void;
  selectNode: (id: string | null) => void;
  setMultiSelected: (ids: string[]) => void;
  createGroup: (
    memberIds: string[],
    memberPositions: Record<string, { x: number; y: number }>,
    boundingBox: { x: number; y: number },
  ) => string;
  expandGroup: (groupId: string) => void;
  autoLayout: (direction?: LayoutDirection) => void;
}

let groupCounter = 0;

function getInitialPositions(): Record<string, { x: number; y: number }> {
  // Check if localStorage already has saved state
  try {
    const stored = localStorage.getItem('class-diagram-state');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed?.state?.positionOverrides && Object.keys(parsed.state.positionOverrides).length > 0) {
        return parsed.state.positionOverrides;
      }
    }
  } catch {}
  // First load: compute layout
  return computeLayout('TB');
}

export const useDiagramStore = create<DiagramState>()(
  persist(
    (set, get) => ({
      positionOverrides: getInitialPositions(),
      groups: [],
      hiddenFilters: [],
      viewport: null,
      selectedNodeId: null,
      multiSelectedIds: [],
      layoutVersion: 0,

      setNodePosition: (id, pos) =>
        set((s) => ({
          positionOverrides: { ...s.positionOverrides, [id]: pos },
        })),

      setViewport: (vp) => set({ viewport: vp }),

      toggleFilter: (filter) =>
        set((s) => {
          const filters = [...s.hiddenFilters];
          const idx = filters.indexOf(filter);
          if (idx >= 0) filters.splice(idx, 1);
          else filters.push(filter);
          return { hiddenFilters: filters };
        }),

      selectNode: (id) => set({ selectedNodeId: id }),

      setMultiSelected: (ids) => set({ multiSelectedIds: ids }),

      createGroup: (memberIds, memberPositions, boundingBox) => {
        const id = `__group_${++groupCounter}`;
        const group: GroupState = {
          id,
          memberIds,
          position: boundingBox,
          originPosition: boundingBox,
          memberPositions,
        };
        set((s) => ({
          groups: [...s.groups, group],
          positionOverrides: { ...s.positionOverrides, [id]: boundingBox },
          multiSelectedIds: [],
          selectedNodeId: null,
        }));
        return id;
      },

      autoLayout: (direction = 'TB') => {
        const positions = computeLayout(direction);
        set((s) => ({
          positionOverrides: positions,
          groups: [],
          viewport: null,
          selectedNodeId: null,
          multiSelectedIds: [],
          layoutVersion: s.layoutVersion + 1,
        }));
      },

      expandGroup: (groupId) => {
        const state = get();
        const group = state.groups.find((g) => g.id === groupId);
        if (!group) return;

        const currentPos = state.positionOverrides[groupId] ?? group.position;
        const dx = currentPos.x - group.originPosition.x;
        const dy = currentPos.y - group.originPosition.y;

        const newOverrides = { ...state.positionOverrides };
        for (const memberId of group.memberIds) {
          const orig = group.memberPositions[memberId];
          if (orig) {
            newOverrides[memberId] = { x: orig.x + dx, y: orig.y + dy };
          }
        }
        delete newOverrides[groupId];

        set({
          groups: state.groups.filter((g) => g.id !== groupId),
          positionOverrides: newOverrides,
          selectedNodeId: state.selectedNodeId === groupId ? null : state.selectedNodeId,
        });
      },
    }),
    {
      name: 'class-diagram-state',
      partialize: (state) => ({
        positionOverrides: state.positionOverrides,
        groups: state.groups,
        hiddenFilters: state.hiddenFilters,
        viewport: state.viewport,
      }),
    },
  ),
);
