---
name: DuckComparator
description: A calm, state-forward reconciliation ledger for large Oracle table comparisons.
colors:
  deep-ink-indigo: "oklch(0.400 0.150 270)"
  deep-ink-indigo-dark: "oklch(0.300 0.120 270)"
  deep-ink-indigo-soft: "oklch(0.950 0.025 270)"
  verified-teal: "oklch(0.520 0.105 174)"
  verified-teal-soft: "oklch(0.955 0.025 174)"
  review-amber: "oklch(0.620 0.125 72)"
  review-amber-soft: "oklch(0.960 0.030 82)"
  ledger-ink: "oklch(0.245 0.025 270)"
  ledger-muted: "oklch(0.470 0.025 270)"
  ledger-border: "oklch(0.875 0.015 270)"
  ledger-surface: "oklch(0.985 0.006 270)"
  ledger-layer: "oklch(0.960 0.012 270)"
  white: "oklch(1 0 0)"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 720
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 680
    lineHeight: 1.25
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "0.04em"
rounded:
  sm: "6px"
  md: "10px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  state-pill-match:
    backgroundColor: "{colors.verified-teal-soft}"
    textColor: "{colors.verified-teal}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "6px 10px"
  state-pill-review:
    backgroundColor: "{colors.review-amber-soft}"
    textColor: "{colors.review-amber}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "6px 10px"
  report-link:
    backgroundColor: "{colors.deep-ink-indigo}"
    textColor: "{colors.white}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "10px 14px"
  ledger-container:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ledger-ink}"
    rounded: "{rounded.md}"
    padding: "24px"
---

# Design System: DuckComparator

## Overview

**Creative North Star: "The Reconciliation Ledger"**

DuckComparator reads like a modern control ledger: deliberate, traceable, and quiet enough for the data to carry authority. The comparison state is unmistakable at the top, while the visual cadence moves naturally from outcome to coverage, exceptions, source identity, and evidence.

The system is clean, appealing, and state-forward. It uses familiar product typography, moderate information density, and flat tonal layers so operators can scan millions-of-row results without the report feeling clinical or crowded. It explicitly rejects legacy administration screens, over-minimal reports, and alarm-wallboard theatrics.

**Key Characteristics:**

- State first, with text and a symbol as well as semantic color.
- One continuous ledger rhythm instead of a grid of interchangeable cards.
- Source identity and connection IDs remain visible beside the result.
- Coverage and exceptions are grouped separately so counts have context.
- Dense evidence tables stay readable, printable, and responsive.

## Colors

Deep Ink Indigo supplies restrained product identity; teal certifies agreement, amber requests review, and cool indigo-tinted neutrals keep the ledger calm.

### Primary

- **Deep Ink Indigo:** The product anchor for links, focus, headings, and restrained emphasis. It occupies less than 10% of the report.
- **Deep Ink Indigo Dark:** Strong text or print-safe emphasis where the primary needs greater contrast.
- **Deep Ink Indigo Soft:** Selected and informational tonal surface.

### Secondary

- **Verified Teal:** The semantic state for a complete match, paired with explicit “MATCH” language and a check symbol.
- **Verified Teal Soft:** The flat state-band and pill surface for verified comparisons.

### Tertiary

- **Review Amber:** The semantic state for differences requiring review, paired with explicit “DIFFERENCES FOUND” language and a delta symbol.
- **Review Amber Soft:** A calm exception surface; never a full-screen warning wash.

### Neutral

- **Ledger Ink:** Primary text and high-value data.
- **Ledger Muted:** Supporting labels and descriptions that retain readable contrast.
- **Ledger Border:** One-pixel dividers, table rules, and container boundaries.
- **Ledger Surface:** Page background.
- **Ledger Layer:** Grouped metric and table-header background.
- **White:** Main content and printable surface.

### Named Rules

**The State Has Words Rule.** Teal and amber never communicate status alone; every state includes a symbol, a label, and a plain-language explanation.

