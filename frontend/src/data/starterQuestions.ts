// The 6 category cards shown on widget open (spec Section 6). Question text
// is verbatim from the spec - do not reword, it's sent exactly as-is when a
// card is clicked.

export interface StarterQuestion {
  id: string;
  label: string;
  icon: string;
  question: string;
}

export const STARTER_QUESTIONS: StarterQuestion[] = [
  {
    id: "demat",
    label: "Demat Services",
    icon: "🗂️",
    question: "How do I open a Demat account with Prabhu Capital, and what are the charges?",
  },
  {
    id: "mutual-fund",
    label: "Mutual Funds & SIP",
    icon: "📈",
    question: "What mutual fund schemes and SIP options does Prabhu Capital offer?",
  },
  {
    id: "pms",
    label: "Portfolio Management (PMS)",
    icon: "💼",
    question: "What is Prabhu Capital's Portfolio Management Service and how can I enroll?",
  },
  {
    id: "ipo",
    label: "IPO & Share Issues",
    icon: "🏦",
    question: "How can I apply for an IPO through Prabhu Capital, and how do I check share allotment?",
  },
  {
    id: "rts",
    label: "Share Registrar (RTS)",
    icon: "📜",
    question: "What Registrar to Shares services does Prabhu Capital provide to companies and shareholders?",
  },
  {
    id: "fees",
    label: "Fees, Forms & Downloads",
    icon: "📄",
    question: "Where can I find Prabhu Capital's forms, and what are the Demat renewal fees?",
  },
];
