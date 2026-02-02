<script lang="ts" module>
	import type { Snapshot } from './$types';

	interface PageState {
		enabledFamilies: Record<string, boolean>;
		enabledDifficulties: Record<number, boolean>;
		enabledPrompts: Record<string, boolean>;
		enabledBudgets: Record<string, boolean>;
		enabledModels: Record<string, boolean>;
		allKnownModels: string[];
		availableModels: string[];
		runs: import('$lib/types').RunSummary[];
		hasLoaded: boolean;
		expandedGroups: string[];
	}

	let savedState: PageState | null = null;

	export const snapshot: Snapshot<PageState> = {
		capture: () => savedState!,
		restore: (state) => {
			savedState = state;
		}
	};
</script>

<script lang="ts">
	import { fetchRunTags, fetchRunModels, fetchRuns } from '$lib/api';
	import type { RunSummary } from '$lib/types';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { ArrowLeft, CheckCircle, XCircle, Circle } from 'lucide-svelte';
	import { onMount } from 'svelte';

	let allTags: string[] = $state([]);
	let runs: RunSummary[] = $state([]);

	let loadingTags = $state(true);
	let loadingRuns = $state(false);
	let loadingModels = $state(false);
	let error: string | null = $state(null);
	let hasLoaded = $state(false);

	// Family filtering
	let enabledFamilies: Record<string, boolean> = $state({});
	// Difficulty filtering
	let enabledDifficulties: Record<number, boolean> = $state({});
	// Prompt name filtering
	let enabledPrompts: Record<string, boolean> = $state({});
	// Budget filtering
	let enabledBudgets: Record<string, boolean> = $state({});
	// Model filtering
	let allKnownModels: string[] = $state([]);
	let availableModels: Set<string> = $state(new Set());
	let enabledModels: Record<string, boolean> = $state({});

	// Expanded groups for stacked runs
	let expandedGroups: Set<string> = $state(new Set());

	// Restore state from snapshot if available
	onMount(() => {
		if (savedState) {
			enabledFamilies = savedState.enabledFamilies;
			enabledDifficulties = savedState.enabledDifficulties;
			enabledPrompts = savedState.enabledPrompts;
			enabledBudgets = savedState.enabledBudgets;
			enabledModels = savedState.enabledModels;
			allKnownModels = savedState.allKnownModels;
			availableModels = new Set(savedState.availableModels);
			runs = savedState.runs;
			hasLoaded = savedState.hasLoaded;
			expandedGroups = new Set(savedState.expandedGroups);
		}
	});

	// Save state for snapshot
	$effect(() => {
		savedState = {
			enabledFamilies,
			enabledDifficulties,
			enabledPrompts,
			enabledBudgets,
			enabledModels,
			allKnownModels,
			availableModels: [...availableModels],
			runs,
			hasLoaded,
			expandedGroups: [...expandedGroups]
		};
	});

	function extractFamily(tag: string): string {
		// Extract family from tag like "fizzbuzz1_enc-..." -> "fizzbuzz"
		const match = tag.match(/^([a-z_]+)/i);
		return match ? match[1].replace(/\d+$/, '') : 'unknown';
	}

	function extractDifficulty(tag: string): number | null {
		// Extract difficulty from tag like "piecewise3_enc-..." -> 3
		const match = tag.match(/^[a-z_]+(\d+)/i);
		return match ? parseInt(match[1], 10) : null;
	}

	function extractPromptName(tag: string): string | null {
		// Extract prompt name from tag like "fizzbuzz1_enc-basic_b05_v1" -> "enc-basic"
		const match = tag.match(/^[a-z_]+\d+_([^_]+(?:-[^_]+)*)_b\d+/i);
		return match ? match[1] : null;
	}

	function extractBudget(tag: string): string | null {
		// Extract budget from tag like "fizzbuzz1_enc-basic_b05_v1" -> "b05"
		const match = tag.match(/_(b\d+)_v\d+$/i);
		return match ? match[1] : null;
	}

	function formatBudget(budget: string): string {
		// Format budget for display: b05 -> 50%, b075 -> 75%, b10 -> 100%
		const num = budget.replace('b', '');
		if (num === '10') return '100%';
		if (num === '05') return '50%';
		if (num === '075') return '75%';
		// Fallback: treat as multiplier (e.g., b05 = 0.5 = 50%)
		const val = parseFloat(num.length === 2 ? `0.${num}` : `0.${num}`);
		return `${Math.round(val * 100)}%`;
	}

	function formatModelName(model: string): string {
		// Shorten model name: "pydantic-ai_google-gla:gemini-2.5-flash" -> "gemini-2.5-flash"
		const parts = model.split(':');
		return parts.length > 1 ? parts[parts.length - 1] : model;
	}

	// Filter out test tags first, then extract families
	const nonTestTags = $derived(allTags.filter((tag) => !tag.toLowerCase().includes('test')));

	const allFamilies = $derived(() => {
		const families = new Set<string>();
		for (const tag of nonTestTags) {
			families.add(extractFamily(tag));
		}
		return [...families].sort();
	});

	const allDifficulties = $derived(() => {
		const difficulties = new Set<number>();
		for (const tag of nonTestTags) {
			const d = extractDifficulty(tag);
			if (d !== null) difficulties.add(d);
		}
		return [...difficulties].sort((a, b) => a - b);
	});

	const allPrompts = $derived(() => {
		const prompts = new Set<string>();
		for (const tag of nonTestTags) {
			const p = extractPromptName(tag);
			if (p !== null) prompts.add(p);
		}
		return [...prompts].sort();
	});

	const allBudgets = $derived(() => {
		const budgets = new Set<string>();
		for (const tag of nonTestTags) {
			const b = extractBudget(tag);
			if (b !== null) budgets.add(b);
		}
		// Sort numerically by the number in the budget string
		return [...budgets].sort((a, b) => {
			const numA = parseFloat(a.replace('b', '').replace('0', '0.'));
			const numB = parseFloat(b.replace('b', '').replace('0', '0.'));
			return numA - numB;
		});
	});

	// Initialize family toggles when tags load (piecewise off by default)
	$effect(() => {
		const families = allFamilies();
		if (families.length > 0 && Object.keys(enabledFamilies).length === 0) {
			const initial: Record<string, boolean> = {};
			for (const f of families) {
				initial[f] = f !== 'piecewise';
			}
			enabledFamilies = initial;
		}
	});

	// Initialize difficulty toggles (only 3 on by default)
	$effect(() => {
		const difficulties = allDifficulties();
		if (difficulties.length > 0 && Object.keys(enabledDifficulties).length === 0) {
			const initial: Record<number, boolean> = {};
			for (const d of difficulties) {
				initial[d] = d === 3;
			}
			enabledDifficulties = initial;
		}
	});

	// Initialize prompt toggles (only enc-basic on by default)
	$effect(() => {
		const prompts = allPrompts();
		if (prompts.length > 0 && Object.keys(enabledPrompts).length === 0) {
			const initial: Record<string, boolean> = {};
			for (const p of prompts) {
				initial[p] = p === 'enc-basic';
			}
			enabledPrompts = initial;
		}
	});

	// Initialize budget toggles (only 100% / b10 on by default)
	$effect(() => {
		const budgets = allBudgets();
		if (budgets.length > 0 && Object.keys(enabledBudgets).length === 0) {
			const initial: Record<string, boolean> = {};
			for (const b of budgets) {
				initial[b] = b === 'b10';
			}
			enabledBudgets = initial;
		}
	});

	// Filter tags: exclude "test", filter by enabled families, difficulty, prompt, and budget
	const tags = $derived(
		nonTestTags.filter((tag) => {
			const family = extractFamily(tag);
			if (enabledFamilies[family] === false) return false;

			// Fizzbuzz is exempt from difficulty filtering
			if (family !== 'fizzbuzz') {
				const difficulty = extractDifficulty(tag);
				if (difficulty !== null && enabledDifficulties[difficulty] === false) return false;
			}

			const prompt = extractPromptName(tag);
			if (prompt !== null && enabledPrompts[prompt] === false) return false;

			const budget = extractBudget(tag);
			if (budget !== null && enabledBudgets[budget] === false) return false;

			return true;
		})
	);

	async function loadTags() {
		loadingTags = true;
		error = null;
		try {
			allTags = await fetchRunTags();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loadingTags = false;
		}
	}

	async function refreshAvailableModels() {
		const filteredTags = tags;
		if (filteredTags.length === 0) {
			availableModels = new Set();
			return;
		}

		loadingModels = true;
		error = null;

		try {
			const models = new Set<string>();

			// Fetch models for each filtered tag
			for (const tag of filteredTags) {
				const tagModels = await fetchRunModels(tag);
				for (const m of tagModels) {
					models.add(m);
				}
			}

			availableModels = models;

			// Add any new models to allKnownModels
			const known = new Set(allKnownModels);
			for (const m of models) {
				known.add(m);
			}
			allKnownModels = [...known].sort();

			// Initialize enabledModels for new models (only select specific models by default)
			const updated = { ...enabledModels };
			for (const m of models) {
				if (!(m in updated)) {
					// Default select only specific models
					const lower = m.toLowerCase();
					const isDefault =
						lower.includes('gemini-2.5-flash') ||
						lower.includes('haiku') ||
						lower.includes('codex-mini') ||
						lower.includes('nano');
					updated[m] = isDefault;
				}
			}
			enabledModels = updated;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loadingModels = false;
		}
	}

	async function loadAllRuns() {
		const filteredTags = tags;
		if (filteredTags.length === 0) {
			runs = [];
			return;
		}

		loadingRuns = true;
		error = null;
		hasLoaded = true;

		try {
			const allRuns: RunSummary[] = [];
			const models = new Set<string>();

			// For each filtered tag, get models then runs
			for (const tag of filteredTags) {
				const tagModels = await fetchRunModels(tag);
				for (const model of tagModels) {
					models.add(model);
					// Skip if model is disabled
					if (enabledModels[model] === false) continue;
					const tagRuns = await fetchRuns(tag, model);
					allRuns.push(...tagRuns);
				}
			}

			// Update available models
			availableModels = models;
			const known = new Set(allKnownModels);
			for (const m of models) {
				known.add(m);
			}
			allKnownModels = [...known].sort();

			runs = allRuns;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loadingRuns = false;
		}
	}

	$effect(() => {
		loadTags();
	});

	function getPassRateColor(rate: number | null): string {
		if (rate === null) return 'text-muted-foreground';
		if (rate >= 1.0) return 'text-green-600';
		if (rate >= 0.5) return 'text-yellow-600';
		return 'text-red-600';
	}

	function formatPassRate(rate: number | null): string {
		if (rate === null) return '-';
		return `${(rate * 100).toFixed(0)}%`;
	}

	// Group runs by task_id + tag (same task config, different models)
	interface RunGroup {
		key: string;
		primary: RunSummary;
		others: RunSummary[];
		sampleLabel: string;
	}

	const groupedRuns = $derived(() => {
		const groups = new Map<string, RunSummary[]>();
		for (const run of runs) {
			const key = `${run.tag}_${run.task_id ?? run.run_id}`;
			if (!groups.has(key)) {
				groups.set(key, []);
			}
			groups.get(key)!.push(run);
		}

		// Convert to array and sort by family + task_id for stable ordering
		const groupArray = [...groups.entries()].sort((a, b) => {
			const aRun = a[1][0];
			const bRun = b[1][0];
			const familyCompare = (aRun.task_family ?? '').localeCompare(bRun.task_family ?? '');
			if (familyCompare !== 0) return familyCompare;
			return (aRun.task_id ?? '').localeCompare(bRun.task_id ?? '');
		});

		// Assign sample numbers per family
		const familyCounts = new Map<string, number>();
		const result: RunGroup[] = [];

		for (const [key, groupRuns] of groupArray) {
			const family = groupRuns[0].task_family ?? 'unknown';
			const count = (familyCounts.get(family) ?? 0) + 1;
			familyCounts.set(family, count);

			result.push({
				key,
				primary: groupRuns[0],
				others: groupRuns.slice(1),
				sampleLabel: `${family} #${count}`
			});
		}
		return result;
	});
