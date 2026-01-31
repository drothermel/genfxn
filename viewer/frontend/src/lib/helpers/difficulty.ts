/**
 * Returns Tailwind class string for difficulty badge styling (1–5).
 */
export function getDifficultyColor(difficulty: number): string {
	const colors: Record<number, string> = {
		1: 'bg-green-100 text-green-800 border-green-200',
		2: 'bg-lime-100 text-lime-800 border-lime-200',
		3: 'bg-yellow-100 text-yellow-800 border-yellow-200',
		4: 'bg-orange-100 text-orange-800 border-orange-200',
		5: 'bg-red-100 text-red-800 border-red-200'
	};
	return colors[difficulty] || 'bg-gray-100 text-gray-800 border-gray-200';
}
