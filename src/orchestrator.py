import os
from datetime import datetime
import pandas as pd
import numpy as np
import gc

# COMPONENTS
from load_data import DataLoader
from data_preprocessor import DataPreProcessor
from physics_engine import PhysicsEngine
from context_engine import ContextEngine
from eraser_engine import EraserEngine
from schema import AnimationScoresSchema, PlayerMetaSchema


def run_full_pipeline():
    start_time = datetime.now()

    # --- CONFIGURATION ---
    DATA_DIR = 'data/train'
    SUPP_FILE = 'data/supplementary_data.csv'
    OUTPUT_DIR = 'data/processed'

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[1/7] Initializing Data Loader ({datetime.now().strftime('%H:%M:%S')})...")
    loader = DataLoader(DATA_DIR, SUPP_FILE)
    raw_supp = loader.load_supplementary()
    raw_tracking = loader.stream_weeks()

    print("[2/7] Preprocessing & Stitching frames...")
    # NOTE: This step applies the "Base Subset" filters (Win Prob 20-80%, Open Field, etc.)
    processor = DataPreProcessor()
    df_clean = processor.run(
        data_stream=raw_tracking, 
        raw_context_df=raw_supp
    )
    
    if df_clean.empty:
        print("CRITICAL ERROR: No data survived filtering. Check your filter masks in 'data_preprocessor.py'.")
        return

    print(f"   -> Dataset Size: {df_clean.shape[0]} frames.")

    print("[3/7] Running Physics Engine (Kinematics)...")
    # Derives: s_derived, a_derived (used for efficiency checks)
    physics_engine = PhysicsEngine()
    df_physics = physics_engine.derive_metrics(df_clean)
    
    del df_clean
    gc.collect() 

    print("[4/7] Phase A: Calculating Void Context (S_throw)...")
    # Calculates: dist_at_throw, void_type (High/Tight)
    context_engine = ContextEngine()
    df_context = context_engine.calculate_void_context(df_physics)
    
    print(f"   -> Identified Voids for {df_context.shape[0]} plays.")


    print("[5/7] Phase B: Calculating Eraser Metrics (VIS)...")
    # Calculates: S_arrival, Distance Closed, VIS, Avg Closing Speed
    eraser_engine = EraserEngine()
    df_metrics = eraser_engine.calculate_erasure(df_physics, df_context)
    
    # ====================================================
    # 6. BENCHMARKING (Calculating CEOE)
    # ====================================================
    print("[6/7] Benchmarking: Creating df_final and calculating CEOE...")
    
    # A. Get Metadata (Position/Role) from Physics DF
    # We need this to group players (e.g., compare CBs to CBs)
    # Using the Schema to select the right columns safely
    meta_cols = list(PlayerMetaSchema.to_schema().columns.keys())
    df_meta = df_physics[meta_cols].drop_duplicates()
    
    # Merge Metadata onto Metrics (now we know WHO the player is)
    df_final = df_metrics.merge(df_meta, on=['game_id', 'play_id', 'nfl_id'], how='left')
    
    # B. Get Context (Void Type) from Context DF
    # We need this to know WHAT the situation was (High Void vs Tight Window)
    # Note: We drop 'dist_at_throw' if it exists to avoid duplication
    if 'dist_at_throw' in df_final.columns:
        df_final = df_final.drop(columns=['dist_at_throw'])
        
    df_final = df_final.merge(
        df_context[['game_id', 'play_id', 'void_type', 'dist_at_throw']], 
        on=['game_id', 'play_id'], 
        how='left'
    )

    # C. CEOE CALCULATION (The "Eraser" Logic)
    # "How much faster did this player close than the average player 
    #  of the SAME POSITION facing the SAME VOID TYPE?"
    print("   -> Computing League Averages...")
    
    # Calculate the benchmark (Mean speed for this Position + Void Type)
    benchmarks = df_final.groupby(['player_position', 'void_type'])['avg_closing_speed'].transform('mean')
    
    # Calculate the Score (Difference from benchmark)
    df_final['ceoe_score'] = df_final['avg_closing_speed'] - benchmarks
    
    # Handle cases where benchmark is NaN (e.g. unique position/role)
    df_final['ceoe_score'] = df_final['ceoe_score'].fillna(0.0)

    # ====================================================
    # 8. HEALTH CHECK (Validation)
    # ====================================================
    print("\n====== PIPELINE HEALTH CHECK ======")
    
    # CHECK 1: VOID DISTRIBUTION
    print("1. Void Type Distribution (Should be mixed):")
    print(df_final['void_type'].value_counts(normalize=True))
    
    # CHECK 2: VIS LOGIC
    print("\n2. VIS Logic Check (Positive = Good):")
    # Grab a play where they closed at least 2 yards
    sample = df_final[df_final['distance_closed'] > 2.0].head(1)
    if not sample.empty:
        print(f"   Start: {sample['dist_at_throw'].values[0]:.1f} | End: {sample['dist_at_arrival'].values[0]:.1f}")
        print(f"   VIS:   {sample['vis_score'].values[0]:.1f} (Expect Positive)")
    else:
        print("   WARNING: No high-closure plays found in sample.")

    # CHECK 3: CEOE SCORES
    print("\n3. Top 3 Erasers (Highest CEOE):")
    cols = ['player_position', 'void_type', 'avg_closing_speed', 'ceoe_score']
    print(df_final.sort_values('ceoe_score', ascending=False)[cols].head(3))
    print("===================================\n")

if __name__ == "__main__":
    run_full_pipeline()