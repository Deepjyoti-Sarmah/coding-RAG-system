import { EXAMPLE_GRAPH } from "../data/content";

const NODE_W = 108;
const NODE_H = 36;

function nodeCenter(n) {
  return { x: n.x + NODE_W / 2, y: n.y + NODE_H / 2 };
}

function edgePath(from, to) {
  const a = nodeCenter(from);
  const b = nodeCenter(to);
  if (Math.abs(a.y - b.y) < 4) {
    // same row — straight connector between the two closest edges
    const x1 = a.x < b.x ? from.x + NODE_W : from.x;
    const x2 = a.x < b.x ? to.x : to.x + NODE_W;
    return `M ${x1} ${a.y} L ${x2 - (a.x < b.x ? 10 : -10)} ${a.y}`;
  }
  // different row — orthogonal-ish curve from bottom/top edge
  const startX = from.x + NODE_W / 2;
  const startY = a.y < b.y ? from.y + NODE_H : from.y;
  const endX = to.x + NODE_W / 2;
  const endY = a.y < b.y ? to.y : to.y + NODE_H;
  const midY = (startY + endY) / 2;
  return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
}

export default function ExampleGraph() {
  const { nodes, edges } = EXAMPLE_GRAPH;
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

  return (
    <figure className="w-full">
      <svg
        viewBox="0 0 340 170"
        className="w-full max-w-[380px]"
        role="img"
        aria-label="Symbol graph fragment across auth.ts and api.ts: login calls createAuth, run calls login"
      >
        <defs>
          <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 Z" fill="var(--color-blueprint)" />
          </marker>
        </defs>

        {edges.map((e) => {
          const from = byId[e.from];
          const to = byId[e.to];
          const d = edgePath(from, to);
          const a = nodeCenter(from);
          const b = nodeCenter(to);
          const midX = (a.x + b.x) / 2;
          const midY = (a.y + b.y) / 2 - (a.y === b.y ? 8 : 0);
          return (
            <g key={`${e.from}-${e.to}`}>
              <path
                d={d}
                fill="none"
                stroke="var(--color-blueprint)"
                strokeWidth="1.5"
                markerEnd="url(#arrow)"
              />
              <text
                x={midX}
                y={midY}
                textAnchor="middle"
                className="fill-blueprint font-mono"
                fontSize="9"
              >
                {e.kind}
              </text>
            </g>
          );
        })}

        {nodes.map((n) => (
          <g key={n.id}>
            <rect
              x={n.x}
              y={n.y}
              width={NODE_W}
              height={NODE_H}
              rx="3"
              fill="var(--color-paper)"
              stroke="var(--color-ink)"
              strokeWidth="1.25"
            />
            <text
              x={n.x + NODE_W / 2}
              y={n.y + NODE_H / 2 + 4}
              textAnchor="middle"
              className="fill-ink font-mono"
              fontSize="11"
              fontWeight="500"
            >
              {n.id}()
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-2 font-mono text-xs text-ink-soft">
        A real fragment of the graph CKG builds — from this project's own test fixtures.
      </figcaption>
    </figure>
  );
}
