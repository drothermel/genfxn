<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>genfxn Trace Viewer</title>
</svelte:head>

<div class="min-h-screen bg-muted/40 font-sans antialiased">
	{@render children()}
</div>
