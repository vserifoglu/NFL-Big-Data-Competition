import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.patches as patches
from scipy.interpolate import UnivariateSpline

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
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))  # Removed sharey=True for independent axes
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

            # Apply spline smoothing to reduce tracking noise (s=50 recommended balance)
            time_arr = merged['time_sec'].values
            dist_arr = merged['dist'].values
            
            # Spline needs at least 4 points and unique x values
            if len(time_arr) >= 4:
                try:
                    spline = UnivariateSpline(time_arr, dist_arr, s=50)
                    smooth_dist = spline(time_arr)
                except:
                    smooth_dist = dist_arr  # Fallback to raw if spline fails
            else:
                smooth_dist = dist_arr
            
            merged['smooth_dist'] = smooth_dist
            
            # Calculate axis limits early (needed for annotations)
            max_dist = merged['smooth_dist'].max()
            max_time = merged['time_sec'].max()

            # PLOT LOGIC
            # 1. Contested Zone Shading (0-1.5 yards) - light gray background
            ax.axhspan(0, 1.5, color='#d5d5d5', alpha=0.4, zorder=0)
            ax.text(max_time * 0.95, 0.75, 'CONTESTED\nZONE', ha='right', va='center',
                   fontsize=8, color='#666666', style='italic', alpha=0.8)
            
            # 2. Smoothed Line & Fill
            ax.plot(merged['time_sec'], merged['smooth_dist'], lw=4, color=color, alpha=0.9)
            ax.fill_between(merged['time_sec'], merged['smooth_dist'], 0, color=color, alpha=0.1)

            # 3. Markers (use smoothed values for consistency)
            start = merged.iloc[0]
            end = merged.iloc[-1]
            
            ax.scatter(start['time_sec'], start['smooth_dist'], color=color, s=150, marker='o', zorder=5, edgecolors='white', lw=2)
            ax.annotate('THROW', (start['time_sec'], start['smooth_dist']), xytext=(5, 5), textcoords='offset points', fontsize=9, fontweight='bold', color=color)

            ax.scatter(end['time_sec'], end['smooth_dist'], color=color, s=150, marker='X', zorder=5, edgecolors='white', lw=2)
            ax.annotate('ARRIVAL', (end['time_sec'], end['smooth_dist']), xytext=(5, 5), textcoords='offset points', fontsize=9, fontweight='bold', color=color)

            # 4. Closing Rate annotation (yards closed per second)
            flight_time = end['time_sec'] - start['time_sec']
            closing_rate = (start['smooth_dist'] - end['smooth_dist']) / flight_time if flight_time > 0 else 0
            rate_sign = "+" if closing_rate < 0 else "−"  # Negative = opening up, Positive = closing
            
            # Position rate annotation at midpoint of trajectory
            mid_idx = len(merged) // 2
            mid_time = merged.iloc[mid_idx]['time_sec']
            mid_dist = merged.iloc[mid_idx]['smooth_dist']
            
            if quad_name in ['Eraser', 'Lockdown']:
                # Show closing rate for closers
                ax.annotate(f'{rate_sign}{abs(closing_rate):.1f} yds/sec', 
                           (mid_time, mid_dist), xytext=(10, -15), textcoords='offset points',
                           fontsize=10, fontweight='bold', color=color,
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, alpha=0.8),
                           arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
            
            # 5. Decision Point markers for Liability & Lost Step (find inflection point)
            if quad_name in ['Liability', 'Lost Step']:
                # Find the minimum point (where trajectory changes direction)
                smooth_arr = merged['smooth_dist'].values
                min_idx = np.argmin(smooth_arr)
                
                # Only mark if it's not at the start or end (true inflection)
                if 2 < min_idx < len(smooth_arr) - 2:
                    inflection_time = merged.iloc[min_idx]['time_sec']
                    inflection_dist = smooth_arr[min_idx]
                    
                    # Decision point marker
                    ax.scatter(inflection_time, inflection_dist, color='#e67e22', s=200, 
                              marker='o', zorder=6, edgecolors='white', lw=2)
                    
                    label = "Lost leverage" if quad_name == 'Liability' else "Lost balance"
                    ax.annotate(f'⚠ {label}', (inflection_time, inflection_dist), 
                               xytext=(8, 12), textcoords='offset points',
                               fontsize=9, fontweight='bold', color='#c0392b',
                               bbox=dict(boxstyle='round,pad=0.2', facecolor='#fdebd0', edgecolor='#e67e22', alpha=0.9))
            
            # Store flight time for bottom annotation
            play_meta['flight_time'] = flight_time
            
            # Formatting with dynamic limits
            ax.axhline(1.5, color='gray', linestyle=':', lw=2)
            ax.axhline(0, color='black', lw=1)
            ax.set_ylim(-0.5, max(max_dist * 1.15, 5))  # 15% padding, minimum 5 yards
            ax.set_xlim(0, max_time + 0.3)  # Small padding on x-axis
            ax.grid(True, alpha=0.3)
            
            if i in [2, 3]: ax.set_xlabel('Seconds After Throw', fontsize=12, fontweight='bold')
            if i in [0, 2]: ax.set_ylabel('Separation (Yards)', fontsize=12, fontweight='bold')

        # Global Legend
        fig.legend(handles=legend_elements, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=11)
        
        # Flight Time annotation at bottom
        flight_parts = []
        for quad_name in quad_order:
            meta = cast_dict.get(quad_name)
            if meta and 'flight_time' in meta:
                flight_parts.append(f"{quad_name}: {meta['flight_time']:.1f}s")
        
        if flight_parts:
            flight_text = "Ball Flight Time — " + " | ".join(flight_parts)
            fig.text(0.5, -0.06, flight_text, ha='center', va='top', fontsize=10, 
                    color='#555555', style='italic')
        
        plt.tight_layout(rect=[0, 0.02, 1, 1])  # Leave room for bottom annotations
        
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

    # =========================================
    # VISUAL 4: EPA/YAC IMPACT CHART
    # =========================================
    def plot_effort_impact_chart(self):
        """
        Slope chart showing Effort → Outcome (EPA/YAC saved).
        Ties the story together: Context → Effort → Result.
        """
        print("   [VizGen] Generating V4: Effort Impact Chart...")
        df = self.summary_df.copy()
        
        # 1. Filter for Completions Only (where damage occurs)
        completed = df[df['pass_result'] == 'C'].copy()
        
        if completed.empty:
            print("      [!] Skipping Impact Chart: No completions found.")
            return
        
        # 2. Derive YAC
        completed['yac'] = completed['yards_gained'] - completed['pass_length']
        
        # 3. Create Start Distance bands
        dist_bins = [0, 3, 6, 10, 100]
        dist_labels = ['Tight\n(0-3 yds)', 'Medium\n(3-6 yds)', 'High Void\n(6-10 yds)', 'Exempt\n(10+ yds)']
        completed['start_band'] = pd.cut(completed['p_dist_at_throw'], bins=dist_bins, labels=dist_labels)
        
        # 4. Calculate VIS quartiles WITHIN each start band
        def get_quartile_label(group):
            q25 = group['vis_score'].quantile(0.25)
            q75 = group['vis_score'].quantile(0.75)
            conditions = [
                group['vis_score'] <= q25,
                group['vis_score'] >= q75
            ]
            choices = ['Low Effort', 'High Effort']
            group['effort_bucket'] = np.select(conditions, choices, default='Middle')
            return group
        
        completed = completed.groupby('start_band', group_keys=False, observed=False).apply(get_quartile_label)
        
        # 5. Filter to only Q1 and Q4 for clean comparison
        extremes = completed[completed['effort_bucket'].isin(['Low Effort', 'High Effort'])]
        
        # 6. Aggregate by band and effort
        impact_data = extremes.groupby(['start_band', 'effort_bucket'], observed=False).agg(
            avg_epa=('expected_points_added', 'mean'),
            avg_yac=('yac', 'mean'),
            count=('play_id', 'count')
        ).reset_index()
        
        # 7. Create the figure with two subplots (EPA and YAC)
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        bands = ['Tight\n(0-3 yds)', 'Medium\n(3-6 yds)', 'High Void\n(6-10 yds)', 'Exempt\n(10+ yds)']
        x_positions = np.arange(len(bands))
        
        for ax_idx, (metric, title, ylabel) in enumerate([
            ('avg_epa', 'EPA Impact: Effort Saves Points', 'Expected Points Added'),
            ('avg_yac', 'YAC Impact: Effort Limits Damage', 'Yards After Catch')
        ]):
            ax = axes[ax_idx]
            
            # Get data for each effort level
            low_effort = []
            high_effort = []
            savings = []
            
            for band in bands:
                low_row = impact_data[(impact_data['start_band'] == band) & (impact_data['effort_bucket'] == 'Low Effort')]
                high_row = impact_data[(impact_data['start_band'] == band) & (impact_data['effort_bucket'] == 'High Effort')]
                
                low_val = low_row[metric].values[0] if not low_row.empty else np.nan
                high_val = high_row[metric].values[0] if not high_row.empty else np.nan
                
                low_effort.append(low_val)
                high_effort.append(high_val)
                savings.append(low_val - high_val if pd.notna(low_val) and pd.notna(high_val) else np.nan)
            
            # Plot bars - calmer colors
            bar_width = 0.35
            bars_low = ax.bar(x_positions - bar_width/2, low_effort, bar_width, 
                             label='Low Effort (Q1)', color='#d98880', alpha=0.85, edgecolor='white', linewidth=1.5)
            bars_high = ax.bar(x_positions + bar_width/2, high_effort, bar_width, 
                              label='High Effort (Q4)', color='#7dcea0', alpha=0.85, edgecolor='white', linewidth=1.5)
            
            # Add value labels on bars
            for bar in bars_low:
                height = bar.get_height()
                if pd.notna(height):
                    ax.annotate(f'{height:.2f}',
                               xy=(bar.get_x() + bar.get_width()/2, height),
                               xytext=(0, 3), textcoords="offset points",
                               ha='center', va='bottom', fontsize=9, fontweight='bold', color='#943126')
            
            for bar in bars_high:
                height = bar.get_height()
                if pd.notna(height):
                    ax.annotate(f'{height:.2f}',
                               xy=(bar.get_x() + bar.get_width()/2, height),
                               xytext=(0, 3), textcoords="offset points",
                               ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1e8449')
            
            # Add savings labels (no arrows, positioned at bottom of chart to avoid overlap)
            max_height = max([v for v in low_effort + high_effort if pd.notna(v)]) if any(pd.notna(v) for v in low_effort + high_effort) else 2
            
            for i, saved in enumerate(savings):
                if pd.notna(saved) and saved > 0:
                    unit = 'EPA' if metric == 'avg_epa' else 'YAC'
                    # Position label below x-axis to avoid overlap with title
                    ax.text(x_positions[i], -0.15 if metric == 'avg_epa' else -0.4, 
                           f'Saved: {saved:.2f} {unit}', 
                           ha='center', va='top', fontsize=9, fontweight='bold',
                           color='#1a5276', 
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='#d5f5e3', edgecolor='#1e8449', alpha=0.9))
            
            # Formatting
            ax.set_xticks(x_positions)
            ax.set_xticklabels(bands, fontsize=10)
            ax.set_xlabel('Starting Distance Band', fontsize=12, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
            ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
            ax.legend(loc='upper right', fontsize=9)
            ax.axhline(0, color='black', linewidth=0.5)
            ax.grid(axis='y', alpha=0.3)
            
            # Set y-limits with padding for labels
            if metric == 'avg_epa':
                ax.set_ylim(bottom=-0.6, top=max_height + 0.5)
            else:
                ax.set_ylim(bottom=-1.0, top=max_height + 0.8)
        
        # Overall title
        fig.suptitle('The Payoff of Erasure: High-Effort Defenders Save Points & Yards', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])  # Leave room for labels and title
        output_path = os.path.join(self.output_dir, 'V4_Effort_Impact_Chart.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"      -> Saved: {output_path}")