import os
from datetime import datetime

from load_data import DataLoader
from data_preprocessor import DataPreProcessor
from landmark_feature import get_landmark_features
from generate_voids import generate_detected_voids

def run_full_pipeline():
    start_time = datetime.now()

    DATA_DIR = 'data/train'
    SUPP_FILE = 'data/supplementary_data.csv'
    OUTPUT_DIR = 'data/processed'

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    loader = DataLoader(DATA_DIR, SUPP_FILE)
    raw_supp = loader.load_supplementary()
    raw_tracking = loader.stream_weeks()
    
    processor = DataPreProcessor()
    df_clean = processor.run(
        data_stream=raw_tracking, 
        raw_context_df=raw_supp
    )

    df_zoned = get_landmark_features(df_clean)

    df_voids_summary = generate_detected_voids(df_zoned)
   
    summary_path = os.path.join(OUTPUT_DIR, 'void_analysis_summary.csv')
    df_voids_summary.to_csv(summary_path, index=False)

    # We select ONLY the columns we need to color the dots
    metrics_to_merge = df_voids_summary[[
        'game_id', 'play_id', 'player_name', 
        'void_penalty', 'is_punished', 'damage_epa', 
        'drift_yards', 'dist_to_ball'
    ]]

    df_final = df_zoned.merge(metrics_to_merge, on=['game_id', 'play_id', 'player_name'], how='left')

    # --- CRITICAL: FILL NA ---
    # If a player is NOT in void_summary, it means they did their job (No Penalty).
    # We must fill NaNs so the Animation Engine knows they are "Safe".
    df_final['void_penalty'] = df_final['void_penalty'].fillna(False)
    df_final['is_punished'] = df_final['is_punished'].fillna(False)
    df_final['damage_epa'] = df_final['damage_epa'].fillna(0.0)

    # [SAVE 2] ANIMATION DATASET
    # Use this for: The Python/Matplotlib Visualizer
    # Contains: x, y, s, dir (for movement) AND void_penalty (for color)
    final_path = os.path.join(OUTPUT_DIR, 'master_animation_data.csv')
    df_final.to_csv(final_path, index=False)
    print(f"✅ Saved Animation Master File to {final_path}")
    
    duration = datetime.now() - start_time
    print(f"🏁 PIPELINE FINISHED in {duration}")

if __name__ == "__main__":
    run_full_pipeline()
import os
import glob
import re
import pandas as pd
from typing import Generator, Tuple
from schema import RawTrackingSchema, OutputTrackingSchema, RawSuppSchema


class DataLoader:
    def __init__(self, data_dir: str, supp_file: str):
        """
        Scans the directory for files but DOES NOT load them yet.
        """
        self.data_dir = data_dir
        self.supp_file = supp_file
        
        # 1. Find all files
        self.input_files = sorted(glob.glob(os.path.join(self.data_dir, 'input_*.csv')))
        self.output_files = glob.glob(os.path.join(self.data_dir, 'output_*.csv'))
        
        self.output_map = {}
        for f in self.output_files:
            match = re.search(r'w(\d{2})', f)
            if not match:
                continue
            self.output_map[match.group(1)] = f

    def load_supplementary(self) -> pd.DataFrame:
        """
        Loads the single Supplementary file.
        """
        if not os.path.exists(self.supp_file):
            raise FileNotFoundError(f"Missing Supp File: {self.supp_file}")
            
        df = pd.read_csv(self.supp_file, low_memory=False)
            
        # VALIDATE (Strict Filter)
        return RawSuppSchema.validate(df)

    def stream_weeks(self) -> Generator[Tuple[str, pd.DataFrame, pd.DataFrame], None, None]:
        """
        The Lazy Loader.
        Yields: (week_num, input_df, output_df)
        
        Validation happens JUST-IN-TIME here.
        """
        for input_path in self.input_files:
            # Extract Week Number
            match = re.search(r'w(\d{2})', input_path)
            if not match: continue
            week_num = match.group(1)
            
            output_path = self.output_map.get(week_num)

            print(f"Streaming Week {week_num}...")
            
            # Load from Disk
            input_raw = pd.read_csv(input_path, low_memory=False)
            output_raw = pd.read_csv(output_path, low_memory=False)
            
            input_raw['nfl_id'] = pd.to_numeric(input_raw['nfl_id'], errors='coerce')
            output_raw['nfl_id'] = pd.to_numeric(output_raw['nfl_id'], errors='coerce')

            # VALIDATE
            input_valid = RawTrackingSchema.validate(input_raw)
            output_valid = OutputTrackingSchema.validate(output_raw)
            
            # Yield the clean, validated data to the Orchestrator
            yield week_num, input_valid, output_valid
import numpy as np
import pandas as pd
from schema import FeatureEngineeredSchema

