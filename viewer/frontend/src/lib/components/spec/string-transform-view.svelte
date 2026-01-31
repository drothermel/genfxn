<script lang="ts">
	interface Props {
		transform: Record<string, unknown>;
		variable?: string;
	}

	let { transform, variable = 's' }: Props = $props();

	function renderTransform(t: Record<string, unknown>, v: string): string {
		const kind = t.kind as string;
		switch (kind) {
			case 'identity':
				return v;
			case 'lowercase':
				return `${v}.lower()`;
			case 'uppercase':
				return `${v}.upper()`;
			case 'capitalize':
				return `${v}.capitalize()`;
			case 'swapcase':
				return `${v}.swapcase()`;
			case 'reverse':
				return `${v}[::-1]`;
			case 'replace':
				return `${v}.replace("${t.old}", "${t.new}")`;
			case 'strip': {
				const chars = t.chars as string | null;
				if (chars) {
					return `${v}.strip("${chars}")`;
				}
				return `${v}.strip()`;
			}
			case 'prepend':
				return `"${t.prefix}" + ${v}`;
			case 'append':
				return `${v} + "${t.suffix}"`;
			default:
				return JSON.stringify(t);
		}
	}

	const rendered = $derived(renderTransform(transform, variable));
</script>

<code class="rounded bg-teal-50 px-1.5 py-0.5 text-teal-700">{rendered}</code>
