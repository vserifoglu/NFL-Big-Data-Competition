# Dataset Description

## Summary of Data

Here, you'll find a summary of each data set in the 2026 Big Data Bowl, a list of key variables to join on, and a description of each variable. The tracking data is provided by the NFL Next Gen Stats team.

## External Data

The 2026 Big Data Bowl allows participants to use external NFL data as long as it is free and publicly available to all participants. Examples of sources that could be used include:

- **nflverse**
- **Pro Football Reference**

**Please note**: The `gameId` and `playId` of the Big Data Bowl data merges with the `old_game_id` and `play_id` of nflverse's play-by-play data.

## Files

### `train/`

#### `input_2023_w[01-18].csv`
The input data contains tracking data **before the pass is thrown**.

| Variable | Description | Type |
|----------|-------------|------|
| `game_id` | Game identifier, unique | Numeric |
| `play_id` | Play identifier, not unique across games | Numeric |
| `player_to_predict` | Whether or not the x/y prediction for this player will be included in the corresponding output file | Boolean |
| `nfl_id` | Player identification number, unique across players | Numeric |
| `frame_id` | Frame identifier for each play/type, starting at 1 for each `game_id`/`play_id`/file type (input or output) | Numeric |
| `play_direction` | Direction that the offense is moving (left or right) | Text |
| `absolute_yardline_number` | Distance from end zone for possession team | Numeric |
| `player_height` | Player height (ft-in) | Text |
| `player_name` | Player name | Text |
| `player_weight` | Player weight (lbs) | Numeric |
| `player_birth_date` | Birth date (yyyy-mm-dd) | Date |
| `player_position` | The player's position (the specific role on the field that they typically play) | Text |
| `player_side` | Team player is on (Offense or Defense) | Text |
| `player_role` | Role player has on play (Defensive Coverage, Targeted Receiver, Passer or Other Route Runner) | Text |
| `x` | Player position along the long axis of the field, generally within 0 - 120 yards | Numeric |
| `y` | Player position along the short axis of the field, generally within 0 - 53.3 yards | Numeric |
| `s` | Speed in yards/second | Numeric |
| `a` | Acceleration in yards/second² | Numeric |
| `o` | Orientation of player (degrees) | Numeric |
| `dir` | Angle of player motion (degrees) | Numeric |
| `num_frames_output` | Number of frames to predict in output data for the given `game_id`/`play_id`/`nfl_id` | Numeric |
| `ball_land_x` | Ball landing position along the long axis of the field, generally within 0 - 120 yards | Numeric |
| `ball_land_y` | Ball landing position along the short axis of the field, generally within 0 - 53.3 yards | Numeric |

#### `output_2023_w[01-18].csv`
The output data contains tracking data **after the pass is thrown**.

| Variable | Description | Type |
|----------|-------------|------|
| `game_id` | Game identifier, unique | Numeric |
| `play_id` | Play identifier, not unique across games | Numeric |
| `nfl_id` | Player identification number, unique across players | Numeric |
| `frame_id` | Frame identifier for each play/type, starting at 1 for each `game_id`/`play_id`/file type (input or output). The maximum value for a given `game_id`, `play_id` and `nfl_id` will be the same as the `num_frames_output` value from the corresponding input file | Numeric |
| `x` | Player position along the long axis of the field, generally within 0 - 120 yards | Numeric |
| `y` | Player position along the short axis of the field, generally within 0 - 53.3 yards | Numeric |

### Supplementary
Contextual info about the game/play.

| Variable | Description | Type |
|----------|-------------|------|
| `game_id` | Game identifier, unique | Numeric |
| `season` | Season of game | Numeric |
| `week` | Week of game | Numeric |
| `game_date` | Game Date (mm/dd/yyyy) | Date |
| `game_time_eastern` | Start time of game (HH:MM:SS, EST) | Time |
| `home_team_abbr` | Home team three-letter code | Text |
| `visitor_team_abbr` | Visiting team three-letter code | Text |
| `home_final_score` | The total amount of points scored by the home team in the game | Numeric |
| `visitor_final_score` | The total amount of points scored by the visiting team in the game | Numeric |
| `play_id` | Play identifier, not unique across games | Numeric |
| `play_description` | Description of play | Text |
| `quarter` | Game quarter | Numeric |
| `game_clock` | Time on clock of play (MM:SS) | Time |
| `down` | Down | Numeric |
| `yards_to_go` | Distance needed for a first down | Numeric |
| `possession_team` | Team abbr of team on offense with possession of ball | Text |
| `defensive_team` | Team abbr of team on defense | Text |
| `yardline_side` | 3-letter team code corresponding to line-of-scrimmage | Text |
| `yardline_number` | Yard line at line-of-scrimmage | Numeric |
| `pre_snap_home_score` | Home score prior to the play | Numeric |
| `pre_snap_visitor_score` | Visiting team score prior to the play | Numeric |
| `pass_result` | Dropback outcome of the play (C: Complete pass, I: Incomplete pass, S: Quarterback sack, IN: Intercepted pass, R: Scramble) | Text |
| `play_nullified_by_penalty` | Whether or not an accepted penalty on the play cancels the play outcome (Y stands for yes and N stands for no) | Text |
| `pass_length` | The distance beyond the LOS that the ball traveled not including yards into the endzone. If thrown behind LOS, the value is negative | Numeric |
| `offense_formation` | Formation used by possession team | Text |
| `receiver_alignment` | Enumerated as 0x0, 1x0, 1x1, 2x0, 2x1, 2x2, 3x0, 3x1, 3x2 | Text |
| `route_of_targeted_receiver` | Route ran by targeted receiver | Text |
| `play_action` | Indicates if there was play action on the play | Binary |
| `dropback_type` | The type of drop back after the snap by the QB (Traditional, Designed Rollout, Scramble, Scramble Rollout, Designed Rollout Left, Designed Rollout Right, Scramble Rollout Left, Scramble Rollout Right, Designed Run, QB Draw, Rollout) | Text |
| `dropback_distance` | The distance the QB dropped back (yards) behind the center after the snap | Numeric |
| `pass_location_type` | The location type of where the QB was at the time of throw - InsideTackle Box, Outside Left, Outside Right or Unknown | Text |
| `defenders_in_the_box` | Number of defenders in close proximity to line-of-scrimmage | Numeric |
| `team_coverage_man_zone` | Indicates the overarching type of coverage (Man/Zone) on a play | Text |
| `team_coverage_type` | The specific kind of coverage assigned on the play | Text |
| `penalty_yards` | Yards gained by offense by penalty | Numeric |
| `pre_penalty_yards_gained` | Net yards gained by the offense, before penalty yardage | Numeric |
| `yards_gained` | Net yards gained by the offense, including penalty yardage | Numeric |
| `expected_points` | Expected points on this play | Numeric |
| `expected_points_added` | Delta of expected points on this play | Numeric |
| `pre_snap_home_team_win_probability` | The win probability of the home team before the play | Numeric |
| `pre_snap_visitor_team_win_probability` | The win probability of the visiting team before the play | Numeric |
| `home_team_win_probability_added` | Win probability delta for home team | Numeric |
| `visitor_team_win_probility_added` | Win probability delta for visitor team | Numeric |