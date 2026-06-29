"use client";

import { useState } from "react";
import { BookCTA } from "@/components/BookCTA";
import { CadenzaMark } from "@/components/CadenzaMark";

const LINKS = [
  { href: "#demo", label: "Live demo" },
  { href: "#why", label: "Why it’s hard" },
  { href: "#how", label: "How it works" },
  { href: "#tech", label: "Under the hood" },
];

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="nav">
      <div className="wrap nav-inner">
        <a className="brand" href="#top" onClick={() => setOpen(false)}>
          <CadenzaMark />
          <div>
            <div className="brand-name">Cadenza</div>
            <div className="brand-sub">by Devs Core</div>
          </div>
        </a>

        <nav className="nav-links" aria-label="Primary">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href}>
              {l.label}
            </a>
          ))}
        </nav>

        <div className="nav-right">
          <BookCTA className="btn btn-gold btn-sm nav-cta-desktop" location="nav">
            Book a build call
          </BookCTA>
          <button
            className="nav-burger"
            aria-label="Toggle menu"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {open ? (
                <path d="M6 6l12 12M6 18L18 6" />
              ) : (
                <>
                  <path d="M3 6h18" />
                  <path d="M3 12h18" />
                  <path d="M3 18h18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      <div className={`mobile-sheet ${open ? "open" : ""}`}>
        {LINKS.map((l) => (
          <a key={l.href} href={l.href} onClick={() => setOpen(false)}>
            {l.label}
          </a>
        ))}
        <BookCTA className="btn btn-gold" location="nav_mobile" onClick={() => setOpen(false)}>
          Book a build call
        </BookCTA>
      </div>
    </header>
  );
}
