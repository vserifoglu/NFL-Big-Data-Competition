import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from dataclasses import dataclass

# ==========================================
# CONFIGURATION
# ==========================================
@dataclass
class Config:
    RESULTS_PATH: str = "data/processed/clv_data_export.csv"
    CACHE_PATH: str = "data/processed/animation_cache.csv"
    
    # --- VISUAL IDENTITY SYSTEM ---
    # Updated colors to pop against a green field
    COLOR_MAP = {
        'Football': '#8B4513',          # Brown
        'Quarterback': '#FFD700',       # Gold (bright)
        'Target (Receiver)': '#00FF00', # Neon Green (High Contrast)
        'Decoy (Gravity)': '#00FFFF',   # Cyan (High Contrast)
        
        'VICTIM (Leaker)': '#FF00FF',   # Magenta (High Contrast)
        'Eraser (Helper)': '#F0E68C',   # Khaki/Light Yellow (Distinct from QB)
        
        'Defense': '#FF4444',           # Bright Red
        'Offense': '#4444FF',           # Bright Blue
        'Ghost': '#E0E0E0'              # Light Gray
    }
    
    SIZE_MAP = {
        'Football': 7, 
        'Quarterback': 14, 
        'Target (Receiver)': 14, 
        'Decoy (Gravity)': 14, 
        'VICTIM (Leaker)': 18,
        'Eraser (Helper)': 18,
        'Defense': 11, 
        'Offense': 11,
        'Ghost': 8
    }
    
    SYMBOL_MAP = {
        'Football': 'circle', 
        'Quarterback': 'pentagon',
        'Target (Receiver)': 'star',
        'Decoy (Gravity)': 'triangle-up',
        
        'VICTIM (Leaker)': 'x',
        'Eraser (Helper)': 'shield',      # Changed to shield for "protector" vibe
        
        'Defense': 'circle', 
        'Offense': 'circle',
        'Ghost': 'cross-thin'
    }

