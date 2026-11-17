# Tableau Public dashboard

## Quick version (about 1 hour), start here

The margins of error and the "3.5% that wasn't" chart are already in the README as images. The dashboard only needs the interactive part.

**1. Connect (5 min).** Open Tableau Public, then Text file → `households_2023.csv`.

**2. Create one parameter (2 min).** `Threshold`: Float, range 0.25 to 0.50, step 0.05, current value 0.30, displayed as a percentage. Right-click it → Show Parameter.

**3. Paste four calculated fields (10 min):**
```
// Burdened at Threshold
IF [Housing Cost Share of Income] > [Threshold] THEN 1 ELSE 0 END

// Burden Rate
SUM([Weight] * [Burdened at Threshold]) / SUM([Weight])

// Households Burdened (M)
SUM([Weight] * [Burdened at Threshold]) / 4 / 1000000

// Housing Share of Spending
SUM([Weight] * [Spend: Housing]) / SUM([Weight] * [Spending incl. Principal (Annualized)])
```
Format `Burden Rate` and `Housing Share of Spending` as percentages with 0 decimals.

**4. Build three sheets (25 min):**
- **Headline:** drag `Burden Rate` and `Households Burdened (M)` to Text. Title: `Households spending more than <Parameters.Threshold> of income on housing`.
- **Who:** Rows `Income Group`, Columns `Burden Rate`, Mark Bar, show labels. Sort the rows manually from Lowest 20% to Highest 20%. Duplicate the sheet twice and swap in `Housing` and `Earners`, or just keep Income.
- **Money:** first right-click `Severely Burdened (>50%)` → Convert to Dimension. Rows `Renter or Owner` and `Severely Burdened (>50%)`, Columns `Housing Share of Spending`, Mark Bar, labels on.

**5. Dashboard (15 min).** Headline across the top, the slider next to it, Who on the left, Money on the right. Add a `Renter or Owner` filter and apply it to all sheets using this data source. Add a text box: "Source: BLS Consumer Expenditure Survey 2023 · code: github.com/nic-stack/household-financial-strain-2023".

**6. Check, then publish (5 min).** At 30% the headline must read **32%** and 42.2 million. At 50% it must read **15%**. Renters filtered: **54%**. Then File → Save to Tableau Public and send me the link.

The full plan below adds a breakdown dropdown, the margins-of-error chart and more polish, if you want them later.

---

# Full plan

**Goal:** one interactive dashboard that lets a non-technical reader answer "Who is housing-cost burdened, and how much does the definition matter?" It closes the project end to end: raw BLS files → SQL → tested results → dashboard.

**Audience:** a city housing office or a nonprofit program manager. They want plain answers, not methods.

**Time:** about 3–4 hours in Tableau Public (free desktop app).

---

## 1. Data (all files are in this folder, produced by `sql/05_tableau_extract.sql`)

