import { useDiagramStore } from '../store';
import { KIND_COLORS, EDGE_COLORS } from '../theme';

const NODE_FILTERS = [
  { key: 'protocol', label: 'Protocol', color: KIND_COLORS.protocol },
  { key: 'abstract', label: 'Abstract', color: KIND_COLORS.abstract },
  { key: 'op', label: 'Op', color: KIND_COLORS.op },
  { key: 'space', label: 'Space', color: KIND_COLORS.space },
  { key: 'registry', label: 'Registry', color: KIND_COLORS.registry },
  { key: 'types', label: 'Types', color: KIND_COLORS.types },
];

const EDGE_FILTERS = [
  { key: 'edge-inherits', label: 'inherits', color: EDGE_COLORS.inherits, dashed: false },
  { key: 'edge-composes', label: 'composes', color: EDGE_COLORS.composes, dashed: false },
  { key: 'edge-uses', label: 'uses', color: EDGE_COLORS.uses, dashed: true },
  { key: 'edge-registers', label: 'registers', color: EDGE_COLORS.registers, dashed: true },
];

export function Legend() {
  const hiddenFilters = useDiagramStore((s) => s.hiddenFilters);
  const toggleFilter = useDiagramStore((s) => s.toggleFilter);

  return (
    <div className="flex gap-3.5 items-center ml-auto text-[11px] text-[#8888a0]">
      {NODE_FILTERS.map((f) => (
        <div
          key={f.key}
          className="flex gap-1.5 items-center cursor-pointer select-none transition-opacity"
          style={{ opacity: hiddenFilters.includes(f.key) ? 0.3 : 1 }}
          onClick={() => toggleFilter(f.key)}
        >
          <div className="w-2 h-2 rounded-full" style={{ background: f.color }} />
          {f.label}
        </div>
      ))}

      {EDGE_FILTERS.map((f) => (
        <div
          key={f.key}
          className="flex gap-1.5 items-center cursor-pointer select-none transition-opacity"
          style={{ opacity: hiddenFilters.includes(f.key) ? 0.3 : 1 }}
          onClick={() => toggleFilter(f.key)}
        >
          <div
            className="w-4 h-0"
            style={{
              borderTop: f.dashed ? `2px dashed ${f.color}` : `2px solid ${f.color}`,
            }}
          />
          {f.label}
        </div>
      ))}
    </div>
  );
}
