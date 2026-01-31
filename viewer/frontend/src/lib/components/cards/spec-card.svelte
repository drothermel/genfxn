<script lang="ts">
  import type { Task } from "$lib/types";
  import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
  } from "$lib/components/ui/card";
  import { Badge } from "$lib/components/ui/badge";
  import PredicateView from "$lib/components/spec/predicate-view.svelte";
  import ExpressionView from "$lib/components/spec/expression-view.svelte";
  import TransformView from "$lib/components/spec/transform-view.svelte";
  import StringPredicateView from "$lib/components/spec/string-predicate-view.svelte";
  import StringTransformView from "$lib/components/spec/string-transform-view.svelte";

  interface Props {
    task: Task;
  }

  let { task }: Props = $props();

  const isPiecewise = $derived(task.family === "piecewise");
  const isStateful = $derived(task.family === "stateful");
  const isSimpleAlgorithms = $derived(task.family === "simple_algorithms");
  const isStringrules = $derived(task.family === "stringrules");
  const template = $derived(task.spec.template as string | undefined);
</script>

<Card>
  <CardHeader>
    <CardTitle>Specification</CardTitle>
  </CardHeader>
  <CardContent>
    {#if isPiecewise}
      <div class="space-y-4">
        <div>
          <h4 class="mb-2 text-sm font-medium text-muted-foreground">
            Branches
          </h4>
          {#if task.spec && Array.isArray(task.spec.branches)}
            <div class="space-y-2">
              {#each task.spec.branches as branch, i}
                <div
                  class="flex items-center gap-3 rounded-lg border bg-muted p-3"
                >
                  <span class="text-sm font-medium text-muted-foreground/70"
                    >if</span
                  >
                  {#if branch?.condition != null}
                    <PredicateView predicate={branch.condition} />
                  {:else}
                    <span class="text-sm text-muted-foreground italic">—</span>
                  {/if}
                  <span class="text-sm text-muted-foreground/70">then</span>
                  {#if branch?.expr != null}
                    <ExpressionView expression={branch.expr} />
                  {:else}
                    <span class="text-sm text-muted-foreground italic">—</span>
                  {/if}
                </div>
              {/each}
            </div>
          {:else}
            <p class="text-sm text-muted-foreground italic">
              No branches defined.
            </p>
          {/if}
        </div>
        <div>
          <h4 class="mb-2 text-sm font-medium text-muted-foreground">
            Default
          </h4>
          <div class="rounded-lg border bg-muted p-3">
            <span class="text-sm text-muted-foreground/70">else</span>
            {#if task.spec?.default_expr != null}
              <ExpressionView
                expression={task.spec.default_expr as Record<string, unknown>}
              />
            {:else}
              <span class="text-sm text-muted-foreground italic"
                >No default expression.</span
              >
            {/if}
          </div>
        </div>
      </div>
    {:else if isStateful && template === "conditional_linear_sum"}
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">conditional_linear_sum</Badge>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Predicate:</span>
            <PredicateView
              predicate={task.spec.predicate as Record<string, unknown>}
              variable="elem"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">If true:</span>
            <TransformView
              transform={task.spec.true_transform as Record<string, unknown>}
              variable="elem"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">If false:</span>
            <TransformView
              transform={task.spec.false_transform as Record<string, unknown>}
              variable="elem"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Init value:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.init_value}</code
            >
          </div>
        </div>
      </div>
    {:else if isStateful && template === "resetting_best_prefix_sum"}
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">resetting_best_prefix_sum</Badge>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Reset predicate:</span>
            <PredicateView
              predicate={task.spec.reset_predicate as Record<string, unknown>}
              variable="elem"
            />
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Init value:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.init_value}</code
            >
          </div>
        </div>
      </div>
    {:else if isStateful && template === "longest_run"}
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">longest_run</Badge>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Match predicate:</span>
            <PredicateView
              predicate={task.spec.match_predicate as Record<string, unknown>}
              variable="elem"
            />
          </div>
        </div>
      </div>
    {:else if isSimpleAlgorithms && template === "most_frequent"}
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">most_frequent</Badge>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Tie break:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.tie_break}</code
            >
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Empty default:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.empty_default}</code
            >
          </div>
        </div>
      </div>
    {:else if isSimpleAlgorithms && template === "count_pairs_sum"}
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">count_pairs_sum</Badge>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Target:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.target}</code
            >
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Counting mode:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.counting_mode}</code
            >
          </div>
        </div>
      </div>
    {:else if isSimpleAlgorithms && template === "max_window_sum"}
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">max_window_sum</Badge>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Window size (k):</span>
            <code class="rounded bg-muted px-1.5 py-0.5">{task.spec.k}</code>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-muted-foreground">Invalid k default:</span>
            <code class="rounded bg-muted px-1.5 py-0.5"
              >{task.spec.invalid_k_default}</code
            >
          </div>
        </div>
      </div>
    {:else if isStringrules}
      {@const rules = task.spec.rules as Array<{
        predicate: Record<string, unknown>;
        transform: Record<string, unknown>;
      }>}
      {@const defaultTransform = task.spec.default_transform as Record<
        string,
        unknown
      >}
      <div class="space-y-4">
        <div>
          <h4 class="mb-2 text-sm font-medium text-muted-foreground">Rules</h4>
          <div class="space-y-2">
            {#each rules as rule, i}
              <div
                class="flex items-center gap-3 rounded-lg border bg-muted p-3"
              >
                <span class="text-sm font-medium text-muted-foreground/70"
                  >{i === 0 ? "if" : "elif"}</span
                >
                <StringPredicateView predicate={rule.predicate} />
                <span class="text-sm text-muted-foreground/70">then</span>
                <StringTransformView transform={rule.transform} />
              </div>
            {/each}
          </div>
        </div>
        <div>
          <h4 class="mb-2 text-sm font-medium text-muted-foreground">
            Default
          </h4>
          <div class="flex items-center gap-3 rounded-lg border bg-muted p-3">
            <span class="text-sm text-muted-foreground/70">else</span>
            <StringTransformView transform={defaultTransform} />
          </div>
        </div>
      </div>
    {:else}
      <pre class="overflow-x-auto text-xs">{JSON.stringify(
          task.spec,
          null,
          2
        )}</pre>
    {/if}
  </CardContent>
</Card>
