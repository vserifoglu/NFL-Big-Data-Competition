import pandas as pd
import gc
from typing import Generator, Tuple, List
from schema import PreprocessedSchema

class DataPreProcessor:
    def __init__(self):
        self.keep_cols = list(PreprocessedSchema.to_schema().columns.keys())

    def filter_context(self, supp_df):
        """
        filter the supplementary dataframe.
        """
        valid_mask = (
            (supp_df['team_coverage_man_zone'].astype(str).str.contains('Zone', case=False, na=False)) &
            (supp_df['pass_result'].isin(['C', 'I', 'IN'])) &
            (supp_df['team_coverage_type'] != 'COVER_6_ZONE') &
            (~supp_df['dropback_type'].isin(['SCRAMBLE', 'SCRAMBLE_ROLLOUT_LEFT', 'SCRAMBLE_ROLLOUT_RIGHT', 'QB_DRAW'])) &
            (supp_df['play_nullified_by_penalty'] != 'Y')
        )
        return supp_df[valid_mask].copy()

    def _stitch_tracking_data(self, input_df, output_df, valid_keys):
        """
        Pure Logic. Merges Pre-Throw and Post-Throw data.
        """
        # Filter Input
        input_df['key_tuple'] = list(zip(input_df.game_id, input_df.play_id))
        input_df = input_df[input_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
        input_df['phase'] = 'pre_throw'
        
        if output_df.empty: return input_df

        # Filter Output
        output_df['key_tuple'] = list(zip(output_df.game_id, output_df.play_id))
        output_df = output_df[output_df['key_tuple'].isin(valid_keys)].drop(columns=['key_tuple'])
        
        # Logic: Tag first frame of Output as pass_forward
        output_df.loc[output_df['frame_id'] == 1, 'event'] = 'pass_forward'
        
        # Metadata Propagation
        meta_cols = ['game_id', 'play_id', 'nfl_id', 'player_name', 'jersey_number', 'player_position', 
                     'player_role', 'player_side', 'play_direction', 'absolute_yardline_number', 
                     'ball_land_x', 'ball_land_y']
        
        avail_cols = [c for c in meta_cols if c in input_df.columns]
        player_meta = input_df[avail_cols].drop_duplicates(subset=['game_id', 'play_id', 'nfl_id'])
        
        # Frame Offset
        play_offsets = input_df.groupby(['game_id', 'play_id'])['frame_id'].max().reset_index()
        play_offsets.columns = ['game_id', 'play_id', 'offset']
        
        output_df = output_df.merge(player_meta, on=['game_id', 'play_id', 'nfl_id'], how='left')
        output_df = output_df.merge(play_offsets, on=['game_id', 'play_id'], how='left')
        
        output_df['frame_id'] = output_df['frame_id'] + output_df['offset'].fillna(0)
        output_df['phase'] = 'post_throw'
        
        df = pd.concat([input_df, output_df.drop(columns=['offset'])], ignore_index=True)

        return df

    def _normalize_coordinates(self, df):
        if 'play_direction' not in df.columns: return df
        mask = df['play_direction'].str.lower() == 'left'
        
        for col in ['x', 'ball_land_x']:
            if col in df.columns: df.loc[mask, col] = 120 - df.loc[mask, col]
        for col in ['y', 'ball_land_y']:
            if col in df.columns: df.loc[mask, col] = 53.3 - df.loc[mask, col]
        for col in ['dir', 'o']:
            if col in df.columns: df.loc[mask, col] = (df.loc[mask, col] + 180) % 360     
        return df

    def _clean_and_deduplicate(self, df):
        df['phase_rank'] = df['phase'].apply(lambda x: 1 if x == 'pre_throw' else 0)
        df = df.sort_values(['game_id', 'play_id', 'nfl_id', 'frame_id', 'phase_rank'])
        df = df.drop_duplicates(subset=['game_id', 'play_id', 'nfl_id', 'frame_id'], keep='last')

        if 's' in df.columns:
            df = df[(df['s'] < 13) | (df['s'].isna())]

        return df.drop(columns=['phase_rank'])

    def process_single_week(self, week_num, input_df, output_df, context_df):
        """
        Internal logic for a single week.
        """
        valid_keys = set(zip(context_df.game_id, context_df.play_id))

        # 1. Stitch
        week_df = self._stitch_tracking_data(input_df, output_df, valid_keys)

        # 2. Merge Context
        week_df = week_df.merge(context_df, on=['game_id', 'play_id'], how='inner')

        # 3. Normalize
        week_df = self._normalize_coordinates(week_df)

        # 4. Features
        week_df['los_x'] = week_df['ball_land_x'] - week_df['pass_length']
        week_df['week'] = int(week_num)

        # 5. Clean
        week_df = self._clean_and_deduplicate(week_df)

        # 6. Validate Output Schema
        return PreprocessedSchema.validate(week_df)

    def run(self, data_stream: Generator[Tuple[str, pd.DataFrame, pd.DataFrame], None, None], 
            raw_context_df: pd.DataFrame) -> pd.DataFrame:
        """
        MAIN ENTRY POINT.
        1. Filters Context.
        2. Consumes the data stream.
        3. Processes week-by-week.
        4. Returns final concatenated dataframe.
        """
        clean_context = self.filter_context(raw_context_df)
        
        processed_chunks: List[pd.DataFrame] = []
        
        for week_num, input_df, output_df in data_stream:
            clean_week_df = self.process_single_week(week_num, input_df, output_df, clean_context)

            if not clean_week_df.empty:
                processed_chunks.append(clean_week_df)

            # Explicit Memory Management
            del input_df, output_df
            gc.collect()

        if not processed_chunks:
            return pd.DataFrame()
        
        return pd.concat(processed_chunks, ignore_index=True)