**The Restrained Indigo Rule.** Deep Ink Indigo identifies and guides; it never becomes decorative color wash.

## Typography

**Display Font:** Inter with the system UI sans-serif stack
**Body Font:** Inter with the system UI sans-serif stack
**Label/Mono Font:** System UI sans-serif; use tabular numerals for counts

**Character:** One familiar sans-serif family keeps the report operational and platform-native. Weight, spacing, and tabular numerals provide hierarchy without introducing a display face into data UI.

### Hierarchy

- **Display** (720, 2rem, 1.15): Comparison name only; compact enough for print and narrow screens.
- **Headline** (680, 1.25rem, 1.25): Section headings and state messages.
- **Title** (650, 1rem, 1.35): Source identities and grouped metric headings.
- **Body** (400, 0.9375rem, 1.55): Explanations and metadata; prose stays within 70ch.
- **Label** (650, 0.75rem, 0.04em): Sparse operational labels; uppercase is reserved for state and compact metric labels.

### Named Rules

**The Numbers Align Rule.** Report counts use tabular numerals and right alignment wherever values form a column.

## Elevation

The system is flat by design. Depth comes from alternating tonal surfaces, one-pixel borders, spacing, and hierarchy; report components use no shadows. This preserves clarity in print and avoids floating-card decoration.

### Named Rules

**The Flat Ledger Rule.** Surfaces remain flat at rest; separate them with tone and a single ledger rule, never a wide decorative shadow.

## Components

### Header

The header is a quiet identity block with the comparison name, short description, report label, and primary-key context. It uses the white ledger surface with a single bottom rule and never competes with the state band.

### State Band

A full-width tonal band announces either “MATCH” with a check symbol or “DIFFERENCES FOUND” with a delta symbol. It pairs the state pill with a sentence describing whether review is required.

### Grouped Metric Strip

One continuous strip contains two named groups: Row coverage and Exceptions. Internal rules create rhythm without turning each metric into an identical card. Counts use tabular numerals; exact-row match rate states that its denominator is all distinct keys across both sources.

### State Pill

- **Shape:** Fully rounded status capsule.
- **Match:** Verified teal text and a verified teal soft surface, with a check symbol and the word “MATCH.”
- **Review:** Review amber text and a review amber soft surface, with a delta symbol and the words “DIFFERENCES FOUND.”

### Source Comparison

The two sources sit in a single split ledger row. Each side names the role, fully qualified schema and table, and Airflow connection ID. A centered comparison marker reinforces the relationship without implying directionality.

### Changed-Columns Table

A compact two-column evidence index with a tonal header, one-pixel row rules, descriptive empty state, and right-aligned difference counts. On narrow screens it remains horizontally scrollable; in print it stays a conventional table.

### Report Link

The Excel evidence link uses Deep Ink Indigo, white text, a 6px radius, and a visible focus outline. It describes the file and capped detail behavior; it is the only button-like action in the static report.

## Do's and Don'ts

### Do:

- **Do** lead with an explicit state label, symbol, and operational sentence.
- **Do** keep Deep Ink Indigo restrained and reserve teal and amber for meaningful state.
- **Do** group coverage and exception metrics inside one continuous ledger strip.
- **Do** show schema, table, Airflow connection ID, primary key, and detail cap plainly.
- **Do** use flat tonal layers, 1px borders, tabular numerals, responsive overflow, and print styles.

### Don't:

- **Don't** create a legacy administration screen with tiny text, dense gray grids, and crowded controls.
- **Don't** create an over-minimal report that hides primary keys, counts, or investigative evidence.
- **Don't** create an alarm wallboard dominated by bright warnings, excessive red, or visually noisy charts.
- **Don't** use a generic grid of identical metric cards, a hero metric, gradient text, glassmorphism, decorative motion, or wide side-stripe accents.
- **Don't** use color alone for status, bury source identities, or introduce external fonts, JavaScript, or web resources.