</script>

<div class="container mx-auto max-w-5xl px-4 py-8">
	<div class="mb-6">
		<a href="/" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
			<ArrowLeft class="h-4 w-4" />
			Back to tasks
		</a>
	</div>

	<header class="mb-8">
		<h1 class="text-3xl font-bold">nl_latents Runs</h1>
		<p class="mt-2 text-muted-foreground">Browse generation runs by tag and model</p>
	</header>

	{#if allFamilies().length > 0}
		<div class="mb-3 flex flex-wrap items-center gap-3">
			<span class="text-sm font-medium text-muted-foreground">Families:</span>
			{#each allFamilies() as family}
				{@const isEnabled = enabledFamilies[family] !== false}
				<label class="flex cursor-pointer items-center gap-1.5 text-sm {isEnabled ? '' : 'text-red-400'}">
					<input
						type="checkbox"
						checked={isEnabled}
						onchange={(e) => {
							enabledFamilies = { ...enabledFamilies, [family]: e.currentTarget.checked };
						}}
						class="h-4 w-4 rounded {isEnabled ? 'border-gray-300' : 'border-red-300 accent-red-400'}"
					/>
					{family}
				</label>
			{/each}
		</div>
	{/if}

	{#if allDifficulties().length > 0}
		<div class="mb-3 flex flex-wrap items-center gap-3">
			<span class="text-sm font-medium text-muted-foreground">Difficulty:</span>
			{#each allDifficulties() as difficulty}
				{@const isEnabled = enabledDifficulties[difficulty] !== false}
				<label class="flex cursor-pointer items-center gap-1.5 text-sm {isEnabled ? '' : 'text-red-400'}">
					<input
						type="checkbox"
						checked={isEnabled}
						onchange={(e) => {
							enabledDifficulties = { ...enabledDifficulties, [difficulty]: e.currentTarget.checked };
						}}
						class="h-4 w-4 rounded {isEnabled ? 'border-gray-300' : 'border-red-300 accent-red-400'}"
					/>
					{difficulty}
				</label>
			{/each}
			<span class="text-xs text-muted-foreground">(fizzbuzz always shown)</span>
		</div>
	{/if}

	{#if allPrompts().length > 0}
		<div class="mb-3 flex flex-wrap items-center gap-3">
			<span class="text-sm font-medium text-muted-foreground">Encoder Prompt:</span>
			{#each allPrompts() as prompt}
				<label class="flex cursor-pointer items-center gap-1.5 text-sm">
					<input
						type="checkbox"
						checked={enabledPrompts[prompt] !== false}
						onchange={(e) => {
							enabledPrompts = { ...enabledPrompts, [prompt]: e.currentTarget.checked };
						}}
						class="h-4 w-4 rounded border-gray-300"
					/>
					{prompt}
				</label>
			{/each}
		</div>
	{/if}

	{#if allBudgets().length > 0}
		<div class="mb-3 flex flex-wrap items-center gap-3">
			<span class="text-sm font-medium text-muted-foreground">Budget:</span>
			{#each allBudgets() as budget}
				<label class="flex cursor-pointer items-center gap-1.5 text-sm">
					<input
						type="checkbox"
						checked={enabledBudgets[budget] !== false}
						onchange={(e) => {
							enabledBudgets = { ...enabledBudgets, [budget]: e.currentTarget.checked };
						}}
						class="h-4 w-4 rounded border-gray-300"
					/>
					{formatBudget(budget)}
				</label>
			{/each}
		</div>
	{/if}

	<div class="mb-4 flex flex-wrap items-center gap-3">
		<span class="text-sm font-medium text-muted-foreground">Models:</span>
		{#if allKnownModels.length === 0}
			<button
				onclick={refreshAvailableModels}
				disabled={loadingModels || loadingTags || tags.length === 0}
				class="rounded border border-input bg-background px-2 py-1 text-xs transition-colors hover:bg-muted disabled:opacity-50"
			>
				{loadingModels ? 'Loading...' : 'Load Models'}
			</button>
		{:else}
			{#each allKnownModels as model}
				{@const isAvailable = availableModels.has(model)}
				{@const isEnabled = enabledModels[model] !== false}
				<label class="flex items-center gap-1.5 text-sm {isAvailable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'} {isAvailable && !isEnabled ? 'text-red-400' : ''}">
					<input
						type="checkbox"
						checked={isEnabled}
						disabled={!isAvailable}
						onchange={(e) => {
							enabledModels = { ...enabledModels, [model]: e.currentTarget.checked };
						}}
						class="h-4 w-4 rounded {isAvailable && !isEnabled ? 'border-red-300 accent-red-400' : 'border-gray-300'}"
					/>
					<span title={model}>{formatModelName(model)}</span>
				</label>
			{/each}
			<button
				onclick={refreshAvailableModels}
				disabled={loadingModels || tags.length === 0}
				class="rounded border border-input bg-background px-2 py-1 text-xs transition-colors hover:bg-muted disabled:opacity-50"
				title="Refresh available models for current filters"
			>
				{loadingModels ? '...' : '↻'}
			</button>
		{/if}
	</div>

	<div class="mb-6 flex flex-wrap items-center gap-4">
		<button
			onclick={loadAllRuns}
			disabled={loadingRuns || loadingTags || tags.length === 0}
			class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
		>
			{loadingRuns ? 'Loading...' : `Load Runs (${tags.length} tags)`}
		</button>

		{#if runs.length > 0}
			<span class="text-sm text-muted-foreground">
				{runs.length} run{runs.length !== 1 ? 's' : ''}
			</span>
		{/if}
	</div>

	{#if loadingTags || loadingRuns}
		<div class="flex items-center justify-center py-12">
			<div class="text-muted-foreground">Loading...</div>
		</div>
	{:else if error}
		<Card>
			<CardContent class="py-8 text-center">
				<p class="text-red-500">{error}</p>
				<p class="mt-2 text-sm text-muted-foreground">
					Make sure the backend is running with --runs-dir
				</p>
			</CardContent>
		</Card>
	{:else if !hasLoaded}
		<Card>
			<CardContent class="py-8 text-center">
				<p class="text-muted-foreground">Set filters above and click "Load Runs" to browse</p>
			</CardContent>
		</Card>
	{:else if runs.length === 0}
		<Card>
			<CardContent class="py-8 text-center">
				<p class="text-muted-foreground">No runs found matching filters</p>
			</CardContent>
		</Card>
	{:else}
		<div class="mb-2 text-sm text-muted-foreground">
			{groupedRuns().length} task{groupedRuns().length !== 1 ? 's' : ''} ({runs.length} total runs)
		</div>
		<div class="space-y-2">
			{#each groupedRuns() as group}
				{@const isExpanded = expandedGroups.has(group.key)}
				<div class="relative">
					<!-- Stacked cards indicator -->
					{#if group.others.length > 0 && !isExpanded}
						<div class="absolute -bottom-0.5 left-1 right-1 h-1 rounded-b border border-t-0 bg-muted/50"></div>
						<div class="absolute -bottom-1 left-2 right-2 h-1 rounded-b border border-t-0 bg-muted/30"></div>
					{/if}

					<!-- Primary card -->
					<a href="/runs/{encodeURIComponent(group.primary.tag)}/{encodeURIComponent(group.primary.model)}/{group.primary.run_id}" class="relative block">
						<Card class="transition-shadow hover:shadow-md">
							<div class="flex items-center justify-between px-4 py-2">
								<div class="flex items-center gap-2">
									<span class="text-sm font-medium">{group.sampleLabel}</span>
									<Badge variant="outline" class="text-xs">{formatModelName(group.primary.model)}</Badge>
									{#if extractBudget(group.primary.tag)}
										<Badge variant="secondary" class="text-xs">{formatBudget(extractBudget(group.primary.tag)!)}</Badge>
									{/if}
								</div>
								<div class="flex items-center gap-2 text-sm">
									{#if group.primary.has_validation}
										<span class="flex items-center gap-1 {getPassRateColor(group.primary.best_pass_rate)}">
											{#if group.primary.best_pass_rate === 1.0}
												<CheckCircle class="h-3 w-3" />
											{:else if group.primary.best_pass_rate !== null && group.primary.best_pass_rate > 0}
												<Circle class="h-3 w-3" />
											{:else}
												<XCircle class="h-3 w-3" />
											{/if}
											{formatPassRate(group.primary.best_pass_rate)}
										</span>
									{/if}
									{#if group.others.length > 0}
										<button
											onclick={(e) => {
												e.preventDefault();
												if (isExpanded) {
													expandedGroups.delete(group.key);
												} else {
													expandedGroups.add(group.key);
												}
												expandedGroups = new Set(expandedGroups);
											}}
											class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted/80"
										>
											+{group.others.length}
										</button>
									{/if}
								</div>
							</div>
						</Card>
					</a>

					<!-- Expanded other runs -->
					{#if isExpanded && group.others.length > 0}
						<div class="mt-1 ml-4 space-y-1 border-l-2 border-muted pl-2">
							{#each group.others as run}
								<a href="/runs/{encodeURIComponent(run.tag)}/{encodeURIComponent(run.model)}/{run.run_id}" class="block">
									<Card class="transition-shadow hover:shadow-md">
										<div class="flex items-center justify-between px-3 py-1.5">
											<div class="flex items-center gap-1.5">
												<Badge variant="outline" class="text-xs">{formatModelName(run.model)}</Badge>
												{#if extractBudget(run.tag)}
													<Badge variant="secondary" class="text-xs">{formatBudget(extractBudget(run.tag)!)}</Badge>
												{/if}
											</div>
											<div class="flex items-center gap-2 text-sm">
												{#if run.has_validation}
													<span class="flex items-center gap-1 {getPassRateColor(run.best_pass_rate)}">
														{#if run.best_pass_rate === 1.0}
															<CheckCircle class="h-3 w-3" />
														{:else if run.best_pass_rate !== null && run.best_pass_rate > 0}
															<Circle class="h-3 w-3" />
														{:else}
															<XCircle class="h-3 w-3" />
														{/if}
														{formatPassRate(run.best_pass_rate)}
													</span>
												{/if}
											</div>
										</div>
									</Card>
								</a>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
