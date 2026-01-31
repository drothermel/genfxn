import type { Task } from './types';

const API_BASE = 'http://127.0.0.1:8000/api';

export async function fetchTasks(family?: string): Promise<Task[]> {
	const url = family ? `${API_BASE}/tasks?family=${family}` : `${API_BASE}/tasks`;
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`Failed to fetch tasks: ${response.statusText}`);
	}
	return response.json();
}

export async function fetchTask(taskId: string): Promise<Task> {
	const response = await fetch(`${API_BASE}/tasks/${taskId}`);
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
