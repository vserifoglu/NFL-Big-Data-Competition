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