import pandera as pa
from pandera.typing import Series


class RawSuppSchema(pa.SchemaModel):
    """
    Validates 'supplementary_data.csv'.
    Contains Game Context, Play Types, and Outcomes.
    """
    # --- Identifiers ---
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    
    # --- Plotting & Context ---
    week: Series[int] = pa.Field(coerce=True)
    home_team_abbr: Series[str]
    visitor_team_abbr: Series[str]
    play_description: Series[str] = pa.Field(nullable=True)
    
    # --- Game State ---
    down: Series[int] = pa.Field(coerce=True, ge=1, le=4)
    yards_to_go: Series[int] = pa.Field(coerce=True)
    possession_team: Series[str]
    defensive_team: Series[str]
    yardline_number: Series[int] = pa.Field(ge=0, le=50) 
    pre_snap_home_team_win_probability: Series[float] = pa.Field(nullable=True)

    # --- Logic Filters (Critical) ---
    play_nullified_by_penalty: Series[str] = pa.Field(nullable=True)
    dropback_type: Series[str] = pa.Field(nullable=True) 
    play_action: Series[bool] = pa.Field(coerce=True, nullable=True)
    
    # --- Defensive Scheme ---
    team_coverage_man_zone: Series[str] = pa.Field(nullable=True)
    team_coverage_type: Series[str] = pa.Field(nullable=True) 
    
    # --- Results & Geometry ---
    pass_result: Series[str] = pa.Field(nullable=True) 
    pass_length: Series[float] = pa.Field(nullable=True)
    pass_location_type: Series[str] = pa.Field(nullable=True) 
    yards_gained: Series[float] = pa.Field(nullable=True)
    expected_points_added: Series[float] = pa.Field(nullable=True)
    route_of_targeted_receiver: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = 'filter' 
        

class RawTrackingSchema(pa.SchemaModel):
    """
    Validates 'input_wXX.csv' files (Pre-Throw / Full Play).
    """
    # --- Identifiers ---
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    frame_id: Series[int] = pa.Field(coerce=True, ge=1)
    nfl_id: Series[float] = pa.Field(coerce=True, nullable=True) # Nullable for Ball
    
    # --- Timing ---
    event: Series[str] = pa.Field(nullable=True) 

    # --- Normalization Anchors ---
    play_direction: Series[str] 
    absolute_yardline_number: Series[int] = pa.Field(ge=0, le=120)
    
    # --- Player Attributes ---
    player_name: Series[str] = pa.Field(nullable=True)
    jersey_number: Series[float] = pa.Field(nullable=True, coerce=True)
    player_position: Series[str] = pa.Field(nullable=True)
    player_side: Series[str] = pa.Field(nullable=True) 
    player_role: Series[str] = pa.Field(nullable=True)
    
    # --- Physics Vectors ---
    x: Series[float] = pa.Field(ge=0, le=120)
    y: Series[float] = pa.Field(ge=0, le=53.3)
    s: Series[float] = pa.Field(ge=0, le=15, nullable=True) 
    a: Series[float] = pa.Field(ge=0, le=15, nullable=True) 
    o: Series[float] = pa.Field(ge=0, le=360, nullable=True) 
    dir: Series[float] = pa.Field(ge=0, le=360, nullable=True)
    
    # --- Answer Key ---
    ball_land_x: Series[float] = pa.Field(nullable=True)
    ball_land_y: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = 'filter' 
        

class OutputTrackingSchema(pa.SchemaModel):
    """
    Validates 'output_wXX.csv' files (Post-Throw Frames).
    Does NOT require speed/accel/dir.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    nfl_id: Series[int] = pa.Field(coerce=True, nullable=True)
    frame_id: Series[int] = pa.Field(coerce=True)
    
    x: Series[float] = pa.Field(ge=0, le=120, nullable=True)
    y: Series[float] = pa.Field(ge=0, le=53.3, nullable=True)

    class Config:
        strict = 'filter'


class PreprocessedSchema(RawTrackingSchema, RawSuppSchema):
    """
    Validates the output of 'preprocessing.py'.
    Inherits RawTracking + RawSupp.
    Adds calculated fields from the ETL process.
    """
    
    phase: Series[str] = pa.Field(isin=["pre_throw", "post_throw"])
    los_x: Series[float] = pa.Field(nullable=True) # Calculated Line of Scrimmage
    
    s_derived: Series[float] = pa.Field(nullable=True, coerce=True)
    a_derived: Series[float] = pa.Field(nullable=True, coerce=True)
    dir_derived: Series[float] = pa.Field(nullable=True, coerce=True) # 0-360 degrees

    class Config:
        strict = 'filter'


class FeatureEngineeredSchema(PreprocessedSchema):
    """
    Validates the output of 'features.py' (Landmark Calculation).
    Inherits PreprocessedSchema.
    Adds Zone Assignments and Target Coordinates.
    """

    # Angle from Player to Ball
    dir_ideal: Series[float] = pa.Field(nullable=True, ge=0, le=360) 

    # Deviation (Efficiency Error)
    angle_diff: Series[float] = pa.Field(nullable=True, ge=0, le=180) 

    class Config:
        strict = 'filter'


class VoidResultSchema(FeatureEngineeredSchema):
    """
    Validates the output of 'metrics.py' (Void Detection).
    Inherits FeatureEngineeredSchema.
    Adds Drift, Penalties, and EPA Impact.
    """
    
    # How many frames to align vector?
    reaction_time_frames: Series[float] = pa.Field(nullable=True) 

    # True if reaction_time > Threshold
    is_reaction_void: Series[bool]   

    # Average angle_diff over the play   
    avg_pursuit_error: Series[float]    

    # EPA Context
    is_punished: Series[bool]
    damage_epa: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = 'filter'