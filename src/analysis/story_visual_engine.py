import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.patches as patches

# Set style for professional report visuals
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.family'] = 'sans-serif'

class StoryVisualEngine:
    def __init__(self, summary_path: str, animation_path: str, output_dir: str):
        print(f"   [VizGen] Loading Summary: {summary_path}...")
        self.summary_df = pd.read_csv(summary_path)
        
        print(f"   [VizGen] Loading Animation Data (Lazy): {animation_path}...")
        # We load specific columns to keep memory low
        req_cols = ['game_id', 'play_id', 'nfl_id', 'frame_id', 'player_role', 'x', 'y']
        self.frames_df = pd.read_csv(animation_path, usecols=req_cols)
        
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Standardize colors
        self.quad_colors = {
            'Eraser': '#2ecc71',      # Green
            'Lockdown': '#3498db',    # Blue
            'Lost Step': '#f1c40f',   # Yellow
            'Liability': '#e74c3c',   # Red
            'Neutral': '#95a5a6'
        }

    # =========================================
    # VISUAL 1: ERASER LANDSCAPE (SCATTER)
    # =========================================
    def plot_eraser_landscape(self, cast_dict):
        """
        Plots S_throw vs S_arrival.
        Annotates the specific plays identified by StoryEngine.
        """
        print("   [VizGen] Generating V1: Eraser Landscape...")
        df = self.summary_df.copy()
        
        # Apply Quadrant Logic for Coloring
        conditions = [
            (df['p_dist_at_throw'] >= 3.0) & (df['dist_at_arrival'] <= 1.5), # Eraser
            (df['p_dist_at_throw'] < 3.0) & (df['dist_at_arrival'] <= 1.5),  # Lockdown
            (df['p_dist_at_throw'] < 3.0) & (df['dist_at_arrival'] > 1.5),   # Lost Step
            (df['p_dist_at_throw'] >= 3.0) & (df['dist_at_arrival'] > 1.5)   # Liability
        ]
        choices = ['Eraser', 'Lockdown', 'Lost Step', 'Liability']
        df['quadrant_plot'] = np.select(conditions, choices, default='Neutral')
        
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # 1. Main Scatter
        sns.scatterplot(
            data=df, x='p_dist_at_throw', y='dist_at_arrival',
            hue='quadrant_plot', palette=self.quad_colors,
            alpha=0.6, s=40, linewidth=0, ax=ax
        )
        
        # 2. Reference Lines
        ax.plot([0, 25], [0, 25], 'k--', lw=2, alpha=0.3, label='Break Even (VIS=0)')
        ax.axvline(x=3.0, color='gray', linestyle=':', lw=2)
        ax.axhline(y=1.5, color='gray', linestyle=':', lw=2)

        # 3. Annotations (Driven by StoryEngine)
        # We iterate through the 'Cast' dictionary
        for role, play_meta in cast_dict.items():
            if play_meta is None: continue
            
            # Find coordinates in summary
            row = df[(df['game_id'] == play_meta['game_id']) & 
                     (df['play_id'] == play_meta['play_id']) & 
                     (df['nfl_id'] == play_meta['nfl_id'])]
            
            if not row.empty:
                sx = row.iloc[0]['p_dist_at_throw']
                sy = row.iloc[0]['dist_at_arrival']
                
                # Annotate
                ax.annotate(play_meta['label'], 
                            (sx, sy), xytext=(sx+2, sy+2),
                            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=8),
                            fontsize=11, fontweight='bold', 
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1))

        ax.set_title('The Eraser Landscape: Recovery vs. Result', fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel('Player Distance at Throw (The Mess)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Distance at Arrival (The Finish)', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 20)
        ax.legend(title='Quadrants', loc='upper right')
        
        output_path = os.path.join(self.output_dir, 'V1_Eraser_Landscape.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    # =========================================
    # VISUAL 2: RACE CHARTS (TRAJECTORIES)
    # =========================================
    def plot_race_charts(self, cast_dict):
        """
        Plots the distance-over-time for the 4 archetypes selected by StoryEngine.
        """
        print("   [VizGen] Generating V2: Race Charts...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12), sharey=True)
        axes = axes.flatten()
        quad_order = ['Eraser', 'Lockdown', 'Liability', 'Lost Step']

        # Legend Elements
        legend_elements = [
            plt.Line2D([0], [0], color='grey', lw=3, label='Defender Path'),
            plt.Line2D([0], [0], color='gray', linestyle=':', label='Closed (1.5y)'),
            plt.Line2D([0], [0], marker='o', color='grey', label='Throw', markersize=10, linestyle='None'),
            plt.Line2D([0], [0], marker='X', color='grey', label='Arrival', markersize=10, linestyle='None')
        ]

        for i, quad_name in enumerate(quad_order):
            ax = axes[i]
            play_meta = cast_dict.get(quad_name)
            color = self.quad_colors.get(quad_name, 'grey')

            # Handle Missing Cast Member
            if play_meta is None:
                ax.set_title(f"{quad_name}", fontsize=16, fontweight='bold', color=color)
                ax.text(0.5, 0.5, "No Candidate Found", ha='center')
                continue

            # Title with VIS Score
            vis_val = play_meta['vis_score']
            sign = "+" if vis_val > 0 else ""
            ax.set_title(f"{quad_name}\n(VIS: {sign}{vis_val:.1f} yds)", fontsize=16, fontweight='bold', color=color)

            # Get Tracking Data
            play_df = self.frames_df[
                (self.frames_df['game_id'] == play_meta['game_id']) & 
                (self.frames_df['play_id'] == play_meta['play_id'])
            ]
            
            def_track = play_df[play_df['nfl_id'] == play_meta['nfl_id']].sort_values('frame_id')
            target_track = play_df[play_df['player_role'] == 'Targeted Receiver'].sort_values('frame_id')

            if def_track.empty or target_track.empty:
                continue
                    
            merged = pd.merge(def_track, target_track, on='frame_id', suffixes=('_d', '_t'))
            merged['dist'] = np.sqrt((merged['x_d'] - merged['x_t'])**2 + (merged['y_d'] - merged['y_t'])**2)
            merged['time_sec'] = (merged['frame_id'] - merged['frame_id'].min()) * 0.1

            # PLOT LOGIC
            # 1. Line & Fill
            sns.lineplot(data=merged, x='time_sec', y='dist', ax=ax, lw=4, color=color, alpha=0.9)
            ax.fill_between(merged['time_sec'], merged['dist'], 0, color=color, alpha=0.1)

            # 2. Markers
            start = merged.iloc[0]
            end = merged.iloc[-1]
            
            ax.scatter(start['time_sec'], start['dist'], color=color, s=150, marker='o', zorder=5, edgecolors='white', lw=2)
            ax.annotate('THROW', (start['time_sec'], start['dist']), xytext=(5, 5), textcoords='offset points', fontsize=9, fontweight='bold', color=color)

            ax.scatter(end['time_sec'], end['dist'], color=color, s=150, marker='X', zorder=5, edgecolors='white', lw=2)
            ax.annotate('ARRIVAL', (end['time_sec'], end['dist']), xytext=(5, 5), textcoords='offset points', fontsize=9, fontweight='bold', color=color)

            # Formatting
            ax.axhline(1.5, color='gray', linestyle=':', lw=2)
            ax.axhline(0, color='black', lw=1)
            ax.set_ylim(-0.5, 18)
            ax.set_xlim(0, merged['time_sec'].max() + 0.5)
            ax.grid(True, alpha=0.3)
            
            if i in [2, 3]: ax.set_xlabel('Seconds After Throw', fontsize=12, fontweight='bold')
            if i in [0, 2]: ax.set_ylabel('Separation (Yards)', fontsize=12, fontweight='bold')

        # Global Legend
        fig.legend(handles=legend_elements, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.05), frameon=False, fontsize=11)
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, 'V2_Race_Charts.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    # =========================================
    # VISUAL 3: HEATMAP
    # =========================================
    def plot_coverage_heatmap(self):
        """
        Average VIS by Route Depth vs Coverage Type.
        """
        print("   [VizGen] Generating V3: Coverage Heatmap...")
        df = self.summary_df.copy()

        if 'pass_length' not in df.columns or 'team_coverage_type' not in df.columns:
            print("      [!] Skipping Heatmap: Columns missing.")
            return

        # Binning
        bins = [-5, 5, 10, 15, 25, 100]
        labels = ['Behind LOS', 'Short (0-5)', 'Medium (5-10)', 'Int (10-15)', 'Deep (15+)']
        df['depth_band'] = pd.cut(df['pass_length'], bins=bins, labels=labels)

        # Filter
        main_coverages = ['COVER_1', 'COVER_2_MAN', 'COVER_2_ZONE', 'COVER_3_ZONE', 'COVER_4_ZONE', 'COVER_6_ZONE']
        df = df[df['team_coverage_type'].isin(main_coverages)]

        # Pivot
        grouped = df.groupby(['team_coverage_type', 'depth_band'], observed=False)
        heatmap_data = grouped['vis_score'].mean()
        counts = grouped.size()
        heatmap_data = heatmap_data.where(counts >= 10).unstack()

        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        cmap = sns.diverging_palette(10, 130, as_cmap=True) # Red-Green
        
        sns.heatmap(
            heatmap_data, annot=True, fmt=".1f", cmap=cmap,
            center=0, vmin=-2, vmax=4, linewidths=.5,
            cbar_kws={'label': 'Average VIS (Yards Erased)'}, ax=ax
        )

        ax.set_title('Where Defenses Erase Space: Scheme vs. Depth', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Target Depth (Air Yards)', fontsize=14)
        ax.set_ylabel('Coverage Scheme', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        
        output_path = os.path.join(self.output_dir, 'V3_Coverage_Heatmap.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()