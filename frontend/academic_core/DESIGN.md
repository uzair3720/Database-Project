---
name: Academic Core
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#434655'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#3e3fcc'
  on-tertiary: '#ffffff'
  tertiary-container: '#585be6'
  on-tertiary-container: '#f1eeff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 32px
  xl: 48px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style

The design system is engineered to elevate the university learning experience from a utilitarian tool to a premium academic environment. It targets a demographic of digital-native students and faculty who require high cognitive clarity and a sense of institutional reliability.

The visual style is **Corporate / Modern** with a strong emphasis on **Minimalism** and **Tactile** depth. It moves away from the flat, generic aesthetics of legacy LMS platforms by introducing significant roundedness, sophisticated elevation, and a hierarchy that prioritizes content over container. The emotional response should be one of "focused calm"—organized, dependable, and inspiring.

## Colors

The palette is anchored by "University Blue," a high-vibrancy primary color that signals authority and action. Surfaces utilize a tiered neutral system to create a sense of structure without relying on heavy lines.

- **Primary (#2563EB):** Used for primary actions, active navigation states, and progress indicators.
- **Surface Neutrals (#F8FAFC, #FFFFFF):** The background uses the subtle gray to define the "canvas," while white is reserved for interactive cards and content containers.
- **Academic Accents:** Emerald (#10B981), Indigo (#6366F1), and Amber (#F59E0B) are designated for course-specific banners and categorization, allowing students to visually distinguish between subjects at a glance.
- **High-Contrast Text:** All body text is set in deep grays or blacks to ensure WCAG AA compliance against white surfaces.

## Typography

This design system uses a dual-font approach to balance technical precision with extreme readability. **Geist** is used for headlines and UI labels to provide a clean, slightly technical "developer-grade" precision. **Inter** handles all body copy to ensure long-form reading comfort in assignments and forum posts.

On mobile devices, `display-lg` should scale down to 32px, and `headline-lg` should scale to 24px to prevent excessive line wrapping. Paragraph spacing is generous (1.5x font size) to reduce visual density in text-heavy course materials.

## Layout & Spacing

The system follows a **Fluid Grid** model with a 12-column structure for desktop. 

- **Desktop (1440px+):** 12 columns, 24px gutters, 40px external margins. Sidebar is fixed at 280px.
- **Tablet (768px - 1439px):** 8 columns, 16px gutters. Sidebar collapses into a drawer.
- **Mobile (< 768px):** 4 columns, 12px gutters, 16px external margins. 

The vertical rhythm is based on a 4px baseline. Components like course cards should use `md` (24px) internal padding to feel spacious and premium. Navigation items use `sm` (16px) padding for optimal touch targets.

## Elevation & Depth

This design system rejects flat, heavy borders in favor of **Ambient Shadows** and **Tonal Layering**. Depth is used to communicate interactivity and hierarchy:

1.  **Level 0 (Canvas):** The base background (#F8FAFC). No shadow.
2.  **Level 1 (Cards/Sidebar):** White surfaces (#FFFFFF) with a very soft, diffused shadow: `0px 4px 20px rgba(0, 0, 0, 0.04)`.
3.  **Level 2 (Hover States/Menus):** When a course card or button is hovered, it rises with a more pronounced shadow: `0px 12px 32px rgba(37, 99, 235, 0.08)`.
4.  **Level 3 (Modals/Popovers):** High-contrast elevation to focus the user: `0px 20px 48px rgba(0, 0, 0, 0.12)`.

Thin, low-contrast outlines (1px solid #E2E8F0) are used sparingly to define card boundaries on Level 1 surfaces.

## Shapes

The design system adopts a **Rounded** shape language to feel approachable and modern. 

- **Base Radius (8px):** Used for small components like inputs, chips, and small buttons.
- **Large Radius (16px):** Used for primary course cards, main content containers, and navigation sidebars.
- **Avatar Radius:** Always circular (full pill) to differentiate human elements from structural UI elements.

All buttons should use the base radius (8px) rather than pills to maintain a professional, academic structure.

## Components

### Course Cards
The centerpiece of the dashboard. Features a 160px height header image/color block with a 16px top-radius. The bottom section (white) contains the course title (Headline-SM) and instructor name. Action icons (folder, assignments) are placed in a dedicated footer bar with a subtle top border.

### Navigation Sidebar
A clean, Level 1 surface. Active states use a "vertical pill" indicator: a 4px wide blue line on the left edge and a subtle blue tint (#EFF6FF) for the background of the menu item.

### Buttons
- **Primary:** Solid #2563EB with white text. 8px radius. Subtle scale-down effect (0.98) on click.
- **Secondary:** Ghost style with #2563EB text and border.
- **Tertiary:** Pure text with a light blue background appearing only on hover.

### Tabbed Interfaces
Used for "Stream," "Classwork," and "People." Tabs are represented by Geist Label-MD text. The active tab is indicated by a 3px thick bottom border in University Blue with 8px of padding between the text and the line.

### Inputs & Selects
Faded gray backgrounds (#F1F5F9) that transition to White (#FFFFFF) with a University Blue border on focus. Labels always sit above the input in Geist Label-SM.

### Animations
- **Hover:** 200ms ease-out transitions for shadows and background colors.
- **Page Entry:** Content should perform a subtle "fade-and-rise" (20px vertical shift) when navigating between tabs or courses.