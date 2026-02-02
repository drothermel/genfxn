<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>genfxn Viewer</title>
</svelte:head>

<div class="min-h-screen bg-muted/40 font-sans antialiased">
	<nav class="border-b bg-background">
		<div class="container mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
			<a href="/" class="font-semibold">genfxn</a>
			<div class="flex gap-4 text-sm">
				<a href="/" class="text-muted-foreground transition-colors hover:text-foreground">Tasks</a>
				<a href="/runs" class="text-muted-foreground transition-colors hover:text-foreground">Runs</a>
			</div>
		</div>
	</nav>
	{@render children()}
</div>
