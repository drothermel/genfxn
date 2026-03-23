import { useDiagramStore } from '../store';
import { NODE_DEFS } from '../data/nodes';
import { getRelatedNodes } from '../hooks';
import { KIND_COLORS } from '../theme';

const RELATION_SECTIONS = [
  { key: 'inherits', label: 'Inherits' },
  { key: 'inheritedBy', label: 'Inherited by' },
  { key: 'composes', label: 'Composes' },
  { key: 'composedBy', label: 'Composed by' },
  { key: 'uses', label: 'Uses' },
  { key: 'usedBy', label: 'Used by' },
  { key: 'registers', label: 'Registers' },
  { key: 'registeredBy', label: 'Registered by' },
] as const;

export function DetailPanel() {
  const selectedNodeId = useDiagramStore((s) => s.selectedNodeId);
  const selectNode = useDiagramStore((s) => s.selectNode);

  if (!selectedNodeId) return null;

  const nodeDef = NODE_DEFS.find((n) => n.id === selectedNodeId);
  if (!nodeDef) return null;

  const related = getRelatedNodes(selectedNodeId);
  const color = KIND_COLORS[nodeDef.kind];

  return (
    <div className="fixed right-0 top-12 bottom-0 w-[360px] bg-[#18181f] border-l border-[#2a2a35] z-50 overflow-y-auto p-5 animate-slide-in">
      <button
        type="button"
        className="absolute top-4 right-4 text-[#8888a0] hover:text-[#e4e4eb] text-lg bg-transparent border-none cursor-pointer"
        onClick={() => selectNode(null)}
      >
        &times;
      </button>

      <div className="font-mono text-[10.5px] text-[#8888a0] bg-[rgba(255,255,255,0.04)] px-2 py-0.5 rounded inline-block mb-2.5">
        {nodeDef.file}
      </div>

      <h2 className="font-mono text-[15px] font-semibold mb-1" style={{ color }}>
        {nodeDef.id}
      </h2>

      <div className="text-[11px] text-[#8888a0] uppercase tracking-wider mb-3.5">
        {nodeDef.kind}
      </div>

      <p className="text-[12.5px] leading-relaxed text-[#e4e4eb] mb-4">
        {nodeDef.desc}
      </p>

      {nodeDef.fields.length > 0 && (
        <>
          <div className="text-[10px] font-bold uppercase tracking-wider text-[#8888a0] mt-3.5 mb-1.5">
            Fields
          </div>
          {nodeDef.fields.map((f) => (
            <div key={f.name} className="flex gap-2 items-baseline py-0.5 font-mono text-[11px]">
              <span className="text-[#e4e4eb]">{f.name}</span>
              {f.type && <span className="text-[#6ee7b7]">{f.type}</span>}
            </div>
          ))}
        </>
      )}

      {RELATION_SECTIONS.map(({ key, label }) => {
        const items = related[key];
        if (items.length === 0) return null;
        return (
          <div key={key}>
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#8888a0] mt-3.5 mb-1.5">
              {label}
            </div>
            {items.map((id) => (
              <div
                key={id}
                className="py-1 text-[11.5px] flex gap-1.5 items-center cursor-pointer hover:text-[#6ee7b7] transition-colors"
                onClick={() => selectNode(id)}
              >
                <span className="text-[#8888a0] text-[10px]">→</span>
                <span>{id}</span>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
