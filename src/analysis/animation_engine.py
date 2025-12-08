import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
from matplotlib.offsetbox import AnchoredText
import os

class AnimationEngine:
    def __init__(self, summary_path, frames_path, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"   [Animator] Loading Data...")
        self.summary_df = pd.read_csv(summary_path)
        
        # ADDED: 'defensive_team', 'yardline_number', 'yardline_side', 'team_coverage_type'
        cols = [
            'game_id', 'play_id', 'nfl_id', 'frame_id', 'x', 'y', 
            'player_role', 'player_name', 'ball_land_x', 'ball_land_y',
            'down', 'yards_to_go', 'pass_result', 'possession_team', 'defensive_team',
            'yardline_number', 'yardline_side', 'team_coverage_type'
        ]
        
        self.frames_df = pd.read_csv(frames_path, usecols=cols)

    def _draw_field(self, ax):
        """Sets up the static field background."""
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 53.3)
        ax.set_facecolor('#f0f0f0')
        
        # Endzones
        ax.add_patch(patches.Rectangle((0, 0), 10, 53.3, color='#a5c9a5', alpha=0.3, zorder=0))
        ax.add_patch(patches.Rectangle((110, 0), 10, 53.3, color='#a5c9a5', alpha=0.3, zorder=0))
        
        # Yard lines
        for x in range(10, 110, 10):
            alpha = 0.8 if x % 10 == 0 else 0.3
            ax.axvline(x, color='white', linestyle='-', linewidth=2, alpha=alpha, zorder=1)
            if x % 10 == 0 and 10 < x < 110:
                num = x if x <= 50 else 100 - x
                ax.text(x, 5, str(num), color='grey', ha='center', fontsize=10, alpha=0.5)

    def generate_video(self, game_id, play_id, eraser_id, filename="play_animation.mp4"):
        print(f"   [Animator] Rendering video for {game_id}-{play_id}...")
        
        # 1. Get Play Data
        play_frames = self.frames_df[
            (self.frames_df['game_id'] == game_id) & 
            (self.frames_df['play_id'] == play_id)
        ].sort_values('frame_id')
        
        if play_frames.empty: return

        # 2. Actors & Context
        target_id = play_frames[play_frames['player_role'] == 'Targeted Receiver']['nfl_id'].iloc[0]
        
        summary_row = self.summary_df[
            (self.summary_df['game_id'] == game_id) & 
            (self.summary_df['play_id'] == play_id)
        ]
        
        # Get Scores
        vis_score = 0.0
        start_dist = 0.0
        context_id = None
        
        if not summary_row.empty:
            eraser_row = summary_row[summary_row['nfl_id'] == eraser_id]
            if not eraser_row.empty:
                vis_score = eraser_row.iloc[0]['vis_score']
                start_dist = eraser_row.iloc[0]['p_dist_at_throw']
            context_id = summary_row.loc[summary_row['p_dist_at_throw'].idxmin()]['nfl_id']

        # 3. BALL TRAJECTORY LOGIC
        # --- FIX: DEFINE unique_frames HERE ---
        unique_frames = play_frames['frame_id'].unique()
        # --------------------------------------
        
        start_frame = play_frames['frame_id'].min()
        end_frame = play_frames['frame_id'].max()
        total_steps = len(unique_frames)
        
        # Passer Logic
        passer = play_frames[(play_frames['frame_id'] == start_frame) & (play_frames['player_role'] == 'Passer')]
        if not passer.empty:
            bx_start, by_start = passer.iloc[0]['x'], passer.iloc[0]['y']
        else:
            bx_start = play_frames.iloc[0]['ball_land_x'] - 15 
            by_start = 26.65

        bx_end, by_end = play_frames.iloc[0]['ball_land_x'], play_frames.iloc[0]['ball_land_y']
        
        ball_x = np.linspace(bx_start, bx_end, total_steps)
        ball_y = np.linspace(by_start, by_end, total_steps)
        
        # Use the defined unique_frames for the zip
        ball_pos_dict = {f: (x, y) for f, x, y in zip(unique_frames, ball_x, ball_y)}

        # 4. Setup Figure
        fig, ax = plt.subplots(figsize=(12, 6))
        self._draw_field(ax)
        
        # Context Box
        meta = play_frames.iloc[0]
        yd_str = f"{meta['yardline_side']} {int(meta['yardline_number'])}"
        cov_str = str(meta['team_coverage_type']).replace('_', ' ').title()
        
        context_text = f"{meta['down']} & {meta['yards_to_go']} | {yd_str}\n{cov_str}"
        at_context = AnchoredText(context_text, loc='upper left', prop=dict(size=10, fontweight='bold'), frameon=True)
        at_context.patch.set_boxstyle("round,pad=0.3")
        at_context.patch.set_alpha(0.8)
        ax.add_artist(at_context)

        # Metric Box
        sign = "+" if vis_score > 0 else ""
        metric_text = f"Start: {start_dist:.1f} yds\nVIS: {sign}{vis_score:.1f} yds"
        at_metric = AnchoredText(metric_text, loc='upper center', prop=dict(size=12, fontweight='bold', color='#2c3e50'), frameon=True)
        at_metric.patch.set_boxstyle("round,pad=0.3")
        at_metric.patch.set_edgecolor('#2ecc71')
        at_metric.patch.set_linewidth(2)
        ax.add_artist(at_metric)

        # Timer
        timer_text = ax.text(118, 50, '', ha='right', fontsize=14, fontweight='bold', color='black',
                             bbox=dict(facecolor='white', edgecolor='black', pad=3))

        # 5. Plot Objects
        scat_others = ax.scatter([], [], c='grey', alpha=0.3, s=40, zorder=2)
        scat_target = ax.scatter([], [], c='#e74c3c', s=150, marker='s', edgecolors='white', zorder=5, label='Target')
        scat_eraser = ax.scatter([], [], c='#2ecc71', s=250, marker='*', edgecolors='white', zorder=6, label='Eraser')
        scat_context = ax.scatter([], [], c='#3498db', s=150, marker='^', edgecolors='white', zorder=5, label='Context Def')
        scat_ball = ax.scatter([], [], c='#d35400', s=180, marker='o', edgecolors='white', linewidth=1.5, zorder=10, label='Ball')
        
        line_void, = ax.plot([], [], color='black', linestyle='--', alpha=0.7, zorder=4)
        text_void = ax.text(0, 0, '', ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        
        ax.legend(loc='lower right', fontsize=9, framealpha=0.9)

        # 6. Update Loop
        def update(frame_num):
            time_sec = (frame_num - start_frame) * 0.1
            timer_text.set_text(f"T + {time_sec:.1f}s")

            snap = play_frames[play_frames['frame_id'] == frame_num]
            
            if frame_num in ball_pos_dict:
                scat_ball.set_offsets([ball_pos_dict[frame_num]])
            
            eraser = snap[snap['nfl_id'] == eraser_id]
            target = snap[snap['nfl_id'] == target_id]
            context = snap[snap['nfl_id'] == context_id] if context_id else pd.DataFrame()
            others = snap[~snap['nfl_id'].isin([eraser_id, target_id, context_id])]
            
            scat_others.set_offsets(others[['x', 'y']].values)
            if not target.empty: scat_target.set_offsets(target[['x', 'y']].values)
            
            if not context.empty and context_id != eraser_id: 
                scat_context.set_offsets(context[['x', 'y']].values)
            else: 
                scat_context.set_offsets(np.empty((0, 2)))
                
            if not eraser.empty:
                scat_eraser.set_offsets(eraser[['x', 'y']].values)
                if not target.empty:
                    ex, ey = eraser.iloc[0]['x'], eraser.iloc[0]['y']
                    tx, ty = target.iloc[0]['x'], target.iloc[0]['y']
                    line_void.set_data([ex, tx], [ey, ty])
                    dist = np.sqrt((ex-tx)**2 + (ey-ty)**2)
                    text_void.set_position(((ex+tx)/2, (ey+ty)/2))
                    text_void.set_text(f"{dist:.1f} yds")
            
            return scat_others, scat_target, scat_eraser, scat_context, scat_ball, line_void, text_void, timer_text

        # 7. Render
        print("      ... Rendering frames ...")
        # Now unique_frames is properly defined
        ani = animation.FuncAnimation(fig, update, frames=unique_frames, interval=100, blit=True)
        
        save_path = os.path.join(self.output_dir, filename)
        ani.save(save_path, writer='pillow', fps=10)
        print(f"   -> Saved Video: {save_path}")
        plt.close()