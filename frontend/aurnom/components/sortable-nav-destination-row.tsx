"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { ReactNode } from "react";

export function SortableNavDestinationRow({ id, children }: { id: string; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
  };
  return (
    <div ref={setNodeRef} style={style} className="flex min-w-0 items-stretch gap-1">
      <button
        type="button"
        className="mt-0.5 h-fit shrink-0 cursor-grab touch-none text-ui-muted hover:text-cyber-cyan active:cursor-grabbing"
        aria-label="Drag to reorder destination"
        {...listeners}
        {...attributes}
      >
        ⋮⋮
      </button>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
