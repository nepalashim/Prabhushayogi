// Inline SVG placeholder avatar using the brand colors. No logo asset exists
// yet - swap the <svg> below for an <img src="..."> once one is supplied,
// everything else (sizing, layout) stays the same.
export function Avatar({ size = 40 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      role="img"
      aria-label="Prabhu Sahayogi"
      className="shrink-0 rounded-full"
    >
      <circle cx="20" cy="20" r="20" fill="var(--brand-green)" />
      <circle cx="20" cy="20" r="20" fill="none" stroke="var(--brand-red)" strokeWidth="2" />
      <text
        x="20"
        y="26"
        textAnchor="middle"
        fontSize="16"
        fontWeight="700"
        fill="white"
        fontFamily="system-ui, sans-serif"
      >
        PS
      </text>
    </svg>
  );
}
