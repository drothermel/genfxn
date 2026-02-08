<script lang="ts">
  import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
  } from "$lib/components/ui/card";
  import { sanitizeHighlightedHtml } from "$lib/helpers/sanitize";
  import { codeToHtml } from "shiki";

  interface Props {
    code: string;
  }

  let { code }: Props = $props();
  let highlightedHtml: string = $state("");

  $effect(() => {
    const c = code;
    let cancelled = false;
    codeToHtml(c, { lang: "python", theme: "github-light" })
      .then((html) => {
        if (!cancelled) highlightedHtml = sanitizeHighlightedHtml(html);
      })
      .catch((err) => {
        if (!cancelled) {
          highlightedHtml = "";
          console.error("Code highlight failed:", err);
        }
      });
    return () => {
      cancelled = true;
    };
  });
</script>

<Card>
  <CardHeader>
    <CardTitle>Generated Code</CardTitle>
  </CardHeader>
  <CardContent>
    {#if highlightedHtml}
      <div class="overflow-x-auto rounded-lg border bg-gray-50 p-4 text-sm">
        {@html highlightedHtml}
      </div>
    {:else}
      <pre
        class="overflow-x-auto rounded-lg border bg-gray-50 p-4 text-sm">{code}</pre>
    {/if}
  </CardContent>
</Card>
