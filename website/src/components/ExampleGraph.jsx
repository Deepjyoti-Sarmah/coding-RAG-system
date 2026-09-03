import { EXAMPLE_GRAPH } from "../data/content";

const W = 110;
const H = 34;

function center(n) {
  return { x: n.x + W / 2, y: n.y + H / 2 };
}

export default function ExampleGraph() {
  const { nodes, edges } = EXAMPLE_GRAPH;
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

  return (
    <div className="flex min-h-[220px] w-full items-center justify-center rounded-sm border border-white/10 bg-panel p-6">
      <svg viewBox="0 0 350 150" className="w-full max-w-[320px]" role="img" aria-label="Symbol graph: login calls createAuth, run calls login">
        <defs>
          <marker id="arrow-dark" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 Z" fill="#8f8fff" />
          </marker>
        </defs>

        {edges.map((e) => {
          const from = byId[e.from];
          const to = byId[e.to];
          const a = center(from);
          const b = center(to);
          let d;
          if (Math.abs(a.y - b.y) < 4) {
            d = `M ${from.x + W} ${a.y} L ${to.x - 10} ${a.y}`;
          } else {
            const sx = from.x + W / 2;
            const sy = a.y < b.y ? from.y + H : from.y;
            const ex = to.x + W / 2;
            const ey = a.y < b.y ? to.y : to.y + H;
            const my = (sy + ey) / 2;
            d = `M ${sx} ${sy} C ${sx} ${my}, ${ex} ${my}, ${ex} ${ey}`;
          }
          return (
            <path key={`${e.from}-${e.to}`} d={d} fill="none" stroke="#8f8fff" strokeWidth="1.5" markerEnd="url(#arrow-dark)" />
          );
        })}

        {nodes.map((n) => (
          <g key={n.id}>
            <rect x={n.x} y={n.y} width={W} height={H} rx="3" fill="#131316" stroke="#3a3a55" strokeWidth="1.25" />
            <text x={n.x + W / 2} y={n.y + H / 2 + 4} textAnchor="middle" fontSize="11" fontWeight="500" fill="#e8e8f5" fontFamily="var(--font-mono)">
              {n.id}()
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
