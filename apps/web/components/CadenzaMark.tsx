export function CadenzaMark({ className = "mark" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Cadenza mark"
      role="img"
    >
      <circle cx="20" cy="20" r="19" fill="#1B2230" />
      <circle cx="20" cy="20" r="19" stroke="#C99A33" strokeWidth="1.5" />
      <circle cx="11" cy="20" r="3.1" fill="#C99A33" />
      <circle cx="20" cy="11.5" r="2.5" fill="#FAF6EF" />
      <circle cx="29" cy="20" r="2.5" fill="#FAF6EF" />
      <circle cx="20" cy="28.5" r="2.5" fill="#FAF6EF" />
      <path
        d="M11 20 L20 11.5 M11 20 L29 20 M11 20 L20 28.5"
        stroke="#C99A33"
        strokeWidth="1.3"
        opacity="0.8"
      />
    </svg>
  );
}
