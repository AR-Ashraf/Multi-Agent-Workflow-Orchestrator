"use client";

import { useState } from "react";
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
          <a href="#book" className="btn btn-gold btn-sm nav-cta-desktop">
            Book a build call
          </a>
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
        <a href="#book" className="btn btn-gold" onClick={() => setOpen(false)}>
          Book a build call
        </a>
      </div>
    </header>
  );
}
