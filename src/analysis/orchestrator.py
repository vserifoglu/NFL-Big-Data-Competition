from story_data_engine import StoryDataEngine
from story_visual_engine import StoryVisualEngine
from story_on_film import StoryOnFilm

def main():
    print("=== STARTING VISUALIZATION PIPELINE ===")
    
    # PATHS
    SUMMARY = "data/processed/eraser_analysis_summary.csv"
    ANIMATION = "data/processed/master_animation_data.csv"
    OUTPUT = "data/visuals_final"
    
    # 1. STORY ENGINE: CASTING CALL
    # Finds the 4 Archetypes automatically based on your strict logic
    print("\n--- STEP 1: CASTING ARCHETYPES ---")
    story = StoryDataEngine(SUMMARY, ANIMATION)
    cast_dict = story.cast_archetypes()
    
    print("Selected Plays:")
    for role, meta in cast_dict.items():
        if meta:
            print(f"   -> {role}: ID {meta['nfl_id']} (VIS: {meta['vis_score']:.1f})")
        else:
            print(f"   -> {role}: [NO CANDIDATE FOUND]")

    # 2. VISUAL GENERATOR: STAT SHEETS
    # Generates Figures 1, 2, 3
    print("\n--- STEP 2: GENERATING CHARTS ---")
    viz = StoryVisualEngine(SUMMARY, ANIMATION, OUTPUT)
    
    # Pass the 'cast_dict' directly. No hardcoding IDs!
    viz.plot_eraser_landscape(cast_dict) 
    viz.plot_race_charts(cast_dict)
    viz.plot_coverage_heatmap()

    # 3. FILM ROOM: CASE STUDIES
    # Generates Figure 4 (Field View)
    print("\n--- STEP 3: GENERATING FILM ROOM ---")
    film = StoryOnFilm(ANIMATION, OUTPUT)
    
    # Render the Hero (Eraser) and the Villain (Liability)
    if cast_dict['Eraser']:
        print("   -> Filming Eraser...")
        film.generate_case_study(
            cast_dict['Eraser']['game_id'], 
            cast_dict['Eraser']['play_id'], 
            cast_dict['Eraser']['nfl_id'], 
            "Archetype_Eraser"
        )
        
    if cast_dict['Liability']:
        print("   -> Filming Liability...")
        film.generate_case_study(
            cast_dict['Liability']['game_id'], 
            cast_dict['Liability']['play_id'], 
            cast_dict['Liability']['nfl_id'], 
            "Archetype_Liability"
        )

    print("\n=== VISUALIZATION COMPLETE ===")

if __name__ == "__main__":
    main()