import pandas as pd
import numpy as np
import os
import glob
import logging
from datetime import datetime
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class EnergyAgent:
    """
    AI Agent for Energy Data Transformation following a defined SSIS-like pipeline.
    """
    
    def __init__(self, config):
        """Step 1: Initialization"""
        self.config = config
        self.data_root = config.DATA_ROOT
        self.master_sheet_path = config.MASTER_SHEET_PATH
        self.master_csv_path = config.MASTER_SHEET_PATH.replace('.xlsx', '.csv')
        self.processed_files_tracker = config.PROCESSED_FILES_TRACKER
        self.processed_log = config.PROCESSED_LOG
        
        self._setup_logging()
        
        self.departments = {
            'Melting': ['IF1', 'IF2'],
            'Moulding': ['MM1', 'MM2'],
            'Sand_Plant': ['SP1', 'SP2', 'SP3'],
            'Shot_Blasting': ['SB1', 'SB2'],
            'Utilities': ['Com_1', 'Com_2', 'Office']
        }
        
        self.non_melting_df = pd.DataFrame()
        self.melting_df = pd.DataFrame()
        self.merged_df = pd.DataFrame()
        self.newly_processed_files = []
        
        print("🤖 Energy Agent Initialized.")

    def _setup_logging(self):
        """Initializes the logging configuration."""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(self.processed_log), logging.StreamHandler()])
        self.logger = logging.getLogger(__name__)

    def _get_processed_files(self) -> set:
        """Reads the set of already processed file names from the tracker."""
        if not os.path.exists(self.processed_files_tracker):
            return set()
        with open(self.processed_files_tracker, 'r') as f:
            return set(line.strip() for line in f)

    def _update_processed_files_tracker(self):
        """Appends newly processed file names to the tracker."""
        os.makedirs(os.path.dirname(self.processed_files_tracker), exist_ok=True)
        with open(self.processed_files_tracker, 'a') as f:
            f.write('\n'.join(self.newly_processed_files) + '\n')
        self.logger.info(f"Updated tracker with {len(self.newly_processed_files)} new files.")

    def discover_and_load_new_files(self) -> bool:
        """Steps 2 & 3: Discover file structure and load only new files."""
        print("🔍 Discovering and loading new files...")
        processed_files = self._get_processed_files()
        all_new_data = []

        for dept, machines in self.departments.items():
            for machine in machines:
                machine_path = os.path.join(self.data_root, dept, machine)
                if not os.path.isdir(machine_path):
                    continue
                
                for file_path in glob.glob(os.path.join(machine_path, "*.xlsx")):
                    file_name = os.path.basename(file_path)
                    if file_name not in processed_files:
                        try:
                            df = pd.read_excel(file_path)
                            df['Machine_Name'] = machine
                            df['Department'] = dept
                            df['File_Name'] = file_name
                            df.rename(columns=lambda c: c.strip(), inplace=True)
                            all_new_data.append(df)
                            self.newly_processed_files.append(file_name)
                            print(f"  - Loaded new file: {file_name}")
                        except Exception as e:
                            self.logger.error(f"Failed to load {file_name}: {e}")
        
        if not all_new_data:
            print("✅ No new files found to process.")
            return False
        
        self.merged_df = pd.concat(all_new_data, ignore_index=True)
        print(f"✅ Loaded a total of {len(self.merged_df)} new records.")
        return True

    def separate_and_union_groups(self):
        """Steps 4 & 5: Separate into groups and union within them."""
        print("🔄 Separating into Melting and Non-Melting groups...")
        
        # Standardize column names before separation
        self.merged_df.columns = [col.replace(' ', '_').lower() for col in self.merged_df.columns]

        self.melting_df = self.merged_df[self.merged_df['department'] == 'Melting'].copy()
        self.non_melting_df = self.merged_df[self.merged_df['department'] != 'Melting'].copy()
        
        print(f"  - Melting records: {len(self.melting_df)}")
        print(f"  - Non-Melting records: {len(self.non_melting_df)}")

    def add_and_sort_by_serial(self):
        """Step 6: Add and sort by serial numbers."""
        print("🔢 Adding and sorting by serial numbers...")
        if not self.non_melting_df.empty:
            self.non_melting_df['SerialNo'] = range(len(self.non_melting_df))
            self.non_melting_df.sort_values('SerialNo', inplace=True)
        if not self.melting_df.empty:
            self.melting_df['SerialNo'] = range(len(self.melting_df))
            self.melting_df.sort_values('SerialNo', inplace=True)

    def align_and_concatenate(self):
        """Step 7: Align columns by adding placeholders and then concatenate."""
        print("🔗 Aligning columns and concatenating groups...")
        
        # Add placeholder columns to align dataframes
        if not self.non_melting_df.empty:
            if 'batch_id' not in self.non_melting_df.columns: self.non_melting_df['batch_id'] = 0
            if 'molten_metal' not in self.non_melting_df.columns: self.non_melting_df['molten_metal'] = 0
        
        if not self.melting_df.empty:
            if 'parts_produced' not in self.melting_df.columns: self.melting_df['parts_produced'] = 0

        # Concatenate the aligned dataframes
        self.merged_df = pd.concat([self.non_melting_df, self.melting_df], ignore_index=True, sort=False)
        
        # Fill null values in batch_id with '0'
        self.merged_df['batch_id'] = self.merged_df['batch_id'].fillna(0)
        
        print(f"✅ Concatenation complete. Total records: {len(self.merged_df)}")
        # print(self.merged_df.head(10))

    def apply_final_transformations(self):
        """Step 8: Apply all final data transformations."""
        print("✨ Applying final transformations...")
        
        # Generate final ID
        self.merged_df['id'] = range(1, len(self.merged_df) + 1)
        
        # Parse Timestamp to extract Date and Hours
        if 'time_stamp' in self.merged_df.columns:
            ts = pd.to_datetime(self.merged_df['time_stamp'].astype(str), errors='coerce')
            self.merged_df['date'] = ts.dt.date.astype(str)
            self.merged_df['hours'] = ts.dt.hour.fillna(0).astype(int)
        else:
            self.merged_df['date'] = ''
            self.merged_df['hours'] = 0
            
        # Ensure numeric columns are numeric, filling NaNs
        for col in ['consumption', 'molten_metal', 'parts_produced']:
            self.merged_df[col] = pd.to_numeric(self.merged_df.get(col), errors='coerce').fillna(0)
            
        # Derive columns
        zone_map = {"Zone A": 5, "Zone B": 7, "Zone C": 9, "Zone D": 11}
        self.merged_df['cost_of_energy'] = self.merged_df.get('mseb_zone', pd.Series(dtype=str)).map(zone_map).fillna(0) * self.merged_df['consumption']
        self.merged_df['kwh_tonne'] = self.merged_df.apply(lambda r: (r['consumption'] / r['molten_metal']) * 1000 if r['molten_metal'] else 0, axis=1)
        self.merged_df['kwh_part'] = self.merged_df.apply(lambda r: r['consumption'] / r['parts_produced'] if r['parts_produced'] else 0, axis=1)

        # Finalize and reorder columns
        final_column_map = {
            'id': 'ID', 'hours': 'Hours', 'date': 'Date', 'machine_name': 'Machine ID',
            'department': 'Department', 'mseb_zone': 'MSEB Zone', 'kwh_reading': 'KWH Reading',
            'consumption': 'Consumption', 'p_f': 'P#F', 'parts_produced': 'Parts produced',
            'molten_metal': 'Molten Metal', 'batch_id': 'Batch ID', 'cost_of_energy': 'Cost of Energy',
            'kwh_tonne': 'KWH_Tonne', 'kwh_part': 'KWH_part'
        }
        self.merged_df.rename(columns=final_column_map, inplace=True)
        
        final_columns_order = list(final_column_map.values())
        self.merged_df = self.merged_df.reindex(columns=final_columns_order)
        print("✅ Final transformations complete.")

    def save_output_files(self):
        """Step 9: Save the final dataframe to both Excel and CSV."""
        print("💾 Saving output files...")
        
        # Optional: Append to existing master sheet
        if os.path.exists(self.master_sheet_path):
            try:
                existing_master = pd.read_excel(self.master_sheet_path)
                self.merged_df = pd.concat([existing_master, self.merged_df], ignore_index=True)
                print(f"  - Appended {len(self.merged_df) - len(existing_master)} new records to existing master files.")
            except Exception as e:
                print(f"⚠️  Could not append to master files: {e}. Overwriting.")

        # Save to Excel
        self.merged_df.to_excel(self.master_sheet_path, index=False)
        # Save to CSV
        self.merged_df.to_csv(self.master_csv_path, index=False)
        print(f"  - Master Excel saved to: {self.master_sheet_path}")
        print(f"  - Master CSV saved to: {self.master_csv_path}")

    def run_complete_pipeline(self) -> bool:
        """Runs the entire data transformation pipeline in the correct order."""
        print("\n🚀 Starting Energy Data Transformation Pipeline...")
        print("="*50)
        
        if not self.discover_and_load_new_files():
            print("="*50)
            print("🎉 Pipeline finished. No new data to process.")
            return True

        self.separate_and_union_groups()
        self.add_and_sort_by_serial()
        self.align_and_concatenate()
        self.apply_final_transformations()
        self.save_output_files()
        
        # Step 10: Update Processed Files Tracker
        self._update_processed_files_tracker()
        
        print("="*50)
        print("🎉 Pipeline completed successfully!")
        return True

    def get_data_summary(self) -> Dict:
        """Returns a summary of the processed data."""
        return {
            'new_files_processed': len(self.newly_processed_files),
            'total_records_in_master_file': len(self.merged_df) if self.merged_df is not None else 0,
            'melting_records_processed': len(self.melting_df),
            'non_melting_records_processed': len(self.non_melting_df)
        }