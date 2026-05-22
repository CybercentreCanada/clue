# Clue Plugin Pipeline Builder — UI PoC Plan

## Goal

Add a `/builder` route to the existing Clue React app that lets users visually assemble an **ordered enrichment pipeline** for a given indicator type by dragging blocks from a catalogue onto a vertical canvas — mirroring the core UX of notebook-builder, but using Clue's tech stack (React + MUI + `@dnd-kit`).

The PoC is **pure frontend**: no new backend endpoints, no execution. The objective is to validate the drag-and-drop composition UI before wiring it to real plugin data.

---

## Scope

| In scope (PoC) | Out of scope (for now) |
|---|---|
| Catalogue pane with static block definitions | Live data from Clue API / plugins |
| Drag blocks from catalogue onto pipeline canvas | Pipeline execution / Jupyter integration |
| Reorder / delete steps on canvas | Saving notebooks to server |
| Step detail panel (static config fields) | Auth / per-user persistence |
| New `/builder` route in Clue's React app | Backend API changes |

---

## Tech Stack Mapping

| notebook-builder (Angular) | Clue equivalent |
|---|---|
| `@angular/cdk/drag-drop` (`cdkDrag`, `cdkDropList`) | `@dnd-kit/core` + `@dnd-kit/sortable` (already in `ui/package.json`) |
| Angular Material (`mat-expansion-panel`, `mat-card`) | MUI (`Accordion`, `Card`, `Paper`) |
| `@ngx-translate` | `react-i18next` (already used in Clue) |
| Angular signals | React `useState` / `useReducer` |
| Angular services (singleton) | React context + custom hooks |

`@dnd-kit` is already a declared dependency — no new packages are required.

---

## Architecture

```
ui/src/
  components/
    routes/
      Builder.tsx               ← new top-level route component
    builder/
      BuilderPage.tsx           ← layout: catalogue | canvas
      catalogue/
        Catalogue.tsx           ← left pane, search, grouped blocks
        CatalogueItem.tsx       ← draggable block chip
      canvas/
        PipelineCanvas.tsx      ← sortable drop zone
        PipelineStep.tsx        ← individual dropped step card
        StepDetailPanel.tsx     ← right panel, static config fields
      hooks/
        usePipelineState.ts     ← useReducer for pipeline state
      data/
        blockDefinitions.ts     ← static catalogue data (PoC)
      types.ts                  ← shared TS types
```

Register in `App.tsx`:
```tsx
<Route path="/builder" element={<Builder />} />
```

---

## Data Model

### Block Definition (catalogue entry)
```ts
interface BlockDefinition {
  id: string;           // e.g. "virustotal.hash"
  label: string;        // "VirusTotal Hash Lookup"
  category: string;     // "Threat Intel" | "Network" | "Sandbox" | ...
  icon?: string;        // MUI icon name or data URL
  description: string;
  configFields: ConfigField[];  // static form schema
}

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'select' | 'boolean';
  options?: string[];   // for 'select'
  defaultValue?: unknown;
}
```

### Pipeline Step (canvas item)
```ts
interface PipelineStep {
  instanceId: string;       // uuid — unique per drop
  definitionId: string;     // references BlockDefinition.id
  config: Record<string, unknown>;
}
```

### Pipeline State
```ts
interface PipelineState {
  indicatorType: string;    // "ip" | "domain" | "hash" | "url"
  steps: PipelineStep[];
  selectedStepId: string | null;
}
```

---

## Drag-and-Drop Design (dnd-kit)

The notebook-builder uses two connected `cdkDropList`s: one for the catalogue (source, copy semantics) and one for the canvas (destination, sortable). `@dnd-kit` achieves the same with two distinct patterns:

### Catalogue → Canvas (copy drop)
- Wrap the catalogue in `<DndContext>` at the `BuilderPage` level.
- Each `CatalogueItem` is a `useDraggable` source with `data = { type: 'catalogue', definitionId }`.
- `PipelineCanvas` is a `useDroppable` target.
- On `onDragEnd`, if `over.id === 'pipeline-canvas'` and `active.data.type === 'catalogue'`, dispatch `ADD_STEP` to create a new `PipelineStep` instance.

### Canvas reorder (sortable)
- Steps inside `PipelineCanvas` are wrapped in `<SortableContext items={stepIds} strategy={verticalListSortingStrategy}>`.
- Each `PipelineStep` uses `useSortable`.
- On `onDragEnd`, if both `active` and `over` are canvas steps, dispatch `MOVE_STEP` using `arrayMove`.

### Drag preview
- Use `@dnd-kit`'s `<DragOverlay>` to render a floating chip showing the block label during drag, matching notebook-builder's `*cdkDragPreview`.

---

## Component Breakdown

### `BuilderPage.tsx`
- Two-column MUI layout (`Box` with `flexDirection: row`).
- Houses the shared `<DndContext onDragEnd={handleDragEnd}>`.
- Left: `<Catalogue>` (~300 px, resizable via a drag handle or just fixed for PoC).
- Right: `<PipelineCanvas>` + optional `<StepDetailPanel>` drawer.

### `Catalogue.tsx`
- MUI `TextField` for fuzzy search (using `fuse.js`, already in Clue).
- `blockDefinitions` grouped by `category`, rendered as MUI `Accordion` panels — one per category.
- Each item renders `<CatalogueItem>`.

### `CatalogueItem.tsx`
- `useDraggable({ id: def.id, data: { type: 'catalogue', definitionId: def.id } })`.
- MUI `Paper` chip with icon, label, description.
- While dragging (`isDragging`), apply reduced opacity (catalogue stays in place; the `DragOverlay` is the visual ghost).

