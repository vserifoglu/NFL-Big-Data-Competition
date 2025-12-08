import pandas as pd
import numpy as np

class TableGenerator:
    def __init__(self, summary_path: str):
        self.df = pd.read_csv(summary_path)
        
        # Standardize Role Filtering (Focus on coverage players)
        # We exclude Pass Rushers who occasionally drop into coverage
        self.df = self.df[self.df['player_role'].isin([
            'Defensive Coverage', 'Cornerback', 'Safety', 'Linebacker'])]

    def generate_leaderboard(self, min_snaps=15):
        """
        TABLE 1: Player/Team Eraser Table
        Top and Bottom defenders by CEOE.
        """

        # Aggregation
        leaderboard = self.df.groupby(['nfl_id', 'player_position']).agg(
            snaps=('play_id', 'count'),
            avg_ceoe=('ceoe_score', 'mean'),
            avg_vis=('vis_score', 'mean'),
            avg_start_dist=('p_dist_at_throw', 'mean') 
        ).reset_index()

        # Filter for Significance (The Law of Large Numbers)
        qualified = leaderboard[leaderboard['snaps'] >= min_snaps].copy()

        # Formatting
        qualified['avg_ceoe'] = qualified['avg_ceoe'].round(3)
        qualified['avg_vis'] = qualified['avg_vis'].round(2)
        qualified['avg_start_dist'] = qualified['avg_start_dist'].round(1)

        # Sort
        top_erasers = qualified.sort_values('avg_ceoe', ascending=False).head(10)
        bottom_erasers = qualified.sort_values('avg_ceoe', ascending=True).head(10)

        return top_erasers, bottom_erasers

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

    def generate_situational_summary(self):
        """
        TABLE 3: Situation Summary Table (Context Check)
        Shows how the metric behaves across Coverage Types and Downs.
        """
        # Grouping
        # We fill NA coverage types just in case
        df = self.df.copy()
        df['team_coverage_type'] = df['team_coverage_type'].fillna('Unknown')

        situation = df.groupby(['team_coverage_type', 'down']).agg(
            snaps=('play_id', 'count'),
            avg_s_throw=('p_dist_at_throw', 'mean'), 
            avg_s_arrival=('dist_at_arrival', 'mean'),
            avg_vis=('vis_score', 'mean')
        ).reset_index()

        # Filter out rare situations (e.g., prevent "Cover 0 on 4th down" with 1 play from skewing data)
        situation = situation[situation['snaps'] > 5]

        # Rounding
        cols = ['avg_s_throw', 'avg_s_arrival', 'avg_vis']
        situation[cols] = situation[cols].round(2)

        return situation

    def generate_shrunk_leaderboard(self, min_snaps=15, prior_m=20):
        """
        TASK 2: Bayesian Shrinkage.
        Shrinks raw CEOE towards the POSITIONAL mean (not global mean).
        Formula: (n * raw + m * pos_avg) / (n + m)
        """
        # 1. Calculate Positional Priors (The Baseline)
        # e.g., Average CEOE for all CBs might be 0.5, for LBs might be -0.2
        pos_stats = self.df.groupby('player_position')['ceoe_score'].mean().to_dict()

        # 2. Aggregate Player Stats
        # We group by ID and Position
        player_stats = self.df.groupby(['nfl_id', 'player_position', 'player_role']).agg(
            snaps=('play_id', 'count'),
            raw_ceoe=('ceoe_score', 'mean'),
            avg_vis=('vis_score', 'mean'),
            avg_start=('p_dist_at_throw', 'mean')
        ).reset_index()

        # 3. Apply Shrinkage Function
        def apply_shrinkage(row):
            # Get the prior for this specific position (default to 0 if unknown)
            prior_mu = pos_stats.get(row['player_position'], 0.0)
            
            n = row['snaps']
            m = prior_m
            
            # The Bayesian Average
            shrunk = ((n * row['raw_ceoe']) + (m * prior_mu)) / (n + m)
            return shrunk

        player_stats['shrunk_ceoe'] = player_stats.apply(apply_shrinkage, axis=1)

        # 4. Filter & Sort
        qualified = player_stats[player_stats['snaps'] >= min_snaps].copy()
        
        # Rounding for display
        qualified['shrunk_ceoe'] = qualified['shrunk_ceoe'].round(3)
        qualified['raw_ceoe'] = qualified['raw_ceoe'].round(3)
        qualified['avg_vis'] = qualified['avg_vis'].round(2)
        qualified['avg_start'] = qualified['avg_start'].round(1)

        # Sort by the new robust metric
        top_erasers = qualified.sort_values('shrunk_ceoe', ascending=False).head(10)
        
        return top_erasers

    def generate_outcome_alignment(self):
        """
        TASK 1: Outcome Alignment Test within Bands.
        Hypothesis: Within the same distance band, higher VIS = more Incompletions.
        """
        df = self.df.copy()
        
        # 1. Binning Logic (S_throw)
        bins = [0, 3, 6, 10, 100]
        labels = ['Tight (0-3)', 'Medium (3-6)', 'High Void (6-10)', 'Deep (10+)']
        df['start_band'] = pd.cut(df['p_dist_at_throw'], bins=bins, labels=labels)

        # 2. Define Outcome (Binary)
        # We treat Interceptions (IN) as Incomplete (Prevented Catch)
        valid_outcomes = ['C', 'I', 'IN']
        df = df[df['pass_result'].isin(valid_outcomes)]
        
        df['outcome_type'] = np.where(df['pass_result'] == 'C', 'Allowed Catch', 'Prevented Catch')

        # 3. Aggregate VIS by Band + Outcome
        alignment = df.groupby(['start_band', 'outcome_type'], observed=False)['vis_score'].mean().reset_index()

        # 4. Pivot for clear comparison
        pivot = alignment.pivot(index='start_band', columns='outcome_type', values='vis_score')
        
        # 5. Calculate the "Eraser Gap"
        # Positive Gap = Good Metric (Prevented catches had higher erasure)
        pivot['VIS_Gap'] = pivot['Prevented Catch'] - pivot['Allowed Catch']
        
        return pivot.round(2)


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
    

if __name__ == "__main__":
    SUMMARY_FILE = "data/processed/eraser_analysis_summary.csv"
    
    gen = TableGenerator(SUMMARY_FILE)
    
    print("\n--- SHRUNK LEADERBOARD (Bayesian m=20) ---")
    print(gen.generate_shrunk_leaderboard().to_string(index=False))
    
    print("\n--- QUADRANT SUMMARY ---")
    print(gen.generate_quadrant_counts().to_string(index=False))
    
    print("\n--- SITUATIONAL CONTEXT ---")
    print(gen.generate_situational_summary().head(10).to_string(index=False))
    
    print("\n--- OUTCOME ALIGNMENT (The Validity Test) ---")
    print(gen.generate_outcome_alignment())

    print("\n--- DAMAGE CONTROL VALIDATION (YAC) ---")
    print(gen.generate_damage_control_validation())