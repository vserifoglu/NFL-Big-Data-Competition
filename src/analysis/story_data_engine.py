import pandas as pd
import numpy as np

class StoryDataEngine:
    def __init__(self, summary_path: str, frames_path: str, seed=42):
        self.summary_df = pd.read_csv(summary_path)
        self.frames_path = frames_path
        self.seed = seed
        
    def cast_archetypes(self):
        """
        Scans summary for archetypes. Samples from top candidates to avoid outliers.
        """
        df = self.summary_df
        
        # Deep start (>10), High VIS (>4). Best = Highest VIS.
        eraser_pool = df[
            (df['p_dist_at_throw'] > 10) & 
            (df['vis_score'] > 4) & 
            (df['dist_at_arrival'] < 3) 
        ]
        eraser = self._select_candidate(eraser_pool, sort_col='vis_score', ascending=False)
        
        # Tight start (<2.5), Tight finish (<1.5). Best = Lowest Arrival Dist.
        lockdown_pool = df[
            (df['p_dist_at_throw'] < 2.5) & 
            (df['dist_at_arrival'] < 1.5) &
            (df['vis_score'].abs() < 2)
        ]
        lockdown = self._select_candidate(lockdown_pool, sort_col='dist_at_arrival', ascending=True)
        
        # Cushion (>5), Bad finish (VIS <-4). Best = Lowest (Negative) VIS.
        liability_pool = df[
            (df['p_dist_at_throw'] > 5) & 
            (df['vis_score'] < -4) &
            (df['dist_at_arrival'] > 8)
        ]
        liability = self._select_candidate(liability_pool, sort_col='vis_score', ascending=True)
        
        # Tight start (<3), Bad finish (VIS <-3). Best = Lowest (Negative) VIS.
        lost_step_pool = df[
            (df['p_dist_at_throw'] < 3) & 
            (df['vis_score'] < -3) &
            (df['dist_at_arrival'] > 6)
        ]
        lost_step = self._select_candidate(lost_step_pool, sort_col='vis_score', ascending=True)

        return {
            'Eraser': self._extract_meta(eraser, "Top Eraser (FS)"),
            'Lockdown': self._extract_meta(lockdown, "Lockdown (CB)"),
            'Liability': self._extract_meta(liability, "Liability (Busted)"),
            'Lost Step': self._extract_meta(lost_step, "Lost Step (Double Move)")
        }

    def _select_candidate(self, df, sort_col, ascending, top_n=5):
        """
        Sorts by criteria, takes top N, then randomly picks one.
        """
        if df.empty: return pd.DataFrame()
        
        # Sort to find best candidates
        sorted_df = df.sort_values(sort_col, ascending=ascending)
        
        # Take top chunk (to ensure quality)
        candidates = sorted_df.head(top_n)
        
        # Sample one (to avoid outlier dependence)
        return candidates.sample(n=1, random_state=self.seed)

    def _extract_meta(self, row, label):
        if row.empty: return None
        return {
            'game_id': int(row.iloc[0]['game_id']),
            'play_id': int(row.iloc[0]['play_id']),
            'nfl_id': float(row.iloc[0]['nfl_id']),
            'vis_score': float(row.iloc[0]['vis_score']),
            'label': label
        }

    def get_play_frames(self, play_meta):
        if not play_meta: return pd.DataFrame()
        df = pd.read_csv(self.frames_path)
        return df[(df['game_id'] == play_meta['game_id']) & (df['play_id'] == play_meta['play_id'])].copy()