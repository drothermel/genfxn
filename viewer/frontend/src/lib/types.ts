export interface TraceStep {
	step: string;
	choice: string;
	value: unknown;
}

export interface GenerationTrace {
	family: string;
	steps: TraceStep[];
}

export type QueryTag = 'typical' | 'boundary' | 'coverage' | 'adversarial';

export interface Query {
	input: unknown;
	output: unknown;
	tag: QueryTag;
}

export interface Task {
	task_id: string;
	family: string;
	spec: Record<string, unknown>;
	code: string;
	queries: Query[];
	trace: GenerationTrace | null;
	axes: Record<string, unknown> | null;
	difficulty: number | null;
	description: string | null;
}
