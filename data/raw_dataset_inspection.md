# 🏈 Big Data Bowl 2026: Dataset Inspection & Engineering Handbook

**Project:** The Void Engine (Zone Coverage Auditing)
**Domain:** NFL Player Tracking Data (Post-Snap/Post-Throw)
**Status:** VALIDATED (with documented constraints)

---

## 1. File Topology & Data Flow

The dataset is split into **Tracking Data** (Time-series) and **Context Data** (Play-level metadata).

### Directory Structure
* **`data/train/`**: Contains the raw tracking data.
    * `input_w[01-09].csv`: **Pre-throw** tracking data (frames leading up to the pass).
    * `output_w[01-09].csv`: **Post-throw** tracking data (frames where the ball is in the air).
    * *Note: Files are paired by Week. Week 1 Input matches Week 1 Output.*
* **`data/supplementary_data.csv`**: The "Rosetta Stone." Contains play-level labels (Coverages, EPA, Penalties).

### The "Stitch" & Time Sparsity
* **Temporal Ratio:** `Input` files are ~2.9x longer than `Output` files.
* **Frame Zeroing:** `input_*.csv` frames end at $N$. The first frame of `output_*.csv` is $1$. The pipeline offsets the output frames by $N$ to create a continuous timeline $1 \to N \to End$.

---

## 2. The "Ghost" Constraint (Attrition Analysis)

**Critical Finding:** The dataset is **Lossy**. Players present in the `Input` file (pre-throw) frequently disappear in the `Output` file (post-throw).

### The Survival Rules (Empirically Proven)
1.  **Targeted Receivers:** 100% Survival Rate. They never disappear.
2.  **Proximity Filter:** The dataset aggressively drops players far from the ball.
    * *Survivors* (Kept in data): Avg distance to landing spot = **8.4 yards**.
    * *Ghosts* (Dropped from data): Avg distance to landing spot = **19.8 yards**.
3.  **The "Danger Zone" (8-15 yards):**
    * There is a transition zone (8-15 yards from catch) where players *may* disappear.
    * *Implication:* If a defender is ~12 yards away from the catch, they might not be graded by the Void Engine because they do not exist in the dataframe.

**Engineering Decision:** The Void Engine treats "Ghosts" as **Exempt**. We assume if the NFL tracking system deemed them irrelevant enough to drop, they were not the primary cause of the defensive breakdown.

---

## 3. Coordinate System & Physics

**Warning:** Raw NFL data is non-standardized regarding direction. This pipeline enforces a **Left-to-Right** normalization.

### Normalization Logic
If `play_direction == 'left'`, the engine flips the geometry so the offense always drives from Left ($X=0$) to Right ($X=120$).

* **X-Axis:** $X_{new} = 120 - X_{raw}$
* **Y-Axis:** $Y_{new} = 53.3 - Y_{raw}$
* **Orientation/Dir:** $\theta_{new} = (\theta_{raw} + 180) \mod 360$

### Derived Geometry
* **Line of Scrimmage (LOS):** Calculated as `ball_land_x - pass_length`.
* **Depth:** $X_{player} - X_{LOS}$.
* **Compression Factor:** Used for "Red Zone Squash."
    $$\text{Compression} = \text{clip}\left(\frac{110 - \text{LOS}}{20}, 0.5, 1.0\right)$$