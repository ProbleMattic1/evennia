import type { ButtonHTMLAttributes } from "react";

export type PanelExpandButtonProps = Pick<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "disabled" | "id"
> & {
  open: boolean;
  onClick: () => void;
  "aria-label": string;
  /** Layout-only classes (e.g. shrink-0, ml-auto). Colors come from `.panel-expand-toggle` in globals.css. */
  className?: string;
};

export function PanelExpandButton({
  open,
  onClick,
  "aria-label": ariaLabel,
  className = "",
  disabled,
  id,
}: PanelExpandButtonProps) {
  return (
    <button
      type="button"
      id={id}
      disabled={disabled}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-expanded={open}
      data-expanded={open ? "true" : "false"}
      className={["panel-expand-toggle px-1", className].filter(Boolean).join(" ")}
    >
      {open ? "▴" : "▸"}
    </button>
  );
}
