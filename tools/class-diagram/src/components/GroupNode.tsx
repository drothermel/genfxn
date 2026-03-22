import { memo, useCallback } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { useDiagramStore } from '../store';

const MAX_VISIBLE = 5;

function GroupNodeInner({ data }: NodeProps) {
  const { groupId, memberNames, memberColors, badge } = data as {
    groupId: string;
    memberNames: string[];
    memberColors: string[];
    badge: string;
  };

  const expandGroup = useDiagramStore((s) => s.expandGroup);

  const handleExpand = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      expandGroup(groupId);
    },
    [groupId, expandGroup],
  );

  const visibleNames = memberNames.slice(0, MAX_VISIBLE);
  const extraCount = memberNames.length - MAX_VISIBLE;

  return (
    <div className="group-card">
      <Handle type="target" position={Position.Top} className="!opacity-0 !w-0 !h-0 !min-w-0 !min-h-0" />
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-[#2a2a35]">
        <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-[3px] text-[#6ee7b7] border border-[#6ee7b733] bg-[rgba(255,255,255,0.06)]">
          {badge}
        </span>
      </div>

      <div className="px-3 py-1.5">
        {visibleNames.map((name, i) => (
          <div key={name} className="py-0.5 font-mono text-[10.5px]">
            <span style={{ color: memberColors[i] }}>{name}</span>
          </div>
        ))}
        {extraCount > 0 && (
          <div className="text-[10px] text-[#8888a0] py-0.5">+{extraCount} more</div>
        )}
      </div>

      <div
        className="text-[9px] text-[#8888a0] px-3 py-1 cursor-pointer hover:text-[#6ee7b7] transition-colors"
        onClick={handleExpand}
      >
        click to expand
      </div>
      <Handle type="source" position={Position.Bottom} className="!opacity-0 !w-0 !h-0 !min-w-0 !min-h-0" />
    </div>
  );
}

export const GroupNode = memo(GroupNodeInner);
