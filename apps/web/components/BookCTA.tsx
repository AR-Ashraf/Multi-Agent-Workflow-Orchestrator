"use client";

import { BOOK_URL, EVENTS, track } from "@/lib/analytics";

/**
 * The "Book a build call" conversion CTA (CLAUDE.md §11). Fires the `book_call`
 * funnel event and links to the real booking URL (NEXT_PUBLIC_BOOK_URL) when
 * configured, falling back to the on-page #book anchor. `location` tags where on
 * the page the click came from for attribution.
 */
export function BookCTA({
  className = "btn btn-gold",
  children = "Book a build call →",
  location,
  onClick,
}: {
  className?: string;
  children?: React.ReactNode;
  location?: string;
  onClick?: () => void;
}) {
  const external = BOOK_URL.startsWith("http");
  return (
    <a
      href={BOOK_URL}
      className={className}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      onClick={() => {
        track(EVENTS.bookCall, location ? { location } : {});
        onClick?.();
      }}
    >
      {children}
    </a>
  );
}
