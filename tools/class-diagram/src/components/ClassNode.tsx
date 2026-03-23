import { memo, useCallback } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { useDiagramStore } from '../store';

const MAX_FIELDS = 3;

function ClassNodeInner({ data }: NodeProps) {
  const { badge, id, color, fields } = data as {
    badge: string;
    id: string;
    color: string;
    fields: { name: string; type: string }[];
  };

  const hideNode = useDiagramStore((s) => s.hideNode);

  const handleHide = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      hideNode(id);
    },
    [id, hideNode],
  );

  const visibleFields = fields.slice(0, MAX_FIELDS);
  const extraCount = fields.length - MAX_FIELDS;

  return (
    <div className="node-card group/node">
      <Handle type="target" position={Position.Top} className="!opacity-0 !w-0 !h-0 !min-w-0 !min-h-0" />
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-[#2a2a35]">
        <span
          className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-[3px]"
          style={{ color, border: `1px solid ${color}33`, background: 'rgba(255,255,255,0.06)' }}
        >
          {badge}
        </span>
        <span className="font-mono text-xs font-semibold" style={{ color }}>
          {id}
        </span>
        <button
          type="button"
          className="ml-auto opacity-0 group-hover/node:opacity-100 transition-opacity text-[#8888a0] hover:text-[#e4e4eb] text-[10px] cursor-pointer leading-none"
          onClick={handleHide}
          title="Hide node"
        >
          ✕
        </button>
      </div>

      {visibleFields.length > 0 && (
        <div className="px-3 py-1.5">
          {visibleFields.map((f) => (
            <div key={f.name} className="flex gap-1.5 items-baseline py-0.5 font-mono text-[10.5px]">
              <span className="text-[#e4e4eb]">{f.name}</span>
              {f.type && <span className="text-[#6ee7b7]">{f.type}</span>}
            </div>
          ))}
          {extraCount > 0 && (
            <div className="text-[10px] text-[#8888a0] py-0.5">+{extraCount} more</div>
          )}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!opacity-0 !w-0 !h-0 !min-w-0 !min-h-0" />
    </div>
  );
}

export const ClassNode = memo(ClassNodeInner);
