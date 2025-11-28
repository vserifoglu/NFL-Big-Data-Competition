import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. VISUALIZATION LOGIC
# ==========================================
def generate_visuals(results_df, qbs):
    print("Generating Charts...")
    sns.set_theme(style="whitegrid")
    
    # --- CHART 1: CONSEQUENCE ---
    plt.figure(figsize=(10, 6))
    if not results_df.empty and 'recovery_tax' in results_df.columns:
        # Drop NaNs for plotting
        plot_data = results_df.dropna(subset=['recovery_tax'])
        if len(plot_data) > 500:
            plot_data = plot_data.sample(n=500, random_state=42)
            
        if not plot_data.empty:
            sns.regplot(data=plot_data, x='clv', y='recovery_tax', 
                       scatter_kws={'alpha':0.5, 's':20}, line_kws={'color':'red'})
            plt.title("Die Konsequenz: The Physical Cost of Mental Deception", fontsize=16, fontweight='bold')
            plt.xlabel("Pre-Throw: Deception (CLV) [yds/s]", fontsize=12)
            plt.ylabel("Post-Throw: Recovery Tax (Lost Yards) [yds]", fontsize=12)
            plt.tight_layout()
            plt.savefig('recovery_tax_chart.png')
            print("Saved 'recovery_tax_chart.png'")

    # --- CHART 2: TRUTH CHART ---
    plt.figure(figsize=(10, 6))
    def bucket_clv(clv):
        if clv > 1.5: return 'High Leak (Fooled)'
        if clv < -0.5: return 'Locked In (Read It)'
        return 'Neutral'
    
    results_df['Leak_Category'] = results_df['clv'].apply(bucket_clv)
    results_df['is_complete'] = (results_df['pass_result'] == 'C').astype(int)
    
    chart_data = results_df.groupby('Leak_Category')['is_complete'].mean().reset_index()
    chart_data['sort_val'] = chart_data['Leak_Category'].map({'High Leak (Fooled)': 0, 'Neutral': 1, 'Locked In (Read It)': 2})
    chart_data = chart_data.sort_values('sort_val').reset_index(drop=True)
    
    sns.barplot(data=chart_data, x='Leak_Category', y='is_complete', palette=['#ff4b4b', '#d3d3d3', '#4b4bff'])
    plt.title("The Cost of Getting Fooled: Completion %", fontsize=16, fontweight='bold')
    plt.ylabel("Completion Percentage", fontsize=12)
    plt.ylim(0, 1.0)
    
    for index, row in chart_data.iterrows():
        plt.text(index, row.is_complete + 0.02, f"{row.is_complete*100:.1f}%", color='black', ha="center", fontweight='bold')

    plt.tight_layout()
    plt.savefig('truth_chart_final.png')
    print("Saved 'truth_chart_final.png'")

# ==========================================
# 2. COACHING REPORTS (SIMPLIFIED)
# ==========================================
def generate_scouting_reports(results_df):
    # NOTE: This function now expects results_df to ALREADY have qb_name, target_name, etc.
    print("\n--- GENERATING DUAL-THREAT SCOUTING REPORTS ---\n")

    if 'qb_name' not in results_df.columns:
        print("Error: Player names missing from results. Cannot generate reports.")
        return None

    # --- REPORT 1: THE PUPPETEERS ---
    qb_leaks = results_df[results_df['leak_cause'] == 'Puppeteer']
    qb_stats = qb_leaks.groupby('qb_name').agg({'clv': ['mean', 'count'], 'epa': 'mean'}).reset_index()
    qb_stats.columns = ['Quarterback', 'Avg_Manipulation_Score', 'Plays', 'EPA']
    
    print(">>> THE PUPPETEER INDEX (Top QBs at moving defenders with Eyes) <<<")
    print(qb_stats[qb_stats['Plays'] >= 3].sort_values('Avg_Manipulation_Score', ascending=False).head(5))

    # --- REPORT 2: THE GRAVITY INDEX ---
    wr_leaks = results_df[results_df['leak_cause'] == 'Gravity']
    wr_stats = wr_leaks.groupby('target_name').agg({'clv': ['mean', 'count'], 'epa': 'mean'}).reset_index()
    wr_stats.columns = ['Receiver', 'Avg_Gravity_Score', 'Plays', 'EPA']
    
    print("\n>>> THE GRAVITY INDEX (Top WRs at dragging defenders out of zones) <<<")
    print(wr_stats[wr_stats['Plays'] >= 3].sort_values('Avg_Gravity_Score', ascending=False).head(5))

    # --- REPORT 3: THE VICTIMS ---
    def_stats = results_df.groupby(['player_name', 'player_position']).agg({'clv': ['mean', 'count'], 'epa': 'mean'}).reset_index()
    def_stats.columns = ['Defender', 'Pos', 'Avg_Bait_Score', 'Plays', 'EPA_Allowed']
    
    print("\n>>> THE LIABILITY LIST (Most Fooled Defenders) <<<")
    print(def_stats[def_stats['Plays'] >= 3].sort_values('Avg_Bait_Score', ascending=False).head(5))

    return qb_stats

