# Markdown Documentation Standards v3-03

**Version**: v3-03
**Date**: 31 January 2026
**Type**: Standard

-----

## 1. Requirements

This document defines universal standards for document creation, versioning, and verification. These standards allow us to write better, preserve critical content, and deliver faster.

### 1.1 Writing

Writing standards govern language, tone, and content presentation.

| Requirement | Good | Bad |
|-------------|------|-----|
| **W1: British English spelling**<br>Americans can't spell and we forgive you, but not in our documents 😃 | organise, analyse, behaviour, colour, centre, labelled, travelling | organize, analyze, behavior, color, center, labeled, traveling |
| **W2: Write in positives**<br>Describe what something IS and ENABLES, not what it isn't | The Critic evaluates intentions before execution. | The Critic does not allow intentions to execute without evaluation. |
| **W3: No label formatting**<br>Use prose or proper headings, never bold labels with inline content | The system handles authentication through OAuth integration. | **Purpose:** The system handles authentication through OAuth integration. |
| **W4: Format matches function**<br>Use bullet lists for discrete items and specifications; use prose for narrative and explanation | | |
| **W5: Altitude discipline**<br>Keep philosophy, strategy, and tactics in separate sections; never mix levels | Section on "Core Philosophy" separate from section on "Implementation Steps" | "We believe in user-first design (philosophy). Click the Settings button (tactic)." |
| **W6: Simple Active Voice**<br>Write in simple terms in the active voice | The Stem orchestrates all agent systems. | All agent systems are orchestrated by the Stem. |
| **W7: No hyperbolic language**<br>Avoid promotional superlatives | The system improves retrieval accuracy. The results suggest improved performance. | The system delivers revolutionary, game-changing retrieval capabilities. The results clearly demonstrate obvious improvements. |
| **W8: No rhetorical questions**<br>Make direct statements instead | Memory consolidation is essential for long-term retention. | But why is memory consolidation so important? Because it enables long-term retention. |
| **W9: No exclamation marks in analytical text**<br>Reserve for genuine alerts only | This constraint significantly impacts performance. | This constraint significantly impacts performance! |

### 1.2 Structure

Structure standards govern document organisation and hierarchy.

| Requirement | Good | Bad |
|-------------|------|-----|
| **S1: Title format**<br>Use `# [Document Title] v[X]-[YY]` as the first line | `# Memory System Design v3-15` | |
| **S2: Metadata header**<br>Include ONLY Version, Date, Type immediately after title | `**Version**: v3-15` / `**Date**: 12 December 2025` / `**Type**: Design Specification` | Adding `**Author**:`, `**Status**:`, `**Purpose**:` or other fields |
| **S3: Section hierarchy**<br>Use `##` for L1 headings, `###` for L2 headings, **bold** for L3 headings; never use `####` | `## 1. Overview` → `### 1.1 Purpose` → **Key concepts** | `## 1. Overview` → `### 1.1 Purpose` → `#### 1.1.1 Key concepts` |
| **S4: Section count**<br>There should be at least two sections at each level, or none at all. | Document has three sections 1, 2 & 3<br>Section 1, has three subsections 1.1, 1.2 and 1.3 | Document has only one section numbered 1<br>Section 1, has one only subsection 1.1  |
| **S5: Introductory text**<br>Every L1 section (`##`) or L2 section must have prose before any L2 subsections (`###`) or L3 subsections | `## 2. Architecture` followed by introductory paragraph, then `### 2.1 Components` | `## 2. Architecture` followed immediately by `### 2.1 Components` |
| **S6: Section separators**<br>Use exactly five hyphens (`-----`) between major sections | `-----` | `---` or `----------` or `*****` |

### 1.3 Markdown

Markdown standards govern technical formatting.

