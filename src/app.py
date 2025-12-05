import streamlit as st
import pandas as pd
import plotly.express as px
from backend import DataService, VizService

# ==========================================
# SETUP
# ==========================================
st.set_page_config(
    page_title="The Anticipation Void",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #ff4b4b; }
    .big-stat { font-size: 2em; font-weight: bold; color: #1f77b4; }
</style>
""", unsafe_allow_html=True)

data_svc = DataService()
viz_svc = VizService()

if data_svc.results.empty:
    st.error("⚠️ Data missing. Please run `src/metrics/calculate_void.py` first.")
    st.stop()

# ==========================================
# PAGE ROUTING
# ==========================================
class AppInterface:
    
    def render_sidebar(self):
        st.sidebar.title("🏈 Anticipation Void")
        return st.sidebar.radio("Navigation", [
            "1. The War Room (Summary)",
            "2. The Void Analyzer (Replay)",
            "3. Scouting Reports",
            "4. The Lab (Physics)"
        ])

    def render_animation_section(self, game_id, play_id, victim_id=-1, decoy_name=None, eraser_name=None):
        st.divider()
        st.subheader(f"🎥 Tape: Game {game_id} Play {play_id}")
        
        # Pass the new eraser_name argument to the backend
        df, name_col, id_col = data_svc.prepare_animation_frame(
            game_id, 
            play_id, 
            victim_id, 
            decoy_name, 
            eraser_name
        )
        
        if df is not None:
            fig = viz_svc.create_field_animation(df, game_id, play_id, name_col, id_col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Animation data not available for this specific play.")

    def page_summary(self):
        st.title("🛡️ The War Room: Executive Dashboard")
        st.markdown("### The State of Manipulation")
        
        m = data_svc.get_summary_metrics()
        if m:
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"""<div class="metric-card">Avg Void<br><span class="big-stat">{m['avg_void']:.2f} Score</span></div>""", unsafe_allow_html=True)
            with c2: st.markdown(f"""<div class="metric-card">Comp % (Exploited)<br><span class="big-stat">{m['high_leak_comp']*100:.1f}%</span></div>""", unsafe_allow_html=True)
            with c3: st.markdown(f"""<div class="metric-card">Comp % (Rotated)<br><span class="big-stat">{m['low_leak_comp']*100:.1f}%</span></div>""", unsafe_allow_html=True)
            with c4: st.markdown(f"""<div class="metric-card">Offensive Adv<br><span class="big-stat" style="color:green">+{int(m['delta'])}%</span></div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("The Quadrant of Domination")
        scatter_data = data_svc.get_league_scatter_data()
        fig = px.scatter(
            scatter_data, x='Total_Void_Yards', y='EPA_Per_Play', size='Plays',
            text='qb_name', color='EPA_Per_Play', color_continuous_scale='RdYlGn',
            title="Processing Volume vs. Efficiency",
            labels={'Total_Void_Yards': 'Manipulation Volume (Void Score)', 'EPA_Per_Play': 'Efficiency (EPA)'}
        )
        fig.update_traces(textposition='top center')
        fig.add_hline(y=scatter_data['EPA_Per_Play'].mean(), line_dash="dash", annotation_text="Avg EPA")
        fig.add_vline(x=scatter_data['Total_Void_Yards'].mean(), line_dash="dash", annotation_text="Avg Volume")
        st.plotly_chart(fig, use_container_width=True)

    def page_analyzer(self):
        st.title("🎬 The Void Analyzer")
        st.markdown("Select a play from the list below to analyze the manipulation.")
        
        # --- NEW FILTER ---
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_type = st.radio(
                "Filter Playlist:",
                ["Exploited Voids (Bad Defense)", "Tactical Rotations (Good Defense)"],
                index=0
            )
        
        catalog = data_svc.get_play_catalog()
        if catalog.empty:
            st.warning("No highlights found.")
            return

        # Apply Filter
        if "Bad" in filter_type:
            # Show high scores (Failures)
            view_catalog = catalog[catalog['Score'] > 0].sort_values('Score', ascending=False)
        else:
            # Show zero scores (Successes) - Sort by something else? 
            # Since Score is 0, we just show them. 
            # We filter for the "Tactical Rotation" label we created in backend.py
            view_catalog = catalog[catalog['The Story'].str.contains("Safety rotated", na=False)]

        st.markdown(f"**Showing {len(view_catalog)} plays**")

        selection = st.dataframe(
            view_catalog,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Score": st.column_config.ProgressColumn("Void Score", format="%.2f", min_value=0, max_value=catalog['Score'].max()),
                "The Story": st.column_config.TextColumn("Play Narrative", width="medium"),
            }
        )

        if selection.selection.rows:
            idx = selection.selection.rows[0]
            row = catalog.iloc[idx]
            
            # --- FIX: LOOKUP LOGIC ---
            # 1. Find the full record in the results to get the Victim's ID (nfl_id)
            # The 'results' dataframe has one row per play, representing the Victim.
            play_record = data_svc.results[
                (data_svc.results['game_id'] == row['game_id']) & 
                (data_svc.results['play_id'] == row['play_id'])
            ]
            
            # 2. Extract Victim ID safely
            v_id = -1
            if not play_record.empty:
                v_id = int(play_record.iloc[0]['nfl_id'])
            
            # 3. Extract Decoy and Eraser names safely from the catalog row
            # (Use .get() to avoid errors if columns are missing or NaN)
            d_name = row.get('decoy_name')
            if pd.isna(d_name): d_name = None
            
            e_name = row.get('eraser_name')
            if pd.isna(e_name): e_name = None

            # 4. Render Animation
            self.render_animation_section(
                row['game_id'], 
                row['play_id'], 
                victim_id=v_id, 
                decoy_name=d_name,
                eraser_name=e_name
            )
        else:
            st.info("👆 Click on a row to load the animation.")

    def page_scouting(self):
        st.title("🏆 Dual-Threat Scouting Reports")
        st.markdown("Click any row to instantly **Watch the Tape** of their defining moment.")
        
        # Update Tabs
        t1, t2, t3, t4 = st.tabs(["🧠 Puppeteers", "🪐 Gravity", "🎯 Victims", "🛡️ The Erasers"])
        
        # Puppeteers
        with t1:
            st.markdown("**Ranked by Total Void Created**")
            df = data_svc.get_puppeteer_stats()
            top = df[df['Plays'] >= 20].head(20).reset_index(drop=True)
            top.index += 1
            
            # FIX: Cast to native float
            max_void = float(top['Total_Void_Yards'].max())
            
            sel = st.dataframe(
                top[['qb_name', 'Total_Void_Yards', 'Avg_Void', 'Plays', 'pass_result']],
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Total_Void_Yards": st.column_config.ProgressColumn("Void Created", format="%.1f", min_value=0, max_value=max_void),
                    "pass_result": st.column_config.TextColumn("Best Rep Result")
                }
            )
            if sel.selection.rows:
                idx = sel.selection.rows[0]
                row = top.iloc[idx]
                self.render_animation_section(row['game_id'], row['play_id'])

        # Gravity
        with t2:
            st.markdown("**Ranked by Total EPA Generated**")
            df = data_svc.get_gravity_stats()
            if not df.empty:
                top = df[df['Plays'] >= 5].head(20).reset_index(drop=True)
                top.index += 1
                
                # FIX: Cast to native float
                max_epa = float(top['Total_EPA_Generated'].max())
                
                sel = st.dataframe(
                    top[['decoy_name', 'Total_EPA_Generated', 'Avg_Void', 'Plays', 'pass_result']],
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={
                        "Total_EPA_Generated": st.column_config.ProgressColumn("EPA Generated", format="%.1f", min_value=0, max_value=max_epa),
                        "pass_result": st.column_config.TextColumn("Best Rep Result")
                    }
                )
                if sel.selection.rows:
                    idx = sel.selection.rows[0]
                    row = top.iloc[idx]
                    self.render_animation_section(row['game_id'], row['play_id'], decoy_name=row['decoy_name'])

        # Victims
        with t3:
            st.markdown("**Ranked by Total Void Allowed**")
            df = data_svc.get_victim_stats()
            top = df[df['Times_Fooled'] >= 20].head(20).reset_index(drop=True)
            top.index += 1
            top['Avg_Exposure'] = top['Avg_Exposure'].fillna(0)
            
            # FIX: Cast to native float
            max_void_allowed = float(top['Total_Void_Allowed'].max())
            
            sel = st.dataframe(
                top[['player_name', 'Total_Void_Allowed', 'Avg_Exposure', 'Times_Fooled', 'pass_result']],
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Total_Void_Allowed": st.column_config.ProgressColumn(
                        "Void Liability", 
                        format="%.1f", 
                        min_value=0, 
                        max_value=max_void_allowed
                    ),
                    "Avg_Exposure": st.column_config.NumberColumn("Avg Exposure Score", format="%.2f"),
                    "pass_result": st.column_config.TextColumn("Worst Rep Result")
                }
            )
            
            if sel.selection.rows:
                idx = sel.selection.rows[0]
                row = top.iloc[idx]
                self.render_animation_section(row['game_id'], row['play_id'], victim_id=row['nfl_id'])

        # --- NEW TAB: THE ERASERS ---
        with t4:
            st.markdown("**Ranked by Successful Rotations (The 'Fixers')**")
            st.info("These players identified a teammate's mistake and covered the Void before the ball arrived.")
            
            df = data_svc.get_rotation_stats()
            if not df.empty:
                top = df.head(20).reset_index(drop=True)
                top.index += 1
                
                # FIX: Cast to native int
                max_rot = int(top['Rotations_Made'].max())
                
                sel = st.dataframe(
                    top[['player_name', 'Rotations_Made', 'player_position']],
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={
                        "Rotations_Made": st.column_config.ProgressColumn(
                            "Saves Made", 
                            format="%d", 
                            min_value=0, 
                            max_value=max_rot
                        ),
                    }
                )
                
                if sel.selection.rows:
                    idx = sel.selection.rows[0]
                    row = top.iloc[idx]
                    # Pass the eraser name so they get the Shield Icon
                    self.render_animation_section(
                        row['game_id'], 
                        row['play_id'], 
                        eraser_name=row['player_name'] # <--- PASS THIS
                    )
            else:
                st.write("No rotation data found.")

    def page_lab(self):
        st.title("🔬 The Physics Engine: Validation")
        st.markdown("How do we know this math predicts actual football outcomes?")
        
        st.subheader("1. The Void Cliff")
        st.markdown("We categorized every play based on the **Void Score** (Displacement + Help Latency). The result is undeniable: **Uncovered Voids lead to Completions.**")
        
        # UPDATED: Calls the new Void Bucket function
        cliff_data = data_svc.get_completion_by_void_bucket()
        fig_cliff = px.bar(
            cliff_data, x='Void_Bucket', y='Completion_Rate',
            color='Completion_Rate', color_continuous_scale='RdYlGn_r',
            text_auto='.1f', title="Completion Rate by Void Severity"
        )
        fig_cliff.update_layout(yaxis_title="Completion Probability (%)", xaxis_title="Void Severity")
        st.plotly_chart(fig_cliff, use_container_width=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("2. What is a 'Void'?")
            st.markdown("""
            We measure the **Leverage Gap** at the moment of the throw:
            * **Ghost Zone:** The area the defender vacated because they bit on a fake.
            * **Arrival Gap:** The difference in arrival time between the Receiver and the nearest Defender (Helper).
            
            **Formula:** $$ Score = \\text{Displacement} \\times (0.5 + \\text{Arrival Gap}) $$
            """)
        
        with c2:
            st.subheader("3. Correlation Matrix")
            st.markdown("Does the Void Score correlate with EPA?")
            df = data_svc.results
            # UPDATED: Removed bia_efficiency, kept clv (Void Score)
            corr = df[['clv', 'epa']].corr()
            fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r', title="Metric Correlations")
            st.plotly_chart(fig_corr, use_container_width=True)

# ==========================================
# EXECUTION
# ==========================================
app = AppInterface()
page = app.render_sidebar()

if page == "1. The War Room (Summary)": app.page_summary()
elif page == "2. The Void Analyzer (Replay)": app.page_analyzer()
elif page == "3. Scouting Reports": app.page_scouting()
elif page == "4. The Lab (Physics)": app.page_lab()