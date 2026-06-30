---
name: Technical Monolith Design System
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#4c4546'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#5f5e5e'
  outline-variant: '#c6c6c6'
  surface-tint: '#5e5e5e'
  primary: '#000000'
  on-primary: '#dfe0ff'
  primary-container: '#0021b4'
  on-primary-container: '#848484'
  inverse-primary: '#c6c6c6'
  secondary: '#5f5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2dfdf'
  on-secondary-container: '#636262'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#0c1c30'
  on-tertiary-container: '#76859d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#1f41ff'
  primary-fixed-dim: '#0029d3'
  on-primary-fixed: '#1b1b1b'
  on-primary-fixed-variant: '#474747'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c6'
  on-secondary-fixed: '#1c1b1c'
  on-secondary-fixed-variant: '#474647'
  tertiary-fixed: '#d4e3fe'
  tertiary-fixed-dim: '#b8c7e2'
  on-tertiary-fixed: '#0c1c30'
  on-tertiary-fixed-variant: '#39485d'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 72px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  display-md:
    fontFamily: Inter
    fontSize: 56px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  display-sm:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.05em
spacing:
  spacing-1: 0.35rem
  spacing-2: 0.7rem
  spacing-3: 1rem
  spacing-4: 1.4rem
  spacing-8: 2.8rem
  spacing-16: 5.5rem
  spacing-24: 8.5rem
---

# Design System Specification: The Architectural Objective

## 1. Overview & Creative North Star

**Creative North Star: The Technical Monolith**

This design system is an exercise in restraint, precision, and mathematical beauty. Inspired by the International Typographic Style (Swiss Design) and high-end horology, it rejects the "friendly" softness of contemporary web trends in favor of an objective, architectural aesthetic.

The system breaks the "template" feel through **extreme whitespace** and **asymmetric balance**. We do not fill space; we curate it. By utilizing a strict modular grid and hairline-thin accents, we create a digital environment that feels like a premium blueprint or a gallery monograph. It is sophisticated, cold to the touch, and unapologetically functional.

---

## 2. Colors & Surface Logic

The palette is a refined monochromatic study, utilizing high-contrast transitions to define space without the need for visual "noise."

### The Palette

- **Core:** `background` (#f8f9fa) and `primary` (#000000). This 100% contrast ratio is our primary engine.
- **Accents:** `primary_fixed` (#1f41ff) is our "Electric Precision" blue. Use this *only* for critical data points, active technical states, or singular focal points. It is a laser, not a wash.
- **Neutrals:** `secondary` (#5f5e5e) and `surface_variant` (#e1e3e4) provide the tonal depth of brushed steel and concrete.

### The "No-Line" Rule (Exceptions for Hairlines)

While traditional 1px borders are forbidden for sectioning, this system permits **Hairline Accents** using `outline_variant` (#c6c6c6) at `0.5px` thickness. For structural containment, prioritize:

- **Surface Nesting:** Use `surface_container_low` (#f3f4f5) against `surface` (#f8f9fa) to define regions.
- **Tonal Transitions:** A shift from `surface` to `surface_container_highest` (#e1e3e4) creates a "block" without a physical boundary.

### Glass & Texture

- **Technical Transparency:** Floating menus must use `surface` at 80% opacity with a `20px` backdrop-blur. This simulates frosted glass common in high-end architectural partitions.
- **The CTA Gradient:** For high-impact actions, use a subtle linear gradient from `primary` (#000000) to `primary_container` (#0021b4) at a 45-degree angle. This adds a "machined" depth to otherwise flat elements.

---

## 3. Typography: The Grid of Language

Typography is the primary visual furniture of this system. We use **Inter** with tight tracking (-0.02em) and variable weights to mimic the precision of a watch face.

- **Display (display-lg/md/sm):** Use `weight: 600`. These are your structural anchors. Always maintain "Massive Whitespace" around display type—at least `spacing-24` (8.5rem).
- **Headlines & Titles:** Use `weight: 500`. These should feel like captions in an art gallery—understated but authoritative.
- **The Body (body-lg/md/sm):** Use `weight: 400`. For body text, increase line-height to 1.6 to ensure the "Swiss" airy feel.
- **Labels (label-md/sm):** The "Technical" layer. Use `weight: 700` and `uppercase` for labels to signify data points or metadata.

---

## 4. Elevation & Depth: Tonal Layering

We reject the "Drop Shadow." Depth is achieved through the **Layering Principle**:

1. **Level 0 (Base):** `surface` (#f8f9fa).
2. **Level 1 (In-set):** `surface_container_lowest` (#ffffff). Use this for input fields or data wells to create a "carved" look.
3. **Level 2 (Raised):** `surface_container_high` (#e7e8e9).
4. **The Ambient Lift:** If a component must float (e.g., a modal), use a shadow with a `64px` blur, `0.04` opacity, using the `on_surface` (#191c1d) color. It should be felt, not seen.
5. **The Ghost Border:** For accessibility on white-on-white elements, use a `0.5px` border of `outline_variant` at 20% opacity.

---

## 5. Components

### Buttons: The Machined Trigger

- **Primary:** `background: primary` (#000000), `text: on_primary` (#dfe0ff). Radius: `0px`.
- **Secondary:** `background: transparent`, `border: 0.5px solid primary`.
- **Interaction:** On hover, the background should shift to `primary_fixed_dim` (#0029d3) with a `200ms` ease-out transition.

### Input Fields: The Blueprint Entry

- **Default State:** A single `0.5px` bottom border using `outline`. No side or top borders.
- **Focus State:** Bottom border transitions to `primary_fixed` (#1f41ff) with a `1px` thickness.
- **Label:** `label-sm`, uppercase, positioned exactly `spacing-1` above the input.

### Cards & Lists: The Modular Grid

- **Rule:** Absolute prohibition of divider lines between list items.
- **Separation:** Use `spacing-4` (1.4rem) of vertical whitespace or an alternating background of `surface` and `surface_container_low`.
- **The "Technical" Chip:** Square corners (`0px`). Use `surface_variant` background with `label-sm` text.

### Data Visualization: The Electric Blue

- Use `primary_fixed` (#1f41ff) for the primary data line.
- Use `tertiary` (#2d3c51) for secondary comparison data.
- All grid lines in charts must be `0.5px` using `outline_variant` at 50% opacity.

---

## 6. Do's and Don'ts

### Do

- **Embrace Asymmetry:** Place a `display-lg` headline on the left with a `body-md` paragraph pushed to the far right of the modular grid.
- **Use "Scale" as a Tool:** A tiny `label-sm` next to a massive `display-lg` creates a sophisticated sense of hierarchy.
- **Strict Adherence to 0px:** Rounded corners are strictly forbidden. Every element must be right-angled to maintain the architectural feel.

### Don't

- **Don't use "Soft" Grays:** Avoid warm grays. Stick to the `cool-gray` and `off-white` tokens provided to maintain the objective tone.
- **Don't Overuse the Blue:** If more than 5% of your screen is `primary_fixed`, the "Electric" effect is lost. It is for focus, not decoration.
- **No Neo-Brutalism:** Do not use thick 2px or 4px black borders. This is a system of "Hairlines," not "Heavy Strokes." Precision is paramount.

---

## 7. Spacing Logic

Utilize the spacing scale to create rhythmic "voids."

- **Countdown Margins:** `spacing-24` (8.5rem).
- **Section Gaps:** `spacing-16` (5.5rem).
- **Component Internals:** `spacing-3` (1rem) for precise, compact information density.