| Requirement | Good | Bad |
|-------------|------|-----|
| **M1: Code blocks specify language**<br>Always declare the language after opening backticks | ` ```python ` | ` ``` ` |
| **M2: JSON formatting**<br>Use 2-space indentation and double quotes | `{ "key": "value" }` with 2-space indent | `{ 'key': 'value' }` or 4-space indent |
| **M3: Lists require blank lines**<br>Add blank line before and after every list | Paragraph, blank line, list, blank line, paragraph | Paragraph immediately followed by list item |
| **M4: List markers**<br>Use `-` for unordered lists, `1.` for ordered lists | `- First item` or `1. First step` | `* First item` or `a. First step` |
| **M5: UTF-8 encoding without BOM**<br>Save files as UTF-8 with no byte order mark | Clean UTF-8 file | File beginning with BOM bytes (EF BB BF) |
| **M6: No garbled characters**<br>Ensure no encoding corruption in text | "quotes" and —dashes | â€œquotesâ€ and â€"dashes |
| **M7: ASCII-safe punctuation**<br>Use standard characters for quotes, dashes, bullets | Straight quotes `"`, standard dash `-` or `--` | Curly quotes `""`, em-dash `—` unless intentional |

### 1.4 Version Control

Version control standards govern change tracking and documentation.

| Requirement | Good | Bad |
|-------------|------|-----|
| **V1: Version increment**<br>Increment version for any content or structure change | Major change v1-02 → v2-00. Adding a paragraph → v1-02 to v1-03. | Making changes without incrementing version |
| **V2: Version format**<br>Use v[Major]-[Minor] with Minor as two digits | v1-00, v2-03, v3-15 | v1.0, v2.3, version 3.15 |
| **V3: Date update**<br>Update date to current date when version changes | Date matches the day the version was created | Date unchanged from previous version |
| **V4: Document changes**<br>Explicitly list all additions, deletions, and modifications | "Added: Section 4.2. Deleted: Appendix B. Modified: Conclusion." | "Made some updates" or "Various edits" |

-----

## 2. Verification

We verify a document after every update. The verification allows us to understand what has changed in the document and identify gaps between the document and the document standards.

```markdown
## Verification: [Document Name] v[X]-[YY]

**Date:** [DD Month YYYY]

### Changes

**Added:**
- [List each addition]

**Deleted:**
- [List each deletion]

**Modified:**
- [List each modification]

### Requirements

| Requirement | Status | Comments |
|-------------|--------|----------|
| **Writing** | | |
| W1. British English | ✅ ⚠️ ❌ | |
| W2. Write in positives | ✅ ⚠️ ❌ | |
| W3. No label formatting | ✅ ⚠️ ❌ | |
| W4. Format matches function | ✅ ⚠️ ❌ | |
| W5. Altitude discipline | ✅ ⚠️ ❌ | |
| W6. Simple active voice | ✅ ⚠️ ❌ | |
| W7. No hyperbolic language | ✅ ⚠️ ❌ | |
| W8. No rhetorical questions | ✅ ⚠️ ❌ | |
| W9. No exclamation marks | ✅ ⚠️ ❌ | |
| **Writing (W1-W9)** | ✅ ⚠️ ❌ | |
| | | |
| **Structure** | | |
| S1. Title format | ✅ ⚠️ ❌ | |
| S2. Metadata header | ✅ ⚠️ ❌ | |
| S3. Section hierarchy | ✅ ⚠️ ❌ | |
| S4. Section count | ✅ ⚠️ ❌ | |
| S5. Introductory text | ✅ ⚠️ ❌ | |
| S6. Section separators | ✅ ⚠️ ❌ | |
| **Structure (S1-S5)** | ✅ ⚠️ ❌ | |
| | | |
| **Markdown** | | |
| M1. Code blocks specify language | ✅ ⚠️ ❌ | |
| M2. JSON formatting | ✅ ⚠️ ❌ | |
| M3. Lists require blank lines | ✅ ⚠️ ❌ | |
| M4. List markers | ✅ ⚠️ ❌ | |
| M5. UTF-8 without BOM | ✅ ⚠️ ❌ | |
| M6. No garbled characters | ✅ ⚠️ ❌ | |
| M7. ASCII-safe punctuation | ✅ ⚠️ ❌ | |
| **Markdown (M1-M7)** | ✅ ⚠️ ❌ | |
| | | |
| **Version Control** | | |
| V1. Version increment | ✅ ⚠️ ❌ | |
| V2. Version format | ✅ ⚠️ ❌ | |
| V3. Date update | ✅ ⚠️ ❌ | |
| V4. Document changes | ✅ ⚠️ ❌ | |
| **Version Control (V1-V4)** | ✅ ⚠️ ❌ | |
| | | |
| **Overall** | ✅ ⚠️ ❌ | |

### Issues

[List issues and resolution. Verification incomplete until resolved.]
```

-----

*End of document*