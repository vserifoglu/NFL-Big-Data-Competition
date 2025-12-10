# Dataset after cleaning required fields.

## Supplementary Data

| Variable | Criticality | Purpose |
|----------|-------------|---------|
| **`game_id`** | Essential | For joining tracking data |
| **`play_id`** | Essential | For joining tracking data |
| **`week`** | Mandatory | For "Metric Stability" report (Split-Half Reliability) |
| **`play_nullified_by_penalty`** | Required | Filter out plays that didn't count (clean data) |
| **`team_coverage_man_zone`** | Critical | Filter for `ZONE_COVERAGE` only |
| **`team_coverage_type`** | Critical | Used by Landmark Script to distinguish Cover 2, 3, and 4 rules |
| **`pass_length`** | Critical | Calculate "Golden Rule" Line of Scrimmage (`ball_land_x - pass_length`) |
| **`yardline_number`** | Critical | Required for "Red Zone" logic fix (identify when to squash zones near goal line) |
| **`route_of_targeted_receiver`** | Necessary | Explain "Pattern Match" limitation/mitigation |
| **`pass_result`** | Critical | Identify completions (C), incompletions (I), and interceptions (IN) |
| **`expected_points_added`** | Critical | Calculate "Total Damage EPA" for "Most Wanted" list |
| **`yards_gained`** | Useful | "Catastrophic Error" report (identify deep bombs vs. short gains) |
| **`possession_team`** & **`defensive_team`** | Required | Color-code dots correctly in animations |
| **`home_team_abbr`** & **`visitor_team_abbr`** | Required | Plot titles (e.g., "BUF vs KC") |
| **`down`** & **`yards_to_go`** | Essential | Context for "Hero Plot" (explain defender positioning decisions) |
| **`play_description`** | Mandatory | Plot captions/titles |
| `play_action` | Secondary | Indicates if there was play action on the play (binary) |
| `dropback_type` | Secondary | Type of QB dropback |
| `pass_location_type` | Secondary | Location of QB at time of throw |
| `pre_snap_home_team_win_probability` | Secondary | Pre-play win probability |

## Input Data

| Variable | Criticality | Purpose |
|----------|-------------|---------|
| **`game_id`** | Essential | Game identifier, unique (numeric) |
| **`play_id`** | Essential | Play identifier, not unique across games (numeric) |
| `player_to_predict` | Secondary | Whether player's x/y prediction included in output file (bool) |
| **`nfl_id`** | Essential | Player identification number, unique across players (numeric) |
| **`frame_id`** | Essential | Frame identifier for each play/type, starting at 1 for each `game_id`/`play_id`/file type (input or output) (numeric) |
| **`play_direction`** | Essential | Direction that offense is moving (left or right) |
| **`absolute_yardline_number`** | Critical | Distance from end zone for possession team |
| **`player_name`** | Useful | Player identification |
| **`player_position`** | Critical | Player's specific role on the field |
| **`player_side`** | Critical | Team player is on (Offense or Defense) |
| **`player_role`** | Critical | Role on play (Defensive Coverage, Targeted Receiver, Passer or Other Route Runner) |
| **`x`** | Critical | Player position along long axis (0-120 yards) |
| **`y`** | Critical | Player position along short axis (0-53.3 yards) |
| **`s`** | Useful | Speed in yards/second |
| **`a`** | Useful | Acceleration in yards/second² |
| **`o`** | Useful | Orientation of player (degrees) |
| **`dir`** | Useful | Angle of player motion (degrees) |
| **`ball_land_x`** | Critical | Ball landing position along long axis (0-120 yards) |
| **`ball_land_y`** | Critical | Ball landing position along short axis (0-53.3 yards) |

## Output Data

| Variable | Criticality | Purpose |
|----------|-------------|---------|
| **`game_id`** | Essential | Game identifier, unique (numeric) |
| **`play_id`** | Essential | Play identifier, not unique across games (numeric) |
| **`nfl_id`** | Essential | Player identification number, unique across players (numeric) |
| **`frame_id`** | Essential | Frame identifier |
| **`x`** | Critical | Player position along long axis (0-120 yards) |
| **`y`** | Critical | Player position along short axis (0-53.3 yards) |