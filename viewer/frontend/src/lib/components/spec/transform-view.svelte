<script lang="ts">
	interface Props {
		transform: Record<string, unknown>;
		variable?: string;
	}

	let { transform, variable = 'x' }: Props = $props();

	function renderTransform(t: Record<string, unknown>, v: string): string {
		const kind = t.kind as string;
		switch (kind) {
			case 'identity':
				return v;
			case 'abs':
				return `abs(${v})`;
			case 'shift': {
				const offset = t.offset as number;
				if (offset >= 0) return `${v} + ${offset}`;
				return `${v} - ${-offset}`;
			}
			case 'negate':
				return `-${v}`;
			case 'scale': {
				const factor = t.factor as number;
				return `${v} * ${factor}`;
			}
			case 'clip': {
				const low = t.low as number;
				const high = t.high as number;
				return `clip(${v}, ${low}, ${high})`;
			}
			default:
				return JSON.stringify(t);
		}
	}

	const rendered = $derived(renderTransform(transform, variable));
</script>

<code class="rounded bg-purple-50 px-1.5 py-0.5 text-purple-700">{rendered}</code>