| File | Rows | Used for |
|---|---|---|
| `households_2023.csv` | 18,510 (one per renter/owner interview) | Interactive charts and filters |
| `estimates_with_ci.csv` | 50 | The chart with 95% intervals (Tableau can't compute replicate-weight errors itself) |
| `team_reconciliation.csv` | 6 | The "3.5% that wasn't" chart |

Connect each as a **separate data source**. Don't join them.

> Every rate must be **weighted**. Never use a plain count or `AVG([Burdened])`. Each row stands for a different number of U.S. households, which is what the `Weight` column holds.

## 2. Parameters

| Name | Type | Values | Default |
|---|---|---|---|
| `Threshold` | Float, range | 0.25 to 0.50, step 0.05, displayed as a percentage | 0.30 |
| `Breakdown` | String, list | Income, Age, Housing, Earners, Household type, Region | Income |

Right-click each parameter and choose **Show Parameter**.

## 3. Calculated fields (in `households_2023`)

```
// Burdened at Threshold
IF [Housing Cost Share of Income] > [Threshold] THEN 1 ELSE 0 END

// Burden Rate
SUM([Weight] * [Burdened at Threshold]) / SUM([Weight])

// Households Burdened (M)
SUM([Weight] * [Burdened at Threshold]) / 4 / 1000000
// (divide by 4: the four quarterly files are pooled)

// Interviews
COUNT([Interview ID])

// Sample Note
IF COUNT([Interview ID]) < 100 THEN "Small sample: treat with caution" ELSE "" END

// Breakdown Group
CASE [Breakdown]
  WHEN "Income" THEN [Income Group]
  WHEN "Age" THEN [Age Group]
  WHEN "Housing" THEN [Housing]
  WHEN "Earners" THEN [Earners]
  WHEN "Household type" THEN [Household Type]
  WHEN "Region" THEN IIF([Region] = "Not stated", NULL, [Region])   // BLS suppresses region for ~2%
END

// Group Order   (keeps groups in a sensible order when the Breakdown changes)
CASE [Breakdown Group]
  WHEN "Lowest 20%" THEN 1 WHEN "Second 20%" THEN 2 WHEN "Middle 20%" THEN 3
  WHEN "Fourth 20%" THEN 4 WHEN "Highest 20%" THEN 5
  WHEN "Under 35" THEN 1 WHEN "35-44" THEN 2 WHEN "45-54" THEN 3
  WHEN "55-64" THEN 4 WHEN "65-74" THEN 5 WHEN "75+" THEN 6
  WHEN "Renter" THEN 1 WHEN "Owner with mortgage" THEN 2 WHEN "Owner, no mortgage" THEN 3
  WHEN "No earners" THEN 1 WHEN "One earner" THEN 2 WHEN "Two or more" THEN 3
  WHEN "Living alone" THEN 1 WHEN "Adults only" THEN 2 WHEN "With children" THEN 3
  ELSE 9
END

// Spending Group
IF [Severely Burdened (>50%)] = 1 THEN "Severely burdened " + LOWER([Renter or Owner]) + "s"
ELSE "Other " + LOWER([Renter or Owner]) + "s" END

// Housing Share of Spending   (repeat for Food, Transport, Healthcare)
SUM([Weight] * [Spend: Housing]) / SUM([Weight] * [Spending incl. Principal (Annualized)])

// Overall Rate   (table calculation: the rate for everything currently on the sheet,
//                 so it follows the filters)
WINDOW_SUM(SUM([Weight] * [Burdened at Threshold])) / WINDOW_SUM(SUM([Weight]))

// Above Overall Rate
[Burden Rate] > [Overall Rate]
```

In `estimates_with_ci`:
```
// Interval Width
[Rate 95% High] - [Rate 95% Low]
```

## 4. Sheets

**Sheet 1, KPI tiles** (3 small sheets, or 1 sheet with Measure Names):
- Text: `Burden Rate` (as a percentage, 0 decimals) and `Households Burdened (M)`.
- These follow the `Threshold` slider, which is how the reader sees that the rate moves from 41% at 25% to 15% at 50%.
- Title: `Households spending more than <Parameters.Threshold> of income on housing`. Insert the parameter so the title changes with the slider.
- Add a second tile filtered to `Renter or Owner = Renter`.

**Sheet 2, Who is burdened** (the main chart):
- Rows: `Breakdown Group`, sorted by `Group Order` (Sort → Field → Group Order, Minimum). Filter out Null.
- Columns: `Burden Rate`. Mark: Bar. Label: `Burden Rate`.
- Drag `Overall Rate` to Detail. Color: `Above Overall Rate`, with the terracotta `#C2593F` for True and the grey `#7B8794` for False.
- Reference line: Analytics → Reference Line → Value: `Overall Rate` (Average), labelled "All households".
  Don't use "Average" of `Burden Rate`: that averages the group rates, which isn't the national rate.
- Tooltip: `<Breakdown Group>: <Burden Rate> burdened, about <Households Burdened (M)> million households. Based on <Interviews> interviews. <Sample Note>`

**Sheet 3, With margins of error** (`estimates_with_ci`):
- Filters: `Measure` = Burdened (>30% of income); `Breakdown` = Income, Housing, Earners, Household type.
- Rows: `Breakdown`, `Group` (sort `Group` by `Sort`, Minimum).
- Columns: `Rate 95% Low` with Mark = Gantt Bar, Size = `Interval Width`. Add `Rate` as a second axis with Mark = Circle. Dual axis, then Synchronize Axis.
- Caption: "Bars show the 95% interval from the survey's 44 replicate weights. These are fixed at the 30% threshold."

**Sheet 4, Where the money goes:**
- Rows: `Spending Group`. Columns: Measure Values = the four share fields. Mark: stacked bar.
- Colors: Housing `#C2593F`, Food `#E8B4A6`, Transport `#7B8794`, Healthcare `#E4E7EB`.

**Sheet 5, The 3.5% that wasn't** (`team_reconciliation`):
- Columns: `Change` (sort by `Step`). Rows: `Share Flagged`. Mark: bar with labels.
- Caption: "The original capstone's 3.5% came from two data errors. Fixed, the same rule flags 41%, too broad to be useful, so this project uses the HUD standard."

## 5. Dashboard layout (fixed size 1200 × 1000)

```
+--------------------------------------------------------------------+
| Who Can Afford Their Home? U.S. Housing Cost Burden, 2023          |
| One line: what this is, data source, how to use the controls       |
+----------------+----------------+-----------------+----------------+
| KPI: all       | KPI: renters   | KPI: households | Threshold      |
| households     |                | (millions)      | slider         |
+----------------+----------------+-----------------+----------------+
| Breakdown dropdown   |  Filters: Renter or Owner, Region, Age      |
+----------------------+---------------------------------------------+
| Sheet 2: Who is burdened (large)  | Sheet 4: Where the money goes  |
|                                   |                                |
+-----------------------------------+--------------------------------+
| Sheet 3: With margins of error    | Sheet 5: The 3.5% that wasn't  |
+-----------------------------------+--------------------------------+
| Source: BLS Consumer Expenditure Survey 2023 · Code: GitHub link   |
+--------------------------------------------------------------------+
```

- Apply the `Renter or Owner`, `Region` and `Age Group` filters to all sheets that use `households_2023` (Apply to Worksheets → All Using This Data Source).
- Optional dashboard action: clicking a bar in Sheet 2 filters Sheet 4.
- Fonts: Tableau Book for text, Tableau Semibold for titles. A white background with plenty of space.

## 6. Check before publishing

With `Threshold` = 30% and no filters, these must match the tested SQL results:

| What | Expected |
|---|---|
| All households burdened | **32.1%** (42.2 million) |
| Renters burdened | **53.5%** |
| Owners burdened | **21.3%** |
| Lowest 20% income | **60.65%** (shows as 61% with 0 decimals) |
| Threshold 50%: all households | **15.5%** |
| Threshold 25% / 40% | **40.8% / 21.3%** |
| Severely burdened renters: housing share of spending | **44.4%** |
| Other renters: housing share | **29.3%** |

If a number is off, the usual cause is an unweighted calculation or a filter left on.

## 7. Publish
1. File → Save to Tableau Public As… → `US Housing Cost Burden 2023`.
2. In the Tableau Public profile, add a description and the GitHub link.
3. Send me the link and I'll add it to the README and the case study.

## What to say about it in an interview
- **Why weights:** "Each interview represents a different number of households, so every rate is a weighted sum. An unweighted average would over-represent some groups."
- **Why the intervals come from SQL:** "The survey gives 44 replicate weights for margins of error. Tableau can't do that calculation, so I computed the intervals in SQL and brought them in as a separate table."
- **Why the threshold slider:** "The 30% line is a convention. The slider shows how sensitive the answer is to it, and that the same groups stand out at every threshold."
