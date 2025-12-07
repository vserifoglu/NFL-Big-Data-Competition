import pandas as pd
import numpy as np
from schema import ContextSchema

class ContextEngine:
    def __init__(self):
        self.output_schema = ContextSchema

    def calculate_void_context(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        PHASE A: Calculates S_throw.
        capture ALL players at the moment of the throw.
        """
        # 1. Filter for Pre-Throw phase
        pre_throw_mask = df['phase'] == 'pre_throw'
        df_pre = df[pre_throw_mask].copy()

        if df_pre.empty:
            print("   CRITICAL: No 'pre_throw' frames found.")
            return pd.DataFrame()

        # IDENTIFY THE SNAPSHOT FRAME
        # we calculate the MAX frame_id for every play
        # transform('max') broadcasts the max value to every row in the group
        last_frame_ids = df_pre.groupby(['game_id', 'play_id'])['frame_id'].transform('max')
        
        # We keep rows where the frame_id matches the last frame of that play
        throw_frames = df_pre[df_pre['frame_id'] == last_frame_ids].copy()

        avg_players = throw_frames.groupby(['game_id', 'play_id']).size().mean()
        print(f"   DEBUG: Avg players captured per snapshot: {avg_players:.1f} (Should be > 1)")
        # -------------------

        # 3. Split into Target vs. Defenders
        # Note: We include 'week' to ensure it survives the merge
        targets = throw_frames[throw_frames['player_role'].astype(str).str.strip() == 'Targeted Receiver'][
            ['game_id', 'play_id', 'nfl_id', 'x', 'y', 'week']
        ].rename(columns={'nfl_id': 'target_nfl_id', 'x': 't_x', 'y': 't_y'})

        defenders = throw_frames[throw_frames['player_role'].astype(str).str.strip() == 'Defensive Coverage'][
            ['game_id', 'play_id', 'nfl_id', 'x', 'y']
        ].rename(columns={'nfl_id': 'def_nfl_id', 'x': 'd_x', 'y': 'd_y'})

        if targets.empty:
            print(f"   CRITICAL: No Targeted Receivers found in {len(throw_frames)} snapshot frames.")
            print(f"   Roles available: {throw_frames['player_role'].unique()}")
            return pd.DataFrame()

        # 4. Cartesian Product (Merge)
        # Now this works because we have ~20 defenders AND 1 target per play
        merged = defenders.merge(targets, on=['game_id', 'play_id'], how='inner')

        # 5. Calculate Euclidean Distance
        merged['dist'] = np.sqrt(
            (merged['d_x'] - merged['t_x'])**2 + 
            (merged['d_y'] - merged['t_y'])**2
        )

        # 6. Find the Nearest Neighbor
        min_dists = merged.loc[merged.groupby(['game_id', 'play_id'])['dist'].idxmin()]

        # 7. Format Output
        context_df = min_dists[['game_id', 'play_id', 'week', 'target_nfl_id', 'def_nfl_id', 'dist']].copy()
        
        context_df = context_df.rename(columns={
            'def_nfl_id': 'nearest_def_nfl_id', 
            'dist': 'dist_at_throw'
        })

        # 8. Apply Classification Labels
        conditions = [
            (context_df['dist_at_throw'] > 5.0),
            (context_df['dist_at_throw'] < 2.0)
        ]
        choices = ['High Void', 'Tight Window']
        context_df['void_type'] = np.select(conditions, choices, default='Neutral')

        return self.output_schema.validate(context_df)