# ==========================================
# 3. DATA LOADING & PROCESSING
# ==========================================
def load_data(input_dir):
    input_files = sorted(glob.glob(os.path.join(input_dir, 'input_2023_w01.csv')))
    if not input_files:
        print("ERROR: No input files found.")
        return pd.DataFrame(), pd.DataFrame()
    print(f"Loading {len(input_files)} Input file(s)...")
    input_df = pd.concat([pd.read_csv(f) for f in input_files], ignore_index=True)
    
    output_files = sorted(glob.glob(os.path.join(input_dir, 'output_2023_w01.csv')))
    output_df = pd.DataFrame()
    if output_files:
        print(f"Loading {len(output_files)} Output file(s)...")
        output_df = pd.concat([pd.read_csv(f) for f in output_files], ignore_index=True)
    
    return input_df, output_df

def normalize_direction(df):
    df = df.copy()
    if 'play_direction' not in df.columns: return df
    mask = df['play_direction'].str.lower() == 'left'
    df.loc[mask, 'x'] = 120 - df.loc[mask, 'x']
    df.loc[mask, 'y'] = 53.3 - df.loc[mask, 'y']
    if 'dir' in df.columns: df.loc[mask, 'dir'] = (df.loc[mask, 'dir'] + 180) % 360
    if 'o' in df.columns: df.loc[mask, 'o'] = (df.loc[mask, 'o'] + 180) % 360
    if 'ball_land_x' in df.columns:
        df.loc[mask, 'ball_land_x'] = 120 - df.loc[mask, 'ball_land_x']
        df.loc[mask, 'ball_land_y'] = 53.3 - df.loc[mask, 'ball_land_y']
    return df

