import { useEffect, useState } from "react";
import { QuoteIcon } from "../lib/icons";

// Static, curated content (Decision #72) -- no backend, no external
// dependency, matches how this project treats content that doesn't need to
// change without a redeploy (same instinct as Decisions #15/#47/#51).
const AFFIRMATIONS: string[] = [
  "The journey of a thousand miles begins with a single step. — Lao Tzu",
  "It always seems impossible until it's done. — Nelson Mandela",
  "Fall seven times, stand up eight. — Japanese proverb",
  "Well begun is half done. — Ancient proverb",
  "A little progress each day adds up to big results.",
  "The expert in anything was once a beginner.",
  "Consistency turns effort into mastery.",
  "You don't have to see the whole staircase, just take the first step. — Martin Luther King Jr.",
  "Study today so tomorrow's problems feel familiar.",
  "Every system you understand today is one less surprise in the interview.",
  "Small, steady steps outlast bursts of intensity.",
  "Difficult roads often lead to beautiful destinations.",
  "Patience, persistence, and perspiration make an unbeatable combination for success. — Napoleon Hill",
  "The best time to plant a tree was 20 years ago. The second best time is now. — Chinese proverb",
  "Confidence comes from preparation, not luck.",
  "What you learn today becomes the instinct you rely on tomorrow.",
  "Progress, not perfection.",
  "One more topic understood is one more question you won't fear.",
];

const REFRESH_INTERVAL_MS = 120_000; // 2 minutes 

function randomIndexExcluding(length: number, exclude: number): number {
  if (length <= 1) return 0;
  let next = Math.floor(Math.random() * length);
  if (next === exclude) next = (next + 1) % length;
  return next;
}

export function AffirmationWidget() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * AFFIRMATIONS.length));

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((current) => randomIndexExcluding(AFFIRMATIONS.length, current));
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="affirmation-widget">
      <QuoteIcon className="affirmation-quote-icon" size={18} />
      <span className="affirmation-text">{AFFIRMATIONS[index]}</span>
    </div>
  );
}
