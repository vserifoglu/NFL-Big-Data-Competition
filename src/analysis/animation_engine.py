import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
from matplotlib.offsetbox import AnchoredText
from matplotlib.patches import FancyBboxPatch, Circle, Ellipse
import os

class AnimationEngine:
    def __init__(self, summary_path, frames_path, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"   [Animator] Loading Data...")
        self.summary_df = pd.read_csv(summary_path)
        
        # ADDED: 'defensive_team', 'yardline_number', 'yardline_side', 'team_coverage_type', 'phase'
        cols = [
            'game_id', 'play_id', 'nfl_id', 'frame_id', 'x', 'y', 'phase',
            'player_role', 'player_name', 'ball_land_x', 'ball_land_y',
            'down', 'yards_to_go', 'pass_result', 'possession_team', 'defensive_team',
            'yardline_number', 'yardline_side', 'team_coverage_type', 'yards_gained',
            's_derived'  # Speed for display
        ]
        
        self.frames_df = pd.read_csv(frames_path, usecols=cols)

    def _draw_field(self, ax):
        """Sets up the static NFL-style field background."""
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 53.3)
        ax.set_facecolor('#2e7d32')  # NFL Green
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Field outline
        field_rect = patches.Rectangle((10, 0), 100, 53.3, linewidth=2, 
                                         edgecolor='white', facecolor='#3d8b40', zorder=0)
        ax.add_patch(field_rect)
        
        # End Zones
        ez_left = patches.Rectangle((0, 0), 10, 53.3, facecolor='#1b5e20', edgecolor='white', linewidth=2, zorder=0)
        ez_right = patches.Rectangle((110, 0), 10, 53.3, facecolor='#1b5e20', edgecolor='white', linewidth=2, zorder=0)
        ax.add_patch(ez_left)
        ax.add_patch(ez_right)
        ax.text(5, 26.65, 'END\nZONE', ha='center', va='center', fontsize=8, 
                fontweight='bold', color='white', alpha=0.6, rotation=90)
        ax.text(115, 26.65, 'END\nZONE', ha='center', va='center', fontsize=8, 
                fontweight='bold', color='white', alpha=0.6, rotation=270)
        
        # Yard lines (every 5 yards, bold every 10)
        for x in range(10, 111, 5):
            lw = 2 if x % 10 == 0 else 0.5
            alpha = 1.0 if x % 10 == 0 else 0.5
            ax.axvline(x, color='white', linestyle='-', linewidth=lw, alpha=alpha, zorder=1)
        
        # Yard numbers
        for x in range(20, 110, 10):
            num = (x - 10) if x <= 60 else (110 - x)
            # Top numbers
            ax.text(x, 48, str(num), color='white', ha='center', va='center', 
                    fontsize=12, fontweight='bold', alpha=0.8)
            # Bottom numbers
            ax.text(x, 5, str(num), color='white', ha='center', va='center', 
                    fontsize=12, fontweight='bold', alpha=0.8)
        
        # Hash marks (NFL style)
        hash_y_top = 39.3  # 70 feet 9 inches from sideline
        hash_y_bot = 14.0
        for x in range(10, 111, 1):
            ax.plot([x, x], [hash_y_top, hash_y_top + 0.5], color='white', linewidth=0.5, alpha=0.6, zorder=1)
            ax.plot([x, x], [hash_y_bot - 0.5, hash_y_bot], color='white', linewidth=0.5, alpha=0.6, zorder=1)

    def generate_video(self, game_id, play_id, eraser_id, filename="play_animation.mp4"):
        print(f"   [Animator] Rendering video for {game_id}-{play_id}...")
        
        # 1. Get Play Data
        play_frames = self.frames_df[
            (self.frames_df['game_id'] == game_id) & 
            (self.frames_df['play_id'] == play_id)
        ].sort_values('frame_id')
        
        if play_frames.empty: return

        # 2. Actors & Context
        target_row = play_frames[play_frames['player_role'] == 'Targeted Receiver']
        target_id = target_row['nfl_id'].iloc[0]
        target_name = target_row['player_name'].iloc[0] if 'player_name' in target_row.columns else "WR"
        
        # Get QB info
        qb_row = play_frames[play_frames['player_role'] == 'Passer']
        qb_id = qb_row['nfl_id'].iloc[0] if not qb_row.empty else None
        qb_name = qb_row['player_name'].iloc[0] if not qb_row.empty and 'player_name' in qb_row.columns else "QB"
        
        summary_row = self.summary_df[
            (self.summary_df['game_id'] == game_id) & 
            (self.summary_df['play_id'] == play_id)
        ]
        
        # Get Scores & Names
        vis_score = 0.0
        start_dist = 0.0
        end_dist = 0.0
        context_id = None
        eraser_name = "DEF"
        context_name = "DEF"
        
        if not summary_row.empty:
            eraser_row = summary_row[summary_row['nfl_id'] == eraser_id]
            if not eraser_row.empty:
                vis_score = eraser_row.iloc[0]['vis_score']
                start_dist = eraser_row.iloc[0]['p_dist_at_throw']
                end_dist = eraser_row.iloc[0].get('p_dist_at_arrival', start_dist - vis_score)
                if 'player_name' in eraser_row.columns:
                    eraser_name = eraser_row.iloc[0]['player_name']
            # Get context defender (closest at throw)
            context_idx = summary_row['p_dist_at_throw'].idxmin()
            context_id = summary_row.loc[context_idx]['nfl_id']
            if 'player_name' in summary_row.columns:
                context_name = summary_row.loc[context_idx]['player_name']

        # Get play metadata
        meta = play_frames.iloc[0]
        pass_result = meta.get('pass_result', 'Unknown')
        yards_gained = meta.get('yards_gained', 0)
        
        # 3. BALL TRAJECTORY LOGIC
        unique_frames = sorted(play_frames['frame_id'].unique())
        start_frame = play_frames['frame_id'].min()
        end_frame = play_frames['frame_id'].max()
        
        # Identify the throw frame (first frame of post_throw phase)
        if 'phase' in play_frames.columns:
            post_throw_data = play_frames[play_frames['phase'] == 'post_throw']
            if not post_throw_data.empty:
                throw_frame = post_throw_data['frame_id'].min()
            else:
                throw_frame = start_frame
        else:
            throw_frame = start_frame
        
        # Get post-throw frames for ball interpolation
        post_throw_frames = sorted([f for f in unique_frames if f >= throw_frame])
        post_throw_steps = len(post_throw_frames)
        
        # Ball landing position
        bx_end, by_end = play_frames.iloc[0]['ball_land_x'], play_frames.iloc[0]['ball_land_y']
        
        # Get QB position at throw frame
        passer_at_throw = play_frames[
            (play_frames['frame_id'] == throw_frame) & 
            (play_frames['player_role'] == 'Passer')
        ]
        if not passer_at_throw.empty:
            bx_throw, by_throw = passer_at_throw.iloc[0]['x'], passer_at_throw.iloc[0]['y']
        else:
            passer_early = play_frames[play_frames['player_role'] == 'Passer'].sort_values('frame_id')
            if not passer_early.empty:
                bx_throw, by_throw = passer_early.iloc[0]['x'], passer_early.iloc[0]['y']
            else:
                bx_throw, by_throw = bx_end - 15, 26.65
        
        # Interpolate ball trajectory ONLY for post-throw frames
        if post_throw_steps > 1:
            ball_x_flight = np.linspace(bx_throw, bx_end, post_throw_steps)
            ball_y_flight = np.linspace(by_throw, by_end, post_throw_steps)
        else:
            ball_x_flight = [bx_end]
            ball_y_flight = [by_end]
        
        # Build ball position dictionary
        ball_pos_dict = {}
        for f in unique_frames:
            if f < throw_frame:
                passer_at_f = play_frames[
                    (play_frames['frame_id'] == f) & 
                    (play_frames['player_role'] == 'Passer')
                ]
                if not passer_at_f.empty:
                    ball_pos_dict[f] = (passer_at_f.iloc[0]['x'], passer_at_f.iloc[0]['y'])
                else:
                    ball_pos_dict[f] = (bx_throw, by_throw)
            else:
                idx = post_throw_frames.index(f)
                ball_pos_dict[f] = (ball_x_flight[idx], ball_y_flight[idx])

        # ===== BUILD PLAYER POSITION CACHE =====
        # Cache last known position for each player to handle "ghost" players
        # who disappear in post_throw frames (>8yds from catch point in output data)
        all_player_ids = play_frames['nfl_id'].unique()
        player_cache = {}  # {nfl_id: {'x': x, 'y': y, 'role': role, 's_derived': speed}}
        
        # Pre-build cache by iterating through frames in order
        player_positions_by_frame = {}
        for f in unique_frames:
            snap = play_frames[play_frames['frame_id'] == f]
            frame_positions = {}
            
            for pid in all_player_ids:
                player_row = snap[snap['nfl_id'] == pid]
                if not player_row.empty:
                    # Update cache with current position
                    player_cache[pid] = {
                        'x': player_row.iloc[0]['x'],
                        'y': player_row.iloc[0]['y'],
                        'role': player_row.iloc[0]['player_role'],
                        's_derived': player_row.iloc[0].get('s_derived', 0)
                    }
                # Use cached position (current or last known)
                if pid in player_cache:
                    frame_positions[pid] = player_cache[pid].copy()
            
            player_positions_by_frame[f] = frame_positions

        # 4. Setup Figure
        fig, ax = plt.subplots(figsize=(14, 7))
        self._draw_field(ax)
        
        # ===== INFO PANELS =====
        
        # Context Box (Top Left) - Down & Distance, Coverage
        yd_str = f"{meta['yardline_side']} {int(meta['yardline_number'])}"
        cov_str = str(meta['team_coverage_type']).replace('_', ' ').title()
        context_text = f"{int(meta['down'])} & {int(meta['yards_to_go'])} | {yd_str}\n{cov_str}"
        at_context = AnchoredText(context_text, loc='upper left', 
                                   prop=dict(size=11, fontweight='bold', family='monospace'), frameon=True)
        at_context.patch.set_boxstyle("round,pad=0.4")
        at_context.patch.set_facecolor('#1a1a2e')
        at_context.patch.set_edgecolor('white')
        at_context.patch.set_alpha(0.95)
        for txt in at_context.txt.get_children():
            txt.set_color('white')
        ax.add_artist(at_context)

        # Metric Box (Top Center) - VIS Score
        sign = "+" if vis_score > 0 else ""
        metric_text = f"START: {start_dist:.1f} yds\nVIS: {sign}{vis_score:.1f} yds"
        at_metric = AnchoredText(metric_text, loc='upper center', 
                                  prop=dict(size=12, fontweight='bold', family='monospace'), frameon=True)
        at_metric.patch.set_boxstyle("round,pad=0.4")
        at_metric.patch.set_facecolor('#16213e')
        at_metric.patch.set_edgecolor('#00ff88' if vis_score > 0 else '#ff4444')
        at_metric.patch.set_linewidth(3)
        for txt in at_metric.txt.get_children():
            txt.set_color('#00ff88' if vis_score > 0 else '#ff4444')
        ax.add_artist(at_metric)

        # Outcome Badge (Top Right area) - shows COMPLETE/INCOMPLETE
        outcome_color = '#27ae60' if pass_result == 'C' else '#c0392b'
        outcome_text = 'COMPLETE ✓' if pass_result == 'C' else 'INCOMPLETE ✗'
        outcome_label = ax.text(118, 50, outcome_text, ha='right', va='top', fontsize=11, 
                                 fontweight='bold', color='white',
                                 bbox=dict(facecolor=outcome_color, edgecolor='white', 
                                          pad=6, boxstyle='round,pad=0.4'))

        # Timer (Right side)
        timer_text = ax.text(118, 42, '', ha='right', fontsize=13, fontweight='bold', color='white',
                             bbox=dict(facecolor='#2c3e50', edgecolor='white', pad=4, boxstyle='round,pad=0.3'))
        
        # Phase Label
        phase_label = ax.text(118, 35, '', ha='right', fontsize=11, fontweight='bold', color='white',
                              bbox=dict(facecolor='#3498db', edgecolor='white', pad=5, boxstyle='round,pad=0.3'))
        
        # Speed indicator for eraser
        speed_label = ax.text(118, 28, '', ha='right', fontsize=10, fontweight='bold', color='white',
                              bbox=dict(facecolor='#8e44ad', edgecolor='white', pad=4, boxstyle='round,pad=0.3'))

        # ===== STATIC MARKERS =====
        
        # Ball Landing Spot (X marker - visible entire animation)
        ax.scatter([bx_end], [by_end], c='#ffff00', s=400, marker='X', 
                   edgecolors='#ff6600', linewidths=3, zorder=2, alpha=0.9)
        ax.text(bx_end, by_end - 2.5, 'TARGET', ha='center', va='top', fontsize=7,
                fontweight='bold', color='#ffff00', alpha=0.9)
        
        # ===== PLAYER MARKERS =====
        
        # Other defenders (blue circles)
        scat_def_others = ax.scatter([], [], c='#2980b9', s=200, marker='o', 
                                      edgecolors='white', linewidths=2, zorder=3, alpha=0.7)
        
        # Other offense (red circles)  
        scat_off_others = ax.scatter([], [], c='#c0392b', s=200, marker='o',
                                      edgecolors='white', linewidths=2, zorder=3, alpha=0.7)
        
        # QB (purple diamond - distinctive)
        scat_qb = ax.scatter([], [], c='#9b59b6', s=350, marker='D', 
                              edgecolors='white', linewidths=3, zorder=5)
        qb_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                           fontweight='bold', color='white',
                           bbox=dict(facecolor='#9b59b6', edgecolor='none', pad=2, alpha=0.9))
        
        # Target Receiver (orange star - stands out)
        scat_target = ax.scatter([], [], c='#ff6b35', s=450, marker='*', 
                                  edgecolors='white', linewidths=2, zorder=6)
        target_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8, 
                               fontweight='bold', color='white',
                               bbox=dict(facecolor='#ff6b35', edgecolor='none', pad=2, alpha=0.9))
        
        # Eraser (bright green, largest circle)
        scat_eraser = ax.scatter([], [], c='#00ff88', s=400, marker='o',
                                  edgecolors='#004d40', linewidths=3, zorder=7)
        eraser_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                               fontweight='bold', color='black',
                               bbox=dict(facecolor='#00ff88', edgecolor='none', pad=2, alpha=0.9))
        
        # Context Defender (cyan triangle - closest at throw)
        scat_context = ax.scatter([], [], c='#00bcd4', s=300, marker='^',
                                   edgecolors='white', linewidths=2, zorder=5)
        context_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                                fontweight='bold', color='white',
                                bbox=dict(facecolor='#00bcd4', edgecolor='none', pad=2, alpha=0.9))
        
        # Ball (brown pentagon - football shape)
        scat_ball = ax.scatter([], [], c='#8B4513', s=200, marker='p',
                                edgecolors='white', linewidths=2, zorder=10)
        
        # Void line (dashed line between eraser and target)
        line_void, = ax.plot([], [], color='#ffff00', linestyle='--', linewidth=2, alpha=0.8, zorder=4)
        text_void = ax.text(0, 0, '', ha='center', va='center', fontsize=10, fontweight='bold', 
                            color='black', bbox=dict(facecolor='#ffff00', alpha=0.9, edgecolor='none', pad=3))

        # ===== LEGEND =====
        legend_elements = [
            plt.scatter([], [], c='#00ff88', s=150, marker='o', edgecolors='#004d40', linewidths=2, label='Eraser'),
            plt.scatter([], [], c='#ff6b35', s=150, marker='*', edgecolors='white', linewidths=2, label='Target WR'),
            plt.scatter([], [], c='#00bcd4', s=100, marker='^', edgecolors='white', linewidths=2, label='Nearest Def'),
            plt.scatter([], [], c='#9b59b6', s=100, marker='D', edgecolors='white', linewidths=2, label='QB'),
            plt.scatter([], [], c='#8B4513', s=80, marker='p', edgecolors='white', linewidths=2, label='Ball'),
            plt.scatter([], [], c='#ffff00', s=100, marker='X', edgecolors='#ff6600', linewidths=2, label='Ball Target'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=8, 
                  framealpha=0.95, facecolor='#1a1a2e', edgecolor='white', labelcolor='white',
                  ncol=2)

        # 6. Update Loop
        def update(frame_num):
            # Timer relative to throw frame
            time_sec = (frame_num - throw_frame) * 0.1
            if frame_num < throw_frame:
                timer_text.set_text(f"T {time_sec:.1f}s")
                phase_label.set_text("⏳ PRE THROW")
                phase_label.get_bbox_patch().set_facecolor('#3498db')
            else:
                timer_text.set_text(f"T +{time_sec:.1f}s")
                phase_label.set_text("🏈 BALL IN AIR")
                phase_label.get_bbox_patch().set_facecolor('#e74c3c')

            # Get cached positions for this frame (includes frozen players)
            frame_positions = player_positions_by_frame.get(frame_num, {})
            
            # Ball position
            if frame_num in ball_pos_dict:
                scat_ball.set_offsets([ball_pos_dict[frame_num]])
            
            # Build position lists from cache
            def_others_pos = []
            off_others_pos = []
            
            excluded_ids = {eraser_id, target_id, context_id}
            if qb_id:
                excluded_ids.add(qb_id)
            
            for pid, pos in frame_positions.items():
                if pid in excluded_ids:
                    continue
                role = pos.get('role', '')
                if role in ['Coverage Defender', 'Pass Rusher', 'Defender']:
                    def_others_pos.append([pos['x'], pos['y']])
                elif role not in ['Passer']:
                    off_others_pos.append([pos['x'], pos['y']])
            
            scat_def_others.set_offsets(np.array(def_others_pos) if def_others_pos else np.empty((0, 2)))
            scat_off_others.set_offsets(np.array(off_others_pos) if off_others_pos else np.empty((0, 2)))
            
            # QB (from cache)
            if qb_id and qb_id in frame_positions:
                qb_pos = frame_positions[qb_id]
                qx, qy = qb_pos['x'], qb_pos['y']
                scat_qb.set_offsets([[qx, qy]])
                qb_label.set_position((qx, qy + 2.5))
                q_name = str(qb_name).split()[-1][:8] if qb_name else "QB"
                qb_label.set_text(q_name)
            else:
                scat_qb.set_offsets(np.empty((0, 2)))
            
            # Target (from cache)
            if target_id in frame_positions:
                target_pos = frame_positions[target_id]
                tx, ty = target_pos['x'], target_pos['y']
                scat_target.set_offsets([[tx, ty]])
                target_label.set_position((tx, ty + 2.5))
                t_name = str(target_name).split()[-1][:8] if target_name else "WR"
                target_label.set_text(t_name)
            
            # Context defender (from cache, with name label)
            if context_id and context_id in frame_positions and context_id != eraser_id: 
                context_pos = frame_positions[context_id]
                cx, cy = context_pos['x'], context_pos['y']
                scat_context.set_offsets([[cx, cy]])
                context_label.set_position((cx, cy + 2.5))
                c_name = str(context_name).split()[-1][:8] if context_name else "DEF"
                context_label.set_text(c_name)
            else: 
                scat_context.set_offsets(np.empty((0, 2)))
                context_label.set_text('')
                
            # Eraser (from cache)
            if eraser_id in frame_positions:
                eraser_pos = frame_positions[eraser_id]
                ex, ey = eraser_pos['x'], eraser_pos['y']
                scat_eraser.set_offsets([[ex, ey]])
                eraser_label.set_position((ex, ey + 2.5))
                e_name = str(eraser_name).split()[-1][:8] if eraser_name else "DEF"
                eraser_label.set_text(e_name)
                
                # Speed display
                speed_yps = eraser_pos.get('s_derived', 0)
                speed_mph = speed_yps * 2.045 if pd.notna(speed_yps) else 0
                speed_label.set_text(f"⚡ {speed_mph:.1f} mph")
                
                # Void line
                if target_id in frame_positions:
                    line_void.set_data([ex, tx], [ey, ty])
                    dist = np.sqrt((ex-tx)**2 + (ey-ty)**2)
                    text_void.set_position(((ex+tx)/2, (ey+ty)/2))
                    text_void.set_text(f"{dist:.1f} yds")
            
            return (scat_def_others, scat_off_others, scat_target, scat_eraser, scat_context, 
                    scat_ball, scat_qb, line_void, text_void, timer_text, phase_label, speed_label,
                    target_label, eraser_label, qb_label, context_label)

        # 7. Render
        print("      ... Rendering frames ...")
        ani = animation.FuncAnimation(fig, update, frames=unique_frames, interval=100, blit=True)
        
        save_path = os.path.join(self.output_dir, filename)
        ani.save(save_path, writer='pillow', fps=10)
        print(f"   -> Saved Video: {save_path}")
        plt.close()