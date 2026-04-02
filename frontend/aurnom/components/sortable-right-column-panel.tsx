"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { ReactNode } from "react";

export function SortableRightColumnPanel({ id, children }: { id: string; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
  };
  return (
    <div ref={setNodeRef} style={style} className="mb-1">
      <div className="grid grid-cols-[1.25rem_minmax(0,1fr)] items-start gap-x-1">
        <button
          type="button"
          className="mt-1 shrink-0 cursor-grab touch-none text-ui-muted hover:text-cyber-cyan active:cursor-grabbing"
          aria-label="Drag to reorder panel"
          {...listeners}
          {...attributes}
        >
          ⋮⋮
        </button>
        <div className="min-w-0 [&_section]:mb-0">{children}</div>
      </div>
    </div>
  );
}
