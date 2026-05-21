---
name: Midnight Executive
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#b7c8e1'
  on-secondary: '#213145'
  secondary-container: '#3a4a5f'
  on-secondary-container: '#a9bad3'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-lg:
    fontFamily: Geist
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  container-padding: 20px
---

## Brand & Style

The design system is engineered for a high-performance provider portal, prioritizing efficiency, clarity, and a sense of "premium reliability." The brand personality is authoritative yet assistive, designed to make complex service management feel effortless.

The aesthetic follows a **Modern Corporate Minimalism** approach. It leverages deep navy tonal layering to create a sophisticated dark environment where vibrant blue accents guide the eye toward critical actions. The UI utilizes generous whitespace (negative space) even in a dark theme to prevent information density from overwhelming the user, ensuring a focused and professional experience.

## Colors

The palette is anchored by "Midnight Navy" backgrounds to reduce eye strain and provide a canvas of depth. 

- **Primary Blue (#3b82f6):** Reserved strictly for primary call-to-actions, active states, and essential progress indicators.
- **Surface Navy (#1e293b):** Used for cards, input backgrounds, and modals to create visual separation from the base background.
- **Secondary Slate (#64748b):** Utilized for secondary text, icons, and non-interactive decorative elements.
- **Functional Colors:** Success and Error tokens are high-chroma to ensure immediate recognition against the dark backdrop.

## Typography

This design system utilizes **Geist** for its technical precision and exceptional legibility in digital interfaces. The type scale is optimized for a mobile-first provider experience.

- **Headlines:** Use a semi-bold weight with slight negative letter spacing to feel compact and "locked-in."
- **Body Text:** Uses a regular weight with generous line height (1.5x) to ensure long-form data is easily digestible.
- **Labels:** Small caps or medium weights are used for metadata and form headers to distinguish them clearly from user input data.

## Layout & Spacing

The layout is built on a **Fluid 8px Grid** system. On mobile, we utilize a 4-column grid with 16px gutters and 20px side margins to ensure content doesn't feel cramped against the bezel.

Spacing follows a strict mathematical progression:
- **Consistent Rhythm:** Use `md` (16px) for internal card padding and `lg` (24px) for vertical section spacing.
- **Visual Grouping:** Related elements (like a label and its input) should use `xs` (4px) or `base` (8px) spacing to establish clear proximity.

## Elevation & Depth

Depth is communicated through **Tonal Layering** rather than traditional heavy shadows. In this dark mode environment, higher elevation is represented by lighter surface colors.

- **Level 0 (Base):** #0f172a (Deepest Navy).
- **Level 1 (Cards/Inputs):** #1e293b (Surface Navy).
- **Level 2 (Modals/Popovers):** #2d3748.

For interactive elements like floating action buttons, a subtle, diffused shadow with a 20% opacity primary blue tint (`rgba(59, 130, 246, 0.2)`) is used to suggest a soft glow, reinforcing the premium feel without introducing visual clutter.

## Shapes

The shape language is defined by a "High Roundedness" philosophy to soften the technical nature of the portal and make the app feel more modern and approachable.

- **Standard Elements:** Buttons and Input Fields use a base 0.5rem (8px) radius.
- **Large Containers:** Content cards and bottom sheets use a 1.5rem (24px) radius on top corners to create a distinctive, high-end mobile silhouette.
- **Status Indicators:** Pills and chips utilize a fully rounded (999px) radius to distinguish them from interactive containers.

## Components

### Buttons
- **Primary:** Solid #3b82f6 with white text. High-padding (16px vertical) for a tactile, easy-to-tap feel.
- **Secondary:** Transparent with a 1px border of #64748b.
- **Tertiary:** Text-only in primary blue for low-priority actions.

### Input Fields
Inputs are critical for the provider portal. They should feature:
- A background of `surface_color_hex` (#1e293b).
- A 1px border that shifts from #334155 (default) to #3b82f6 (focus).
- Floating labels that transition to `label-sm` when active.

### Cards
Cards are the primary vehicle for displaying service requests and earnings. 
- Use Level 1 elevation (#1e293b).
- Ensure 20px internal padding.
- Use a very subtle 1px inner border of #334155 to define edges against the background.

### Status Chips
Use background tints of functional colors at 15% opacity (e.g., Green text on dark green tint) to indicate job statuses like "In Progress" or "Completed."