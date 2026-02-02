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

// nl_latents Run types

export interface RunMeta {
	run_id: string;
	engine: string | null;
	model: string;
	provider: string | null;
	tag: string;
	timestamp_utc: string | null;
	prompt_name: string | null;
	prompt_version: number | null;
	sampling: Record<string, unknown> | null;
	budgets: Record<string, unknown> | null;
	git: Record<string, unknown> | null;
	task: { task_id?: string; family?: string } | null;
}

export interface TestCaseResult {
	input_value: unknown;
	expected_output: unknown;
	actual_output: unknown;
	passed: boolean;
	error: string | null;
}

export interface ValidationResult {
	decoder_name: string;
	raw_output: string | null;
	extracted_code: string | null;
	has_code_fences: boolean | null;
	is_valid_python: boolean | null;
	python_error: string | null;
	expected_function_name: string | null;
	has_expected_function: boolean | null;
	test_pass_rate: number | null;
	test_case_results: TestCaseResult[] | null;
}

export interface RunData {
	meta: RunMeta;
	task_prompt: string | null;
	system_prompt: string | null;
	output: string | null;
	eval: Record<string, unknown> | null;
	validations: ValidationResult[];
	decoder_outputs: Record<string, string>;
}

export interface RunSummary {
	run_id: string;
	tag: string;
	model: string;
	task_id: string | null;
	task_family: string | null;
	has_eval: boolean;
	has_validation: boolean;
	validation_count: number;
	best_pass_rate: number | null;
}