# ==========================================
# 4. MAIN LOGIC (SINGLE MERGE STRATEGY)
# ==========================================
def main():
    input_dir = 'data/train' 
    supp_path = 'data/supplementary_data.csv'

    input_df, output_df = load_data(input_dir)
    if input_df.empty: return
    
    supp_df = pd.read_csv(supp_path, low_memory=False)
    
    # ID Cleanup
    for df in [input_df, output_df, supp_df]:
        if not df.empty:
            df['game_id'] = df['game_id'].astype(int)
            df['play_id'] = df['play_id'].astype(int)

    print("Normalizing Coordinates...")
    input_df = normalize_direction(input_df)
    if not output_df.empty:
        dir_map = input_df[['game_id', 'play_id', 'play_direction']].drop_duplicates()
        output_df = output_df.merge(dir_map, on=['game_id', 'play_id'], how='left')
        output_df = normalize_direction(output_df)

    print("Applying Filters...")
    input_df = input_df.merge(supp_df[['game_id', 'play_id', 'team_coverage_man_zone', 'pass_result', 'expected_points_added']], on=['game_id', 'play_id'], how='inner')
    
    filtered_input = input_df[
        (input_df['team_coverage_man_zone'].astype(str).str.contains('Zone', case=False, na=False)) &
        (input_df['pass_result'].isin(['C', 'I', 'IN']))
    ].copy()
    
    results = []
    animation_cache = [] 
    
    print("Calculating CLV and Caching Highlights...")
    
    for (game_id, play_id), play_input in filtered_input.groupby(['game_id', 'play_id']):
        
        # --- PRE-CALCULATION CHECKS ---
        ball_x = play_input['ball_land_x'].iloc[0]
        ball_y = play_input['ball_land_y'].iloc[0]
        if pd.isna(ball_x): continue

        last_frame = play_input['frame_id'].max()
        window_start = max(1, last_frame - 5)
        
        # --- 1. FIND DEFENDER ---
        start_df = play_input[(play_input['frame_id'] == window_start) & (play_input['player_role'] == 'Defensive Coverage')]
        if start_df.empty: continue
        dists = np.sqrt((start_df['x'] - ball_x)**2 + (start_df['y'] - ball_y)**2)
        if dists.empty: continue
        subject_idx = dists.idxmin()
        subject_id = start_df.loc[subject_idx, 'nfl_id']
        
        # --- 2. VISION SPLIT ---
        def_x, def_y, def_o = start_df.loc[subject_idx, ['x', 'y', 'o']]
        
        qb_start = play_input[(play_input['frame_id'] == window_start) & (play_input['player_role'] == 'Passer')]
        leak_cause = 'Unknown'
        
        if not qb_start.empty:
            qb_x = qb_start.iloc[0]['x']
            qb_y = qb_start.iloc[0]['y']
            vec_deg = np.degrees(np.arctan2(qb_y - def_y, qb_x - def_x)) % 360
            def_o_math = (90 - def_o) % 360
            diff = abs(def_o_math - vec_deg)
            if min(diff, 360-diff) < 60:
                leak_cause = 'Puppeteer'
            else:
                leak_cause = 'Gravity'

        # --- 3. CLV ---
        subj_pre = play_input[(play_input['nfl_id'] == subject_id) & (play_input['frame_id'] >= window_start)].copy()
        if subj_pre.empty: continue
        dir_rad = np.radians(90 - subj_pre['dir'])
        vx = subj_pre['s'] * np.cos(dir_rad)
        vy = subj_pre['s'] * np.sin(dir_rad)
        dx, dy = ball_x - subj_pre['x'], ball_y - subj_pre['y']
        dist = np.sqrt(dx**2 + dy**2) + 1e-6
        clv = -1 * ((vx * (dx/dist)) + (vy * (dy/dist))).mean()
        
        # --- 4. TAX ---
        recovery_tax = np.nan
        play_output_data = pd.DataFrame() 
        if not output_df.empty:
            play_output_data = output_df[(output_df['game_id'] == game_id) & (output_df['play_id'] == play_id)]
            subj_post = play_output_data[play_output_data['nfl_id'] == subject_id].sort_values('frame_id').head(10)
            if len(subj_post) >= 5:
                actual = np.sqrt((subj_post.iloc[0]['x']-ball_x)**2 + (subj_post.iloc[0]['y']-ball_y)**2) - \
                         np.sqrt((subj_post.iloc[-1]['x']-ball_x)**2 + (subj_post.iloc[-1]['y']-ball_y)**2)
                recovery_tax = (8.0 * (len(subj_post)/10.0)) - actual

        results.append({
            'game_id': game_id, 'play_id': play_id, 'nfl_id': subject_id,
            'clv': clv, 'recovery_tax': recovery_tax, 'leak_cause': leak_cause,
            'epa': play_input['expected_points_added'].iloc[0],
            'pass_result': play_input['pass_result'].iloc[0]
        })

        # --- 5. ANIMATION CACHE ---
        if clv > 2.5 or clv < -1.5:
            last_frame_in = play_input['frame_id'].max()
            pre_throw_clip = play_input[play_input['frame_id'] >= (last_frame_in - 15)].copy()
            post_throw_clip = pd.DataFrame()
            if not play_output_data.empty:
                first_frame_out = play_output_data['frame_id'].min()
                post_throw_clip = play_output_data[play_output_data['frame_id'] <= (first_frame_out + 15)].copy()
            
            full_clip = pd.concat([pre_throw_clip, post_throw_clip])
            full_clip['highlight_type'] = 'High Leak' if clv > 2.5 else 'Good Read'
            full_clip['clv_score'] = clv
            animation_cache.append(full_clip)

    # 6. REPORTING & SAVING (SINGLE MERGE)
    results_df = pd.DataFrame(results)
    print(f"Analysis Complete. Processed {len(results_df)} plays.")
    
    if not results_df.empty:
        print("Merging player names for export...")
        
        # 1. Defender Names
        def_map = input_df[['nfl_id', 'player_name', 'player_position']].drop_duplicates(subset=['nfl_id'])
        results_df = results_df.merge(def_map, on='nfl_id', how='left')
        
        # 2. QB Names
        qb_map = input_df[input_df['player_role'] == 'Passer'][['game_id', 'play_id', 'player_name']].rename(columns={'player_name': 'qb_name'})
        results_df = results_df.merge(qb_map, on=['game_id', 'play_id'], how='left')
        
        # 3. Target Names
        target_map = input_df[input_df['player_role'] == 'Targeted Receiver'][['game_id', 'play_id', 'player_name']].rename(columns={'player_name': 'target_name'}).drop_duplicates(subset=['game_id', 'play_id'])
        results_df = results_df.merge(target_map, on=['game_id', 'play_id'], how='left')
        
        # SAVE
        print("Saving 'clv_data_export.csv'...")
        results_df.to_csv("clv_data_export.csv", index=False)
        
        if animation_cache:
            print(f"Saving 'animation_cache.csv' ({len(animation_cache)} plays)...")
            pd.concat(animation_cache).to_csv("animation_cache.csv", index=False)

        # REPORTS (Uses the already merged df)
        qbs = generate_scouting_reports(results_df)
        generate_visuals(results_df, qbs)
    else:
        print("No results found.")

if __name__ == '__main__':
    main()