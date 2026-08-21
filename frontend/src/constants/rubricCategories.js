// Mirrors backend/app/services/answer_evaluation/rubrics.py
// (CATEGORY_DESCRIPTIONS / CATEGORY_LABELS / FOCUSABLE_CATEGORIES /
// MAX_FOCUS_CATEGORIES) — the canonical set of rubric categories a
// candidate can ask to focus practice on, independent of question type.
// Shared between the setup page's focus-area picker, the dashboard's
// "Practice weak areas" CTA, and the results/interview pages' focus badges,
// so the label/description text and the 3-category cap only live in one
// place on the frontend.

export const RUBRIC_CATEGORIES = [
  { key: 'relevance', label: 'Relevance', description: 'Directly addressing what was actually asked.' },
  { key: 'clarity', label: 'Clarity', description: 'How clear and easy to follow the explanation is.' },
  { key: 'structure', label: 'Structure', description: 'Organized delivery, e.g. Situation-Task-Action-Result.' },
  { key: 'specificity', label: 'Specificity / Examples', description: 'Citing a specific, concrete example or outcome.' },
  { key: 'communication', label: 'Communication', description: 'Confidence, concision, and overall communication quality.' },
  { key: 'technical_accuracy', label: 'Technical Accuracy', description: 'Correctness of technical claims and terminology.' },
  { key: 'completeness', label: 'Completeness', description: 'Covering the key aspects, edge cases, and tradeoffs.' },
  { key: 'reasoning', label: 'Reasoning / Problem Solving', description: 'Explaining the reasoning and tradeoffs behind an approach.' },
  { key: 'examples', label: 'Examples', description: 'Grounding answers in a concrete example, metric, or use case.' },
]

export const CATEGORY_LABELS = Object.fromEntries(
  RUBRIC_CATEGORIES.map((c) => [c.key, c.label]),
)

export const MAX_FOCUS_CATEGORIES = 3

export function categoryLabel(key) {
  return CATEGORY_LABELS[key] ?? key
}
