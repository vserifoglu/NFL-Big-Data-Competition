from src.config import VisPipelineConfig, vis_config
from src.analysis.data_loader import DataLoader
from src.analysis.story_data_engine import StoryDataEngine
from src.analysis.story_visual_engine import StoryVisualEngine
from src.analysis.animation_engine import AnimationEngine
from src.analysis.table_generator import TableGenerator

def run_full_pipeline(SUMMARY_FILE=None, TRACKING_FILE=None, OUTPUT_DIR=None):

    vis_cfg = VisPipelineConfig(
        SUMMARY_FILE=SUMMARY_FILE or vis_config.SUMMARY_FILE,
        TRACKING_FILE=TRACKING_FILE or vis_config.TRACKING_FILE,
        OUTPUT_DIR=OUTPUT_DIR or vis_config.OUTPUT_DIR
    )
    
    summary_path = vis_cfg.SUMMARY_FILE
    tracking_path = vis_cfg.TRACKING_FILE
    output_dir = vis_cfg.OUTPUT_DIR

    loader = DataLoader(summary_path, tracking_path)
    summary_df, frames_df = loader.load_data()
    
    # Generate summary tables
    table_gen = TableGenerator(summary_df)
    tables_stream = table_gen.run_all_analyses()

    # Story Engine (Logic & Stats)
    story = StoryDataEngine(summary_df, frames_df)

    # Visual Engine (Static Charts)
    viz = StoryVisualEngine(summary_df, frames_df, output_dir)
    viz.plot_coverage_heatmap()
    viz.plot_effort_impact_chart()

    leaderboard_df = tables_stream["leaderboard"]
    viz.plot_ceoe_leaderboard(leaderboard_df)
    viz.plot_styled_leaderboard(leaderboard_df)

    # archetypes
    cast_dict = story.cast_archetypes()
    viz.plot_eraser_landscape(cast_dict) 
    viz.plot_race_charts(cast_dict)

    # Animation Engine (Video Rendering)
    animator = AnimationEngine(summary_df, frames_df, output_dir)

    # Get Comparisons for animations
    fs_contrast = story.get_position_contrast('FS')

    # Render Top FS Eraser
    if fs_contrast['top']:
        animator.generate_video(
            game_id=fs_contrast['top']['game_id'], 
            play_id=fs_contrast['top']['play_id'], 
            eraser_id=fs_contrast['top']['nfl_id'], 
            filename="Figure_Top_FS_Eraser.gif" 
        )

    # Render Bottom FS Eraser
    if fs_contrast['bottom']:
        animator.generate_video(
            game_id=fs_contrast['bottom']['game_id'], 
            play_id=fs_contrast['bottom']['play_id'], 
            eraser_id=fs_contrast['bottom']['nfl_id'], 
            filename="Figure_Bottom_FS_Eraser.gif" 
        )

if __name__ == "__main__":
    run_full_pipeline()