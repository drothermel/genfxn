import { memo } from 'react';
import { useInternalNode, type EdgeProps } from '@xyflow/react';

/** Compute the point on a rectangle's border closest to an external point */
function getClosestBorderPoint(
  nodeX: number,
  nodeY: number,
  nodeW: number,
  nodeH: number,
  targetX: number,
  targetY: number,
): { x: number; y: number } {
  const cx = nodeX + nodeW / 2;
  const cy = nodeY + nodeH / 2;
  const dx = targetX - cx;
  const dy = targetY - cy;

  if (dx === 0 && dy === 0) return { x: cx, y: cy };

  const halfW = nodeW / 2;
  const halfH = nodeH / 2;

  // Scale factor to reach the border
  const scaleX = halfW / Math.abs(dx || 1);
  const scaleY = halfH / Math.abs(dy || 1);
  const scale = Math.min(scaleX, scaleY);

  return {
    x: cx + dx * scale,
    y: cy + dy * scale,
  };
}

function FloatingEdgeInner({
  id,
  source,
  target,
  style,
  markerEnd,
}: EdgeProps) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);

  if (!sourceNode || !targetNode) return null;

  const sourceW = sourceNode.measured?.width ?? 150;
  const sourceH = sourceNode.measured?.height ?? 40;
  const targetW = targetNode.measured?.width ?? 150;
  const targetH = targetNode.measured?.height ?? 40;

  const sourceCx = sourceNode.internals.positionAbsolute.x + sourceW / 2;
  const sourceCy = sourceNode.internals.positionAbsolute.y + sourceH / 2;
  const targetCx = targetNode.internals.positionAbsolute.x + targetW / 2;
  const targetCy = targetNode.internals.positionAbsolute.y + targetH / 2;

  const start = getClosestBorderPoint(
    sourceNode.internals.positionAbsolute.x,
    sourceNode.internals.positionAbsolute.y,
    sourceW,
    sourceH,
    targetCx,
    targetCy,
  );

  const end = getClosestBorderPoint(
    targetNode.internals.positionAbsolute.x,
    targetNode.internals.positionAbsolute.y,
    targetW,
    targetH,
    sourceCx,
    sourceCy,
  );

  // Bezier control point: slight curve perpendicular to the line
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const mx = (start.x + end.x) / 2;
  const my = (start.y + end.y) / 2;
  const cx = mx - dy * 0.08;
  const cy = my + dx * 0.08;

  const path = `M${start.x},${start.y} Q${cx},${cy} ${end.x},${end.y}`;

  return (
    <path
      id={id}
      d={path}
      fill="none"
      className="react-flow__edge-path"
      style={style}
      markerEnd={markerEnd as string}
    />
  );
}

export const FloatingEdge = memo(FloatingEdgeInner);