def get_landmark_features(df):
    """
    FINAL PRODUCTION VERSION (Context-Aware + Schema Validated)
    - Integrates 'Red Zone Squash' logic.
    - Integrates 'Dynamic Depth' for Pattern Matching.
    - Validates output against FeatureEngineeredSchema.
    """
    # Working on a copy to avoid SettingWithCopy warnings on the original DF
    df = df.copy()

    # Geometry Shortcuts
    los = df['los_x']
    y = df['y']
    current_x = df['x']
    depth = current_x - los 
    
    # Dimensions
    NUM_BOT, NUM_TOP = 12.0, 41.3
    HASH_BOT, HASH_TOP = 23.366, 29.966
    FIELD_WIDTH = 53.3
    GOAL_LINE_X = 110.0 # Assumes Normalized 0->120

    # --- 2. LOGIC GATES ---
    is_bottom = y < 26.65
    
    pos = df['player_position']
    is_CB = pos.isin(['CB', 'DB']) 
    is_S = pos.isin(['S', 'SS', 'FS', 'DB'])
    is_LB = pos.isin(['MLB', 'ILB', 'LB', 'OLB'])
    
    cov = df['team_coverage_type']
    is_cov_2 = cov == 'COVER_2_ZONE'
    is_cov_3 = cov == 'COVER_3_ZONE'
    is_cov_4 = cov == 'COVER_4_ZONE'

    # Clamp compression between 0.5 (Goal Line) and 1.0 (Open Field)
    dist_to_goal = GOAL_LINE_X - los
    compression = np.clip(dist_to_goal / 20.0, 0.5, 1.0)
    
    # Dynamic Depth (Fixes Pattern Matching "False Negatives")
    standard_deep_depth = 18.0 * compression
    dynamic_deep_x = los + np.maximum(standard_deep_depth, depth)

    # Static Compressed Depths
    flat_depth = 5.0 * compression
    hook_depth = 12.0 * compression
    
    # Coordinates Calculation
    slot_target_x = los + hook_depth
    slot_target_y = np.where(is_bottom, (HASH_BOT + NUM_BOT)/2, (HASH_TOP + NUM_TOP)/2)

    cov2_flat_x = los + flat_depth
    cov2_flat_y = np.where(is_bottom, 5, FIELD_WIDTH - 5)
    
    deep_half_x = dynamic_deep_x 
    deep_half_y = np.where(is_bottom, 13.3, FIELD_WIDTH - 13.3) 

    deep_13_x = dynamic_deep_x   
    deep_13_y = np.where(is_bottom, 6, FIELD_WIDTH - 6) 
    
    post_s_x = dynamic_deep_x    
    post_s_y = 26.65 

    quarters_s_x = dynamic_deep_x 
    quarters_s_y = np.where(is_bottom, HASH_BOT, HASH_TOP) 

    lb_flat_x = los + (10 * compression)
    lb_flat_y = np.where(is_bottom, NUM_BOT, NUM_TOP)
    
    lb_hook_x = los + hook_depth
    lb_hook_y = np.where(is_bottom, HASH_BOT, HASH_TOP)

    slot_boundary_bot = NUM_BOT + 4 
    slot_boundary_top = NUM_TOP - 4 
    is_slot_area = (y > slot_boundary_bot) & (y < slot_boundary_top)
    
    dist_to_hash = np.minimum(np.abs(y - HASH_BOT), np.abs(y - HASH_TOP))
    dist_to_num = np.minimum(np.abs(y - NUM_BOT), np.abs(y - NUM_TOP))
    is_LB_wide = dist_to_num < dist_to_hash 

    conditions = [
        # CORNERBACKS
        (is_CB & is_slot_area & (is_cov_3 | is_cov_4) & (depth < 15)), # Nickel Seam
        (is_CB & is_slot_area & (is_cov_3 | is_cov_4)),                # Deep Slot Match
        (is_CB & is_cov_2),                                            # Cov 2 Flat
        (is_CB & ((y <= slot_boundary_bot) | (y >= slot_boundary_top))), # Deep Outside

        # SAFETIES
        (is_S & is_cov_2),                  # Deep 1/2
        (is_S & is_cov_3 & (depth < 12)),   # Cov 3 Rotator
        (is_S & is_cov_3),                  # Post Safety
        (is_S & is_cov_4),                  # Quarters

        # LINEBACKERS
        (is_LB & is_LB_wide),               # Curl/Flat
        (is_LB)                             # Hook
    ]

    choices_name = [
        "Nickel Seam", "Deep 1/4 (Match)", "Cov2 Flat", "Deep Outside",
        "Deep 1/2", "Cov3 Rotator", "Deep Post", "Deep 1/4 (Inside)",
        "Curl/Flat", "Hook (Middle)"
    ]
    
    choices_x = [
        slot_target_x, quarters_s_x, cov2_flat_x, deep_13_x,
        deep_half_x, los+10, post_s_x, quarters_s_x,
        lb_flat_x, lb_hook_x
    ]

    choices_y = [
        slot_target_y, quarters_s_y, cov2_flat_y, deep_13_y,
        deep_half_y, y, post_s_y, quarters_s_y,
        lb_flat_y, lb_hook_y
    ]

    df['zone_assignment'] = np.select(conditions, choices_name, default="Unknown")
    df['target_zone_x'] = np.select(conditions, choices_x, default=np.nan)
    df['target_zone_y'] = np.select(conditions, choices_y, default=np.nan)

    return FeatureEngineeredSchema.validate(df)
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
