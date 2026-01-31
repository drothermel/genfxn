<script lang="ts">
	interface Props {
		expression: Record<string, unknown>;
		variable?: string;
	}

	let { expression, variable = 'x' }: Props = $props();

	function renderExpression(expr: Record<string, unknown>, v: string): string {
		const kind = expr.kind as string;
		switch (kind) {
			case 'affine': {
				const a = Number(expr.a ?? 0);
				const b = Number(expr.b ?? 0);
				const parts: string[] = [];
				if (a !== 0) parts.push(a === 1 ? v : a === -1 ? `-${v}` : `${a}${v}`);
				if (b !== 0 || parts.length === 0)
					parts.push(b >= 0 && parts.length > 0 ? `+ ${b}` : String(b));
				return parts.join(' ');
			}
			case 'quadratic': {
				const a = Number(expr.a ?? 0);
				const b = Number(expr.b ?? 0);
				const c = Number(expr.c ?? 0);
				const parts: string[] = [];
				if (a !== 0) parts.push(`${a}${v}²`);
				if (b !== 0) parts.push(b > 0 && parts.length > 0 ? `+ ${b}${v}` : `${b}${v}`);
				if (c !== 0 || parts.length === 0)
					parts.push(c >= 0 && parts.length > 0 ? `+ ${c}` : String(c));
				return parts.join(' ');
			}
			case 'abs': {
				const a = Number(expr.a ?? 0);
				const b = Number(expr.b ?? 0);
				const abs = a === 1 ? `|${v}|` : a === -1 ? `-|${v}|` : `${a}|${v}|`;
				if (b === 0) return abs;
				return b > 0 ? `${abs} + ${b}` : `${abs} - ${-b}`;
			}
			case 'mod': {
				const divisor = Number(expr.divisor ?? 1);
				const a = Number(expr.a ?? 0);
				const b = Number(expr.b ?? 0);
				const mod = a === 1 ? `(${v} % ${divisor})` : `${a}(${v} % ${divisor})`;
				if (b === 0) return mod;
				return b > 0 ? `${mod} + ${b}` : `${mod} - ${-b}`;
			}
			default:
				return JSON.stringify(expr);
		}
	}

	const rendered = $derived(renderExpression(expression, variable));
</script>

<code class="rounded bg-green-50 px-1.5 py-0.5 text-green-700">{rendered}</code>