### `PipelineCanvas.tsx`
- `useDroppable({ id: 'pipeline-canvas' })`.
- `<SortableContext>` wrapping the list of `<PipelineStep>` components.
- Empty state: dashed-border drop zone with "Drag a block here" hint.
- Highlighted border when a catalogue item is dragged over it.

### `PipelineStep.tsx`
- `useSortable({ id: step.instanceId })`.
- MUI `Card`: drag handle icon (left), block label + category chip, delete button (right).
- Click → `setSelectedStepId(step.instanceId)` to open detail panel.

### `StepDetailPanel.tsx`
- MUI `Drawer` (persistent, right side) or inline panel.
- Renders `configFields` from the selected step's `BlockDefinition` as MUI form controls.
- Changes dispatched via `UPDATE_STEP_CONFIG`.

### `usePipelineState.ts`
```ts
type Action =
  | { type: 'ADD_STEP'; definitionId: string }
  | { type: 'MOVE_STEP'; from: number; to: number }
  | { type: 'DELETE_STEP'; instanceId: string }
  | { type: 'UPDATE_STEP_CONFIG'; instanceId: string; patch: Record<string, unknown> }
  | { type: 'SET_INDICATOR_TYPE'; indicatorType: string }
  | { type: 'SELECT_STEP'; instanceId: string | null };

// useReducer(pipelineReducer, initialState)
```

---

## Static Block Catalogue (PoC)

Define ~10 representative blocks drawn from Clue's known plugins, grouped by category:

```ts
// blockDefinitions.ts
export const BLOCK_DEFINITIONS: BlockDefinition[] = [
  {
    id: 'virustotal.hash',
    label: 'VirusTotal Hash',
    category: 'Threat Intel',
    icon: 'security',
    description: 'Lookup a file hash in VirusTotal.',
    configFields: [{ key: 'api_key', label: 'API Key', type: 'text' }],
  },
  {
    id: 'crtsh.domain',
    label: 'crt.sh Certificate Search',
    category: 'Network',
    icon: 'verified',
    description: 'Find certificates for a domain via crt.sh.',
    configFields: [],
  },
  {
    id: 'assemblyline.submit',
    label: 'AssemblyLine Submit',
    category: 'Sandbox',
    icon: 'cloud_upload',
    description: 'Submit a file or URL to AssemblyLine for analysis.',
    configFields: [
      { key: 'url', label: 'AssemblyLine URL', type: 'text' },
      { key: 'classification', label: 'Classification', type: 'select', options: ['TLP:WHITE', 'TLP:GREEN', 'TLP:AMBER'] },
    ],
  },
  {
    id: 'malware_bazaar.hash',
    label: 'MalwareBazaar Hash',
    category: 'Threat Intel',
    icon: 'bug_report',
    description: 'Query MalwareBazaar for a known malware hash.',
    configFields: [],
  },
  {
    id: 'port_lookup.ip',
    label: 'Port Lookup',
    category: 'Network',
    icon: 'router',
    description: 'Check open ports for an IP address.',
    configFields: [{ key: 'timeout', label: 'Timeout (s)', type: 'text', defaultValue: '5' }],
  },
  // ... add more as needed
];
```

Category colors and icons can mirror Clue's existing `CATEGORY_COLORS` / `CATEGORY_ICONS` patterns from the Clue models.

---

## File Register / Routing

1. Create `ui/src/components/routes/Builder.tsx` (thin wrapper).
2. Add `<Route path="/builder" element={<Builder />} />` in `App.tsx`.
3. Add a nav link to the existing left-side drawer (see `ui/src/components/app/drawers/`).

---

## Styling

- Use MUI `sx` prop throughout — no new CSS files needed for PoC.
- Two-column split: `display: flex`, left pane `width: 300px`, right pane `flex: 1`.
- Step cards: consistent `borderLeft: 4px solid <categoryColor>` accent matching notebook-builder's visual cue.
- `DragOverlay` chip: small elevated `Paper` with the block label + icon.

---

## Implementation Sequence

1. **Types & data** — `types.ts` + `blockDefinitions.ts` (no UI yet).
2. **State hook** — `usePipelineState.ts` with all actions and tests.
3. **Catalogue** — `Catalogue.tsx` + `CatalogueItem.tsx` (render only, no drag yet).
4. **Canvas** — `PipelineCanvas.tsx` + `PipelineStep.tsx` (render only).
5. **Wire dnd-kit** — `BuilderPage.tsx` adds `DndContext`, `DragOverlay`, and `onDragEnd` handler connecting catalogue → canvas and canvas reorder.
6. **Detail panel** — `StepDetailPanel.tsx` with static config form.
7. **Route + nav** — register `/builder`, add drawer link.
8. **Polish** — empty state, search filter, keyboard accessibility (dnd-kit supports keyboard by default).

---

## Key Differences vs. notebook-builder

| Concern | notebook-builder | Clue PoC |
|---|---|---|
| Drag library | Angular CDK drag-drop | `@dnd-kit` (core + sortable) |
| Two-list connection | `cdkDropListConnectedTo` | Shared `DndContext` + `useDroppable` / `useSortable` |
| Copy semantics (catalogue) | `cdkDropListSortingDisabled` + `noopDrop()` | Detect `active.data.type === 'catalogue'` in `onDragEnd`, create new instance |
| Step preview | `*cdkDragPreview` | `<DragOverlay>` portal |
| Config editing | `StepEditDialog` (modal) | `StepDetailPanel` (persistent right drawer) |
| State management | Angular signals | `useReducer` hook |
