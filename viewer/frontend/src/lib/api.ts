import type { Task } from './types';

/** API base URL. Set VITE_API_BASE in .env or deployment config; falls back to /api for same-origin. */
const API_BASE =
	(typeof import.meta.env.VITE_API_BASE === 'string' && import.meta.env.VITE_API_BASE) || '/api';

export async function fetchTasks(family?: string): Promise<Task[]> {
	const url = family ? `${API_BASE}/tasks?family=${encodeURIComponent(family)}` : `${API_BASE}/tasks`;
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`Failed to fetch tasks: ${response.statusText}`);
	}
	return response.json();
}

export async function fetchTask(taskId: string): Promise<Task> {
	const response = await fetch(`${API_BASE}/tasks/${encodeURIComponent(taskId)}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch task: ${response.statusText}`);
	}
	return response.json();
}

export async function fetchFamilies(): Promise<string[]> {
	const response = await fetch(`${API_BASE}/families`);
	if (!response.ok) {
		throw new Error(`Failed to fetch families: ${response.statusText}`);
	}
	return response.json();
}
