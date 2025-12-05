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