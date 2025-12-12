import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from src.schema import PhysicsSchema

class PhysicsEngine:
    def __init__(self):
        self.output_schema = PhysicsSchema

    def derive_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies Savitzky-Golay filter to calculate generic Speed (s) and Acceleration (a).
        REMOVED: Direction (dir) calculation, as we now use specific vectors in Phase B.
        """
        # Ensure temporal ordering for the filter
        df = df.sort_values(['game_id', 'play_id', 'nfl_id', 'frame_id'])
        
        # SAVITZKY-GOLAY PARAMETERS
        WINDOW = 7 # 0.7 seconds
        POLY = 2   # Quadratic fit
        
        def calculate_sg(group):

            if len(group) < WINDOW:
                # 1. Calculate Velocity Components (First Derivative)
                # We use fillna(0) to handle the first frame where diff is NaN
                vx = group['x'].diff().fillna(0) / 0.1
                vy = group['y'].diff().fillna(0) / 0.1
                
                # 2. Calculate Acceleration Components (Second Derivative)
                # Differentiate Velocity to get Acceleration
                ax = vx.diff().fillna(0) / 0.1
                ay = vy.diff().fillna(0) / 0.1
                
                # 3. Calculate Vector Magnitudes
                s = np.sqrt(vx**2 + vy**2)
                a = np.sqrt(ax**2 + ay**2)
                
                return pd.DataFrame(
                    {'s_derived': s, 'a_derived': a}, 
                    index=group.index)
            
            # First Derivative (Velocity)
            vx = savgol_filter(group['x'], window_length=WINDOW, polyorder=POLY, deriv=1, delta=0.1)
            vy = savgol_filter(group['y'], window_length=WINDOW, polyorder=POLY, deriv=1, delta=0.1)
            
            # Second Derivative (Acceleration)
            ax = savgol_filter(group['x'], window_length=WINDOW, polyorder=POLY, deriv=2, delta=0.1)
            ay = savgol_filter(group['y'], window_length=WINDOW, polyorder=POLY, deriv=2, delta=0.1)
            
            # Magnitudes (Scalar)
            s = np.sqrt(vx**2 + vy**2)
            a = np.sqrt(ax**2 + ay**2)
            
            return pd.DataFrame({
                's_derived': s,
                'a_derived': a
            }, index=group.index)

        # Apply grouping
        # Only apply to players (nfl_id is not null)
        mask_players = df['nfl_id'].notna()
        
        physics_cols = df[mask_players].groupby(
            ['game_id', 'play_id', 'nfl_id'], group_keys=False).apply(calculate_sg, include_groups=False)

        # Map back to original DataFrame
        df.loc[physics_cols.index, 's_derived'] = physics_cols['s_derived']
        df.loc[physics_cols.index, 'a_derived'] = physics_cols['a_derived']

        return self.output_schema.validate(df)