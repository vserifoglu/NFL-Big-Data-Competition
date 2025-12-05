import pandas as pd
import numpy as np
from schema import VoidResultSchema

def generate_detected_voids(df):
    df = df.copy()

    # 1. Prepare Data
    play_end_frames = df.groupby(['game_id', 'play_id'])['frame_id'].max().reset_index()
    plays_with_ball = df.merge(play_end_frames, on=['game_id', 'play_id', 'frame_id'], how='inner')
    plays_with_ball = plays_with_ball.dropna(subset=['ball_land_x', 'ball_land_y']).copy()

    relevant_frames = plays_with_ball[plays_with_ball['player_role'] == 'Defensive Coverage'].copy()

    # 2. Assign Ownership
    relevant_frames['dist_zone_to_ball'] = np.sqrt(
        (relevant_frames['target_zone_x'] - relevant_frames['ball_land_x'])**2 + 
        (relevant_frames['target_zone_y'] - relevant_frames['ball_land_y'])**2
    )
    
    relevant_frames['min_zone_dist'] = relevant_frames.groupby(['game_id', 'play_id'])['dist_zone_to_ball'].transform('min')
    
    # Filter 10-yard scheme exception
    relevant_frames = relevant_frames[relevant_frames['min_zone_dist'] < 10.0].copy()

    is_owner = relevant_frames['dist_zone_to_ball'] == relevant_frames['min_zone_dist']
    owners_df = relevant_frames[is_owner].copy()
    owners_df = owners_df.drop_duplicates(subset=['game_id', 'play_id'])

    # 3. Calculate Geometry
    owners_df['drift_yards'] = np.sqrt(
        (owners_df['target_zone_x'] - owners_df['x'])**2 + 
        (owners_df['target_zone_y'] - owners_df['y'])**2
    )
    
    owners_df['dist_to_ball'] = np.sqrt(
        (owners_df['x'] - owners_df['ball_land_x'])**2 + 
        (owners_df['y'] - owners_df['ball_land_y'])**2
    )
    
    # 4. Determine Flags
    DRIFT_TOLERANCE = 5.0
    CATCH_RADIUS = 3.0

    # Logic: You drifted too far AND you weren't close enough to contest the catch.
    owners_df['void_penalty'] = (
        (owners_df['drift_yards'] > DRIFT_TOLERANCE) & 
        (owners_df['dist_to_ball'] > CATCH_RADIUS)
    )

    # 5. EPA Logic
    owners_df['damage_epa'] = owners_df['expected_points_added'].clip(lower=0)
    owners_df['is_punished'] = owners_df['damage_epa'] > 0

    return VoidResultSchema.validate(owners_df)