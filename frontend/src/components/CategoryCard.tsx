import type { StarterQuestion } from "../data/starterQuestions";

interface CategoryCardProps {
  category: StarterQuestion;
  onSelect: (question: string) => void;
}

export function CategoryCard({ category, onSelect }: CategoryCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(category.question)}
      className="flex flex-col items-start gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 text-left transition hover:border-[var(--brand-green)] hover:bg-[var(--brand-green-light)]"
    >
      <span className="text-xl">{category.icon}</span>
      <span className="text-xs font-medium leading-snug text-[var(--text-primary)]">{category.label}</span>
    </button>
  );
}
