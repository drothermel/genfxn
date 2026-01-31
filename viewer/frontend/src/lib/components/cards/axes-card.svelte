<script lang="ts">
  import type { Task } from "$lib/types";
  import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
  } from "$lib/components/ui/card";
  import { Badge } from "$lib/components/ui/badge";

  interface Props {
    task: Task;
  }

  let { task }: Props = $props();

  type TaskWithAxes = Task & { axes: Record<string, unknown> | null };
  const axes = $derived((task as TaskWithAxes).axes);
  const isPiecewise = $derived(task.family === "piecewise");
  const isStateful = $derived(task.family === "stateful");
  const isSimpleAlgorithms = $derived(task.family === "simple_algorithms");
  const isStringRules = $derived(task.family === "stringrules");

  function formatRange(range: unknown): string {
    if (range == null) {
      return "—";
    }
    if (Array.isArray(range) && range.length === 2) {
      return `[${range[0]}, ${range[1]}]`;
    }
    return String(range);
  }

  function formatAxisValue(value: unknown): string {
    if (Array.isArray(value)) {
      if (
        value.length === 2 &&
        typeof value[0] === "number" &&
        typeof value[1] === "number"
      ) {
        return formatRange(value);
      }
      return value.map(String).join(", ");
    }
    if (typeof value === "object" && value !== null) {
      return JSON.stringify(value);
    }
    return String(value);
  }
</script>

{#if axes}
  <Card>
    <CardHeader>
      <CardTitle>Sampling Axes</CardTitle>
    </CardHeader>
    <CardContent>
      <div class="grid gap-4 sm:grid-cols-2">
        {#if isPiecewise}
          <!-- Piecewise axes -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Type Constraints
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Branches:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{axes.n_branches}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Expression types:</span>
                <div class="flex flex-wrap gap-1">
                  {#each (axes.expr_types as string[]) ?? [] as exprType}
                    <Badge variant="secondary">{exprType}</Badge>
                  {/each}
                </div>
              </div>
            </div>
          </div>
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Numeric Ranges
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Value range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.value_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Threshold range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.threshold_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Coefficient range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.coeff_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Divisor range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.divisor_range)}</code
                >
              </div>
            </div>
          </div>
        {:else if isStateful}
          <!-- Stateful axes -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Type Constraints
            </h4>
            <div class="space-y-2 text-sm">
              <div>
                <span class="text-muted-foreground">Templates:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.templates as string[]) ?? [] as template}
                    <Badge variant="secondary">{template}</Badge>
                  {/each}
                </div>
              </div>
              <div>
                <span class="text-muted-foreground">Predicate types:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.predicate_types as string[]) ?? [] as predType}
                    <Badge variant="outline">{predType}</Badge>
                  {/each}
                </div>
              </div>
              <div>
                <span class="text-muted-foreground">Transform types:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.transform_types as string[]) ?? [] as transType}
                    <Badge variant="outline">{transType}</Badge>
                  {/each}
                </div>
              </div>
            </div>
          </div>
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Numeric Ranges
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Value range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.value_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">List length:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.list_length_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Threshold range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.threshold_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Divisor range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.divisor_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Shift range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.shift_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Scale range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.scale_range)}</code
                >
              </div>
            </div>
          </div>
        {:else if isSimpleAlgorithms}
          <!-- Simple algorithms axes -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Type Constraints
            </h4>
            <div class="space-y-2 text-sm">
              <div>
                <span class="text-muted-foreground">Templates:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.templates as string[]) ?? [] as t}
                    <Badge variant="secondary">{t}</Badge>
                  {/each}
                </div>
              </div>
              <div>
                <span class="text-muted-foreground">Tie-break modes:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.tie_break_modes as string[]) ?? [] as m}
                    <Badge variant="outline">{m}</Badge>
                  {/each}
                </div>
              </div>
              <div>
                <span class="text-muted-foreground">Counting modes:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.counting_modes as string[]) ?? [] as m}
                    <Badge variant="outline">{m}</Badge>
                  {/each}
                </div>
              </div>
            </div>
          </div>
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Numeric Ranges
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Value range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.value_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">List length:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.list_length_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Target range:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.target_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Window size:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.window_size_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Empty default:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.empty_default_range)}</code
                >
              </div>
            </div>
          </div>
        {:else if isStringRules}
          <!-- String rules axes -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              Type Constraints
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Number of rules:</span>
                <code class="rounded bg-muted px-2 py-0.5">{axes.n_rules}</code>
              </div>
              <div>
                <span class="text-muted-foreground">Predicate types:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.predicate_types as string[]) ?? [] as predType}
                    <Badge variant="outline">{predType}</Badge>
                  {/each}
                </div>
              </div>
              <div>
                <span class="text-muted-foreground">Transform types:</span>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each (axes.transform_types as string[]) ?? [] as transType}
                    <Badge variant="outline">{transType}</Badge>
                  {/each}
                </div>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Overlap level:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{axes.overlap_level}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Charset:</span>
                <code class="rounded bg-muted px-2 py-0.5">{axes.charset}</code>
              </div>
            </div>
          </div>
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-muted-foreground">
              String & Length Ranges
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">String length:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.string_length_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Prefix/suffix length:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.prefix_suffix_length_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Substring length:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.substring_length_range)}</code
                >
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">Length threshold:</span>
                <code class="rounded bg-muted px-2 py-0.5"
                  >{formatRange(axes.length_threshold_range)}</code
                >
              </div>
            </div>
          </div>
        {:else}
          <!-- Generic fallback for unknown families -->
          <div class="col-span-full space-y-2 text-sm">
            <h4 class="text-sm font-medium text-muted-foreground">
              Axes (family: {task.family})
            </h4>
            <div class="flex flex-wrap gap-2">
              {#each Object.entries(axes) as [key, value]}
                <div
                  class="flex items-center gap-1.5 rounded border bg-muted/50 px-2 py-1"
                >
                  <span class="text-muted-foreground">{key}:</span>
                  <code class="rounded bg-muted px-1.5 py-0.5 text-xs"
                    >{formatAxisValue(value)}</code
                  >
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </CardContent>
  </Card>
{/if}
