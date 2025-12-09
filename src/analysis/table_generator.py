import pandas as pd
import numpy as np

class TableGenerator:
    def __init__(self, summary_path: str):
        self.df = pd.read_csv(summary_path)
        
        # Standardize Role Filtering (Focus on coverage players)
        # We exclude Pass Rushers who occasionally drop into coverage
        self.df = self.df[self.df['player_role'].isin([
            'Defensive Coverage', 'Cornerback', 'Safety', 'Linebacker'])]

    def generate_quadrant_counts(self):
        """
        TABLE 2: Quadrant Counts Table
        Buckets plays into the 4 Matrix Outcomes.
        """
        df = self.df.copy()

        # Define Thresholds
        # OPEN: > 3 yards at throw (A bit tighter than "High Void" to capture more data)
        # CLOSED: < 1.5 yards at arrival
        
        OPEN_THRESH = 3.0
        CLOSED_THRESH = 1.5

        conditions = [
            (df['dist_at_throw'] >= OPEN_THRESH) & (df['dist_at_arrival'] <= CLOSED_THRESH), # Open -> Closed
            (df['dist_at_throw'] < OPEN_THRESH) & (df['dist_at_arrival'] <= CLOSED_THRESH),  # Tight -> Closed
            (df['dist_at_throw'] < OPEN_THRESH) & (df['dist_at_arrival'] > CLOSED_THRESH),  # Tight -> Open
            (df['dist_at_throw'] >= OPEN_THRESH) & (df['dist_at_arrival'] > CLOSED_THRESH)  # Open -> Open
        ]
        
        choices = ['Eraser (The Cleanup)', 'Lockdown (The Blanket)', 'Lost Step (The Beat)', 'Liability (The Void)']
        
        df['quadrant'] = np.select(conditions, choices, default='Neutral/Zone Drift')

        # Aggregation
        summary = df.groupby('quadrant').agg(
            play_count=('play_id', 'count'),
            avg_vis=('vis_score', 'mean'),
            avg_ceoe=('ceoe_score', 'mean')
        ).reset_index()

        summary['avg_vis'] = summary['avg_vis'].round(2)
        summary['avg_ceoe'] = summary['avg_ceoe'].round(3)

        return summary.sort_values('avg_vis', ascending=False)

    def generate_shrunk_leaderboard(self, min_snaps=15, prior_m=20):
        """
        TASK 2: Bayesian Shrinkage with Names.
        """
        # 1. Positional Priors
        pos_stats = self.df.groupby('player_position')['ceoe_score'].mean().to_dict()

        # 2. Add player_name to grouping
        group_cols = ['nfl_id', 'player_position', 'player_role']
        if 'player_name' in self.df.columns:
            group_cols.insert(1, 'player_name')

        player_stats = self.df.groupby(group_cols).agg(
            snaps=('play_id', 'count'),
            raw_ceoe=('ceoe_score', 'mean'),
            avg_vis=('vis_score', 'mean'),
            avg_start=('p_dist_at_throw', 'mean')
        ).reset_index()

        # 3. Shrinkage
        def apply_shrinkage(row):
            prior_mu = pos_stats.get(row['player_position'], 0.0)
            n = row['snaps']
            m = prior_m
            shrunk = ((n * row['raw_ceoe']) + (m * prior_mu)) / (n + m)
            return shrunk

        player_stats['shrunk_ceoe'] = player_stats.apply(apply_shrinkage, axis=1)

        # 4. Filter & Sort
        qualified = player_stats[player_stats['snaps'] >= min_snaps].copy()
        
        qualified['shrunk_ceoe'] = qualified['shrunk_ceoe'].round(3)
        qualified['raw_ceoe'] = qualified['raw_ceoe'].round(3)
        qualified['avg_vis'] = qualified['avg_vis'].round(2)
        qualified['avg_start'] = qualified['avg_start'].round(1)

        top_erasers = qualified.sort_values('shrunk_ceoe', ascending=False).head(10)
        
        return top_erasers

    def generate_damage_control_validation(self):
        """
        TASK 3: Damage Control Validation (YAC & EPA).
        Hypothesis: On COMPLETED passes, higher VIS (better closing) 
        should correlate with LOWER YAC and LOWER EPA (better for defense).
        """
        df = self.df.copy()
        
        # 1. Filter for Completions Only (Where YAC exists)
        completed = df[df['pass_result'] == 'C'].copy()
        
        if completed.empty:
            return "No completions found in dataset."

        # 2. Derive YAC
        # YAC = Total Yards - Air Yards
        completed['yac'] = completed['yards_gained'] - completed['pass_length']
        
        # 3. Bin Start Distance (Context Control)
        # We only care about Medium/High Voids where YAC is a threat.
        bins = [3, 6, 10, 100]
        labels = ['Medium (3-6)', 'High Void (6-10)', 'Deep (10+)']
        completed['start_band'] = pd.cut(completed['p_dist_at_throw'], bins=bins, labels=labels)
        
        # 4. Bin VIS Score (The Independent Variable)
        # Low Effort vs. High Effort closing
        vis_bins = [-np.inf, 0, 3, np.inf]
        vis_labels = ['Negative (Lost Gap)', 'Moderate (0-3)', 'High Erasure (3+)']
        completed['vis_bucket'] = pd.cut(completed['vis_score'], bins=vis_bins, labels=vis_labels)

        # 5. Aggregate
        damage_control = completed.groupby(['start_band', 'vis_bucket'], observed=False).agg(
            count=('play_id', 'count'),
            avg_yac=('yac', 'mean'),
            avg_epa=('expected_points_added', 'mean') # Lower is better for defense
        ).reset_index()

        # 6. Pivot for YAC (The Primary Proof)
        yac_pivot = damage_control.pivot(index='start_band', columns='vis_bucket', values='avg_yac')
        
        # Calculate the "Savings" (Difference between Negative VIS and High Erasure)
        yac_pivot['YAC_Savings'] = yac_pivot['Negative (Lost Gap)'] - yac_pivot['High Erasure (3+)']
        
        return yac_pivot.round(2)

    def generate_epa_savings(self):
        """
        TABLE 5: EPA Savings Table (Quartile Approach).
        Shows how much Expected Points high-effort defenders save vs low-effort defenders.
        Uses within-band quartiles to avoid structural NaNs.
        Focuses on COMPLETED passes where EPA damage occurs.
        """
        df = self.df.copy()
        
        # 1. Filter for Completions Only (where EPA damage occurs)
        completed = df[df['pass_result'] == 'C'].copy()
        
        if completed.empty:
            return "No completions found in dataset."
        
        # 2. Create Start Distance bands
        dist_bins = [0, 3, 6, 10, 100]
        dist_labels = ['Tight (0-3)', 'Medium (3-6)', 'High Void (6-10)', 'Exempt (10+)']
        completed['start_band'] = pd.cut(completed['p_dist_at_throw'], bins=dist_bins, labels=dist_labels)
        
        # 3. Calculate VIS quartiles WITHIN each start band
        # This avoids NaNs by making "effort" relative to what's possible from each start position
        def get_quartile_label(group):
            q25 = group['vis_score'].quantile(0.25)
            q75 = group['vis_score'].quantile(0.75)
            
            conditions = [
                group['vis_score'] <= q25,
                group['vis_score'] >= q75
            ]
            choices = ['Low Effort (Q1)', 'High Effort (Q4)']
            group['effort_bucket'] = np.select(conditions, choices, default='Middle (Q2-Q3)')
            return group
        
        completed = completed.groupby('start_band', group_keys=False, observed=False).apply(get_quartile_label)
        
        # 4. Filter to only Q1 and Q4 for clean comparison
        extremes = completed[completed['effort_bucket'].isin(['Low Effort (Q1)', 'High Effort (Q4)'])]
        
        # 5. Aggregate EPA by Start Band and Effort Bucket
        epa_table = extremes.groupby(['start_band', 'effort_bucket'], observed=False).agg(
            play_count=('play_id', 'count'),
            avg_epa=('expected_points_added', 'mean')
        ).reset_index()
        
        # 6. Pivot for clear comparison
        epa_pivot = epa_table.pivot(index='start_band', columns='effort_bucket', values='avg_epa')
        
        # 7. Calculate EPA Saved (Low Effort EPA - High Effort EPA)
        # Positive = High effort defenders saved points
        if 'Low Effort (Q1)' in epa_pivot.columns and 'High Effort (Q4)' in epa_pivot.columns:
            epa_pivot['EPA_Saved'] = epa_pivot['Low Effort (Q1)'] - epa_pivot['High Effort (Q4)']
        
        # 8. Add play counts for context
        count_pivot = epa_table.pivot(index='start_band', columns='effort_bucket', values='play_count')
        epa_pivot['Plays_Compared'] = count_pivot.sum(axis=1)
        
        # Reorder columns for clarity
        col_order = ['Low Effort (Q1)', 'High Effort (Q4)', 'EPA_Saved', 'Plays_Compared']
        epa_pivot = epa_pivot[[c for c in col_order if c in epa_pivot.columns]]
        
        return epa_pivot.round(3)

    def generate_position_breakdown(self):
        """
        TABLE 6: Position Breakdown - "Who Should Erase?"
        Shows which position groups are best suited for the Eraser role.
        Uses RAW metrics (not shrunk) for position-level comparisons.
        """
        df = self.df.copy()
        
        # 1. Define Eraser criteria (derived from start/end distances, not void_type)
        # Eraser = Started in High Void (>6yds) AND closed to tight (<2yds)
        OPEN_THRESH = 6.0
        CLOSED_THRESH = 2.0
        df['is_eraser_play'] = (df['p_dist_at_throw'] >= OPEN_THRESH) & (df['dist_at_arrival'] <= CLOSED_THRESH)
        
        # 2. Group by player position
        position_stats = df.groupby('player_position').agg(
            play_count=('play_id', 'count'),
            avg_start_dist=('p_dist_at_throw', 'mean'),
            avg_end_dist=('dist_at_arrival', 'mean'),
            avg_vis=('vis_score', 'mean'),
            eraser_plays=('is_eraser_play', 'sum')
        ).reset_index()
        
        # 3. Calculate Eraser Rate (% of plays where they achieved Eraser outcome)
        position_stats['eraser_rate'] = (position_stats['eraser_plays'] / position_stats['play_count'] * 100).round(1)
        
        # 4. Filter for positions with meaningful sample size
        position_stats = position_stats[position_stats['play_count'] >= 50].copy()
        
        # 5. Derive Erasure Archetype based on behavior patterns
        def assign_archetype(row):
            avg_start = row['avg_start_dist']
            avg_vis = row['avg_vis']
            eraser_rate = row['eraser_rate']
            
            # Primary Eraser: Deep starters who close aggressively
            if avg_start >= 8 and avg_vis >= 1.5:
                return "🟢 Primary Eraser"
            # Secondary Eraser: Medium depth with good closing
            elif avg_start >= 6 and avg_vis >= 1.0:
                return "🔵 Secondary Eraser"
            # Lockdown: Tight coverage specialists (low start = already close)
            elif avg_start < 5 and avg_vis < 0.5:
                return "🟡 Lockdown Focus"
            # Situational: High eraser rate despite moderate metrics
            elif eraser_rate >= 5:
                return "🟠 Situational Eraser"
            else:
                return "⚪ Zone Support"
        
        position_stats['archetype'] = position_stats.apply(assign_archetype, axis=1)
        
        # 6. Format output columns
        position_stats['avg_start_dist'] = position_stats['avg_start_dist'].round(1)
        position_stats['avg_end_dist'] = position_stats['avg_end_dist'].round(1)
        position_stats['avg_vis'] = position_stats['avg_vis'].round(2)
        
        # 7. Select and order columns for output
        # Note: Dropping raw_ceoe as it regresses toward positional means (~0) and confuses readers
        # VIS and archetype provide clearer differentiation
        output_cols = ['player_position', 'play_count', 'avg_start_dist', 'avg_end_dist',
                       'avg_vis', 'eraser_rate', 'archetype']
        
        # Sort by avg_start_dist descending (deep players first = primary erasers)
        return position_stats[output_cols].sort_values('avg_start_dist', ascending=False)
    
if __name__ == "__main__":
    SUMMARY_FILE = "data/processed/eraser_analysis_summary.csv"
    
    gen = TableGenerator(SUMMARY_FILE)
    
    print("\n--- SHRUNK LEADERBOARD (Bayesian m=20) ---")
    print(gen.generate_shrunk_leaderboard().to_string(index=False))
    
    print("\n--- QUADRANT SUMMARY ---")
    print(gen.generate_quadrant_counts().to_string(index=False))

    print("\n--- DAMAGE CONTROL VALIDATION (YAC) ---")
    print(gen.generate_damage_control_validation())

    print("\n--- EPA SAVINGS TABLE ---")
    print(gen.generate_epa_savings())
    
    print("\n--- POSITION BREAKDOWN (Who Should Erase?) ---")
    print(gen.generate_position_breakdown().to_string(index=False))