# ==========================================
# DATA SERVICE (Unchanged from previous version)
# ==========================================
class DataService:
    def __init__(self):
        self.results = self._load_csv(Config.RESULTS_PATH)
        self.cache = self._load_csv(Config.CACHE_PATH)
        self._ensure_types()

    def _load_csv(self, path):
        if os.path.exists(path):
            return pd.read_csv(path)
        return pd.DataFrame()

    def _ensure_types(self):
        if not self.cache.empty and 'nfl_id' in self.cache.columns:
            self.cache['nfl_id'] = pd.to_numeric(self.cache['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)

    def get_summary_metrics(self):
        if self.results.empty: return None
        avg_void = self.results['clv'].mean()
        high_leak = self.results[self.results['clv'] > 8.0]
        low_leak = self.results[self.results['leak_cause'] == 'Tactical Rotation']
        
        hl_comp = (high_leak['pass_result'] == 'C').mean() if not high_leak.empty else 0
        ll_comp = (low_leak['pass_result'] == 'C').mean() if not low_leak.empty else 0
        
        return {
            'avg_void': avg_void,
            'high_leak_comp': hl_comp,
            'low_leak_comp': ll_comp,
            'delta': (hl_comp - ll_comp) * 100
        }

    def get_play_catalog(self):
        if self.cache.empty or self.results.empty: return pd.DataFrame()
        available = self.cache[['game_id', 'play_id', 'highlight_type', 'clv_score']].drop_duplicates()
        
        catalog = available.merge(
            self.results[['game_id', 'play_id', 'qb_name', 'player_name', 'decoy_name', 'eraser_name', 'leak_cause', 'pass_result', 'epa']],
            on=['game_id', 'play_id'],
            how='left'
        )

        def generate_story(row):
            qb = str(row['qb_name']).split()[-1]
            vic = str(row['player_name']).split()[-1]
            cause = str(row['leak_cause'])
            
            if cause == 'Tactical Rotation': 
                saver = str(row['eraser_name']).split()[-1] if pd.notna(row['eraser_name']) else "Safety"
                return f"🛡️ {vic} bit, but {saver} SAVED it"
            if cause == 'Puppeteer': return f"👀 {qb} froze {vic}"
            if cause == 'Gravity': return f"🧲 Scheme pulled {vic}"
            return f"⚠️ {vic} blown coverage"

        catalog['The Story'] = catalog.apply(generate_story, axis=1)
        catalog['Score'] = catalog['clv_score'].round(2)
        catalog['Result'] = catalog['pass_result']
        return catalog.sort_values('Score', ascending=False)

    def get_rotation_stats(self):
        if 'eraser_name' not in self.results.columns: return pd.DataFrame()
        df = self.results[self.results['leak_cause'] == 'Tactical Rotation'].copy()
        df = df.dropna(subset=['eraser_name'])
        
        stats = df.groupby('eraser_name').agg(
            Rotations_Made=('play_id', 'count'),
            Total_Eraser_Score=('eraser_score', 'sum'),
            Avg_Eraser_Score=('eraser_score', 'mean')
        ).reset_index()
        
        stats = stats.rename(columns={'eraser_name': 'player_name'})
        stats['player_position'] = 'DB' 
        
        bests = df.sort_values('eraser_score', ascending=False).drop_duplicates('eraser_name')[['eraser_name', 'game_id', 'play_id']]
        bests = bests.rename(columns={'eraser_name': 'player_name'})
        return stats.merge(bests, on='player_name').sort_values('Total_Eraser_Score', ascending=False)

    def get_puppeteer_stats(self):
        df = self.results[self.results['leak_cause'] == 'Puppeteer'].copy()
        stats = df.groupby('qb_name').agg(Total_Void_Yards=('clv', 'sum'), Avg_Void=('clv', 'mean'), Plays=('clv', 'count')).reset_index()
        bests = df.sort_values('clv', ascending=False).drop_duplicates('qb_name')[['qb_name', 'game_id', 'play_id', 'pass_result']]
        return stats.merge(bests, on='qb_name').sort_values('Total_Void_Yards', ascending=False)

    def get_gravity_stats(self):
        if 'decoy_name' not in self.results.columns: return pd.DataFrame()
        df = self.results[self.results['leak_cause'] == 'Gravity'].copy()
        stats = df.groupby('decoy_name').agg(Total_EPA_Generated=('epa', 'sum'), Avg_Void=('clv', 'mean'), Plays=('clv', 'count')).reset_index()
        bests = df.sort_values('clv', ascending=False).drop_duplicates('decoy_name')[['decoy_name', 'game_id', 'play_id', 'pass_result']]
        return stats.merge(bests, on='decoy_name').sort_values('Total_EPA_Generated', ascending=False)

    def get_victim_stats(self):
        stats = self.results.groupby(['player_name', 'player_position']).agg(Total_Void_Allowed=('clv', 'sum'), Times_Fooled=('clv', 'count'), Avg_Exposure=('clv', 'mean')).reset_index()
        worsts = self.results.sort_values('clv', ascending=False).drop_duplicates('player_name')[['player_name', 'game_id', 'play_id', 'nfl_id', 'pass_result']]
        return stats.merge(worsts, on='player_name').sort_values('Total_Void_Allowed', ascending=False)
    
    def get_league_scatter_data(self):
        df = self.results[self.results['leak_cause'] == 'Puppeteer'].copy()
        stats = df.groupby('qb_name').agg(Total_Void_Yards=('clv', 'sum'), EPA_Per_Play=('epa', 'mean'), Plays=('clv', 'count')).reset_index()
        return stats[stats['Plays'] >= 10]
        
    def get_completion_by_void_bucket(self):
        df = self.results.copy()
        df['Void_Bucket'] = pd.qcut(df['clv'], 4, labels=["Tight", "Small Gap", "Open", "Wide Open"], duplicates='drop')
        df['is_complete'] = (df['pass_result'] == 'C').astype(int)
        stats = df.groupby('Void_Bucket')['is_complete'].mean().reset_index()
        stats['Completion_Rate'] = stats['is_complete'] * 100
        return stats

    def prepare_animation_frame(self, game_id, play_id, victim_id=-1, decoy_name=None, eraser_name=None):
        play_data = self.cache[(self.cache['game_id'] == game_id) & (self.cache['play_id'] == play_id)].copy()
        if play_data.empty: return None, None, None

        cols = play_data.columns
        name_col = 'player_name' if 'player_name' in cols else 'displayName'
        if name_col not in cols: name_col = 'nfl_id'
        id_col = 'nfl_id'

        if 'phase' in play_data.columns:
            post_frames = sorted(play_data[play_data['phase'] == 'post_throw']['frame_id'].unique())
            if post_frames:
                pre_ids = set(play_data[play_data['phase'] == 'pre_throw'][id_col].unique())
                post_ids = set(play_data[play_data['phase'] == 'post_throw'][id_col].unique())
                dropout_ids = list(pre_ids - post_ids)
                
                if dropout_ids:
                    last_known = play_data[play_data[id_col].isin(dropout_ids)].sort_values('frame_id').groupby(id_col).tail(1)
                    ghosts = []
                    for _, row in last_known.iterrows():
                        for f in post_frames:
                            g = row.copy()
                            g['frame_id'] = f
                            g['s'] = 0 
                            ghosts.append(g)
                    if ghosts:
                        play_data = pd.concat([play_data, pd.DataFrame(ghosts)], ignore_index=True)

        play_data = play_data.sort_values(['frame_id', id_col])
        play_data = self._apply_visual_roles(play_data, name_col, id_col, victim_id, decoy_name, eraser_name)
        return play_data, name_col, id_col

    def _apply_visual_roles(self, df, name_col, id_col, victim_id, decoy_name, eraser_name):
        tgt_id = -1
        if 'target_id' in df.columns:
            ts = df['target_id'].dropna().unique()
            if len(ts) > 0: tgt_id = int(ts[0])

        s_vic, s_tgt = str(victim_id), str(tgt_id)
        clean_decoy = str(decoy_name).lower().strip() if decoy_name else None
        clean_eraser = str(eraser_name).lower().strip() if eraser_name else None

        def get_role(row):
            pid = str(row[id_col])
            pname = str(row[name_col]).lower().strip()
            
            if 'football' in pname or pid == '999999': return 'Football', ''
            if clean_eraser and clean_eraser in pname: return 'Eraser (Helper)', f"🛡️ SAVIOR: {row[name_col]}"
            if clean_decoy and clean_decoy in pname: return 'Decoy (Gravity)', f"🧲 GRAVITY: {row[name_col]}"
            if pid == s_tgt: return 'Target (Receiver)', f"🎯 TARGET: {row[name_col]}"
            if pid == s_vic: return 'VICTIM (Leaker)', f"⚠️ VICTIM: {row[name_col]}"
            
            pos = str(row.get('player_position', '')) 
            if pos == 'nan': pos = str(row.get('position', ''))
            role = str(row.get('player_role', ''))
            if pos == 'QB' or role == 'Passer': return 'Quarterback', f"QB: {row[name_col]}"
            
            side = str(row.get('player_side', '')).lower()
            return ('Defense', '') if side == 'defense' else ('Offense', '')

        roles = df.apply(get_role, axis=1)
        df['visual_role'] = [r[0] for r in roles]
        df['visual_label'] = [r[1] for r in roles]
        df['visual_size'] = df['visual_role'].map(Config.SIZE_MAP).fillna(8)
        return df

# ==========================================
# VISUALIZATION SERVICE (UPDATED FOR FIELD ART)
# ==========================================
class VizService:
    @staticmethod
    def create_field_animation(df, game_id, play_id, name_col, id_col):
        # Base Scatter Plot
        fig = px.scatter(
            df, x='x', y='y', animation_frame='frame_id', animation_group=id_col,
            color='visual_role', color_discrete_map=Config.COLOR_MAP,
            symbol='visual_role', symbol_map=Config.SYMBOL_MAP,
            size='visual_size', size_max=20, # Increased slightly
            text='visual_label', hover_name=name_col,
            range_x=[0, 120], range_y=[0, 53.3],
            title=f"Game {game_id} | Play {play_id}"
        )
        
        # Add Catch Point Star
        if 'ball_land_x' in df.columns:
            bx, by = df['ball_land_x'].iloc[0], df['ball_land_y'].iloc[0]
            fig.add_trace(go.Scatter(
                x=[bx], y=[by], mode='markers', 
                marker=dict(symbol='star-open', size=22, color='gold', line=dict(width=3)),
                name='Catch Point'
            ))

        # --- ADD FIELD ART ---
        VizService._add_nfl_field_layout(fig)
            
        fig.update_traces(textposition='top center', textfont=dict(color='white')) # White text for contrast
        
        # Animation Speed Settings
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 110 # Slightly slower for clarity
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 50 # Smoother transition

        return fig

    @staticmethod
    def _add_nfl_field_layout(fig):
        """Draws the NFL field using shapes and annotations."""
        # 1. Field Background (Grass)
        fig.update_layout(
            plot_bgcolor='#567D46', # Turf Green
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
            height=600,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="right", x=1,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            ),
            title=dict(font=dict(color="white"))
        )

        shapes = []
        annotations = []

        # 2. Endzones (Slightly different color)
        shapes.append(dict(type="rect", x0=0, y0=0, x1=10, y1=53.3, line_width=0, fillcolor="#436137", layer="below"))
        shapes.append(dict(type="rect", x0=110, y0=0, x1=120, y1=53.3, line_width=0, fillcolor="#436137", layer="below"))

        # 3. Yard Lines & Markings
        line_color = "rgba(255, 255, 255, 0.8)"
        
        for x in range(10, 111, 5):
            # Line width: Thicker for goal lines and 50
            width = 3 if x in [10, 60, 110] else 1
            shapes.append(dict(type="line", x0=x, y0=0, x1=x, y1=53.3, line=dict(color=line_color, width=width), layer="below"))
            
            # Yard Numbers (Skip goal lines)
            if x in [20, 30, 40, 50, 60, 70, 80, 90, 100]:
                label = str(50 - abs(x - 60)) if x != 60 else "50"
                # Bottom numbers
                annotations.append(dict(x=x, y=4, text=label, showarrow=False, font=dict(color=line_color, size=16, family="Arial Black")))
                # Top numbers
                annotations.append(dict(x=x, y=53.3-4, text=label, showarrow=False, font=dict(color=line_color, size=16, family="Arial Black")))

        # 4. Hash Marks (Simplified: at 5-yard intervals to keep animation fast)
        # NFL Hashes are ~23.6 yards from sideline
        hash_bot = 23.6
        hash_top = 53.3 - 23.6
        for x in range(11, 110):
             # Draw hashes every yard
             shapes.append(dict(type="line", x0=x, y0=hash_bot-0.3, x1=x, y1=hash_bot+0.3, line=dict(color=line_color, width=1), layer="below"))
             shapes.append(dict(type="line", x0=x, y0=hash_top-0.3, x1=x, y1=hash_top+0.3, line=dict(color=line_color, width=1), layer="below"))

        fig.update_layout(shapes=shapes, annotations=annotations)