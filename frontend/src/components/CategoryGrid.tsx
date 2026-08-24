import { STARTER_QUESTIONS } from "../data/starterQuestions";
import { CategoryCard } from "./CategoryCard";

export function CategoryGrid({ onSelect }: { onSelect: (question: string) => void }) {
  return (
    <div className="px-4 py-4">
      <p className="mb-3 text-sm text-[var(--text-muted)]">Choose an option below for quick assistance</p>
      <div className="grid grid-cols-2 gap-2.5">
        {STARTER_QUESTIONS.map((category) => (
          <CategoryCard key={category.id} category={category} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}
