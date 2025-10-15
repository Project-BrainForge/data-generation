"""
Pipeline Orchestrator for DeepSIF Data Generation

This script orchestrates the complete data generation pipeline:
1. Generate TVB data for each region
2. Process raw NMM data region by region
3. Delete raw data after each region is processed
4. Generate synthetic source data for all regions at the end

Usage:
    python pipeline_orchestrator.py --start_region 0 --end_region 10 [--filename spikes] [--leadfield leadfield_75_20k.mat]
"""

import sys
import subprocess
import shutil
import argparse
import time
from pathlib import Path
from mega import Mega
import os
from pathlib import Path


class PipelineOrchestrator:
    def __init__(
        self,
        start_region,
        end_region,
        filename="spikes",
        leadfield_name="leadfield_75_20k.mat",
    ):
        """
        Initialize the pipeline orchestrator

        Args:
            start_region: Starting region ID (inclusive)
            end_region: Ending region ID (exclusive)
            filename: Filename prefix for processed data
            leadfield_name: Name of the leadfield file to use
        """
        self.start_region = start_region
        self.end_region = end_region
        self.filename = filename
        self.leadfield_name = leadfield_name
        self.base_path = Path(__file__).parent.parent
        self.raw_data_path = self.base_path / "source" / "raw_nmm"
        self.processed_data_path = self.base_path / "source" / f"nmm_{self.filename}"

    def check_processed_spikes_exist(self, region_id):
        """
        Check if processed spikes already exist for a specific region

        Args:
            region_id: Region ID to check

        Returns:
            True if processed spikes exist, False otherwise
        """
        region_path = self.processed_data_path / f"a{region_id}"

        if not region_path.exists():
            return False

        # Check if clip_info exists for all iterations
        # Looking for files like clip_info/iter0/iter_0_i_{region_id}.mat
        for iter_num in [0, 1, 2]:  # Check iterations 0, 1, 2
            clip_info_file = (
                self.processed_data_path
                / "clip_info"
                / f"iter{iter_num}"
                / f"iter_{iter_num}_i_{region_id}.mat"
            )
            if not clip_info_file.exists():
                return False

        # Also check if there are some spike files
        spike_files = list(region_path.glob("nmm_*.mat"))
        if len(spike_files) == 0:
            return False

        return True

    def check_raw_data_exists(self, region_id):
        """
        Check if raw data already exists for a specific region

        Args:
            region_id: Region ID to check

        Returns:
            True if raw data exists, False otherwise
        """
        region_path = self.raw_data_path / f"a{region_id}"

        if not region_path.exists():
            return False

        # Check if at least one iteration file exists
        # Looking for files like mean_iter_0_a_iter_{region_id}_0.mat
        for iter_num in [0, 1, 2]:  # Check iterations 0, 1, 2
            expected_file = (
                region_path / f"mean_iter_{iter_num}_a_iter_{region_id}_0.mat"
            )
            if expected_file.exists():
                return True

        return False

    def run_generate_tvb_data(self, region_id):
        """
        Generate TVB data for a specific region (only if raw data doesn't exist)

        Args:
            region_id: Region ID to process
        """
        print(f"\n{'=' * 80}")
        print(f"STEP 1: Checking/Generating TVB data for region {region_id}")
        print(f"{'=' * 80}\n")

        # Check if raw data already exists
        if self.check_raw_data_exists(region_id):
            print(
                f"✓ Raw data already exists for region {region_id}, skipping TVB generation"
            )
            return True

        print(f"Raw data not found for region {region_id}, generating TVB data...")

        try:
            cmd = [
                sys.executable,
                "generate_tvb_data.py",
                "--a_start",
                str(region_id),
                "--a_end",
                str(region_id + 1),
            ]

            subprocess.run(
                cmd,
                cwd=self.base_path / "forward",
                check=True,
                capture_output=False,
                text=True,
            )

            print(f"✓ Successfully generated TVB data for region {region_id}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Error generating TVB data for region {region_id}: {e}")
            return False

    def run_process_raw_nmm(self, region_id):
        """
        Process raw NMM data for a specific region using MATLAB

        Args:
            region_id: Region ID to process
        """
        print(f"\n{'=' * 80}")
        print(f"STEP 2: Processing raw NMM data for region {region_id}")
        print(f"{'=' * 80}\n")

        # Create MATLAB command to call the process_region function
        matlab_cmd = f"""
        cd('{self.base_path / "forward"}');
        pkg load signal;
        process_region({region_id}, '{self.filename}', '{self.leadfield_name}', '{self.base_path}');
        quit;
        """

        try:
            # Try to run with MATLAB
            subprocess.run(
                ["matlab", "-nodisplay", "-nosplash", "-nodesktop", "-r", matlab_cmd],
                cwd=self.base_path / "forward",
                check=True,
                capture_output=False,
                text=True,
                timeout=3600,  # 1 hour timeout per region
            )
            print(f"✓ Successfully processed raw NMM data for region {region_id}")
            return True

        except FileNotFoundError:
            print("✗ MATLAB not found. Trying Octave...")
            try:
                subprocess.run(
                    ["octave", "--no-gui", "--eval", matlab_cmd],
                    cwd=self.base_path / "forward",
                    check=True,
                    capture_output=False,
                    text=True,
                    timeout=3600,
                )
                print(f"✓ Successfully processed raw NMM data for region {region_id}")
                return True
            except FileNotFoundError:
                print("✗ Neither MATLAB nor Octave found. Please install one of them.")
                return False
            except subprocess.CalledProcessError as e:
                print(f"✗ Error processing with Octave for region {region_id}: {e}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"✗ Error processing raw NMM data for region {region_id}: {e}")
            return False
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout processing region {region_id}")
            return False

    def delete_raw_data(self, region_id):
        """
        Delete raw NMM data for a specific region to save disk space

        Args:
            region_id: Region ID whose raw data should be deleted
        """
        print(f"\n{'=' * 80}")
        print(f"STEP 3: Deleting raw data for region {region_id}")
        print(f"{'=' * 80}\n")

        region_path = self.raw_data_path / f"a{region_id}"

        if region_path.exists():
            try:
                shutil.rmtree(region_path)
                print(f"✓ Successfully deleted raw data for region {region_id}")
                print(f"  Removed: {region_path}")
                return True
            except Exception as e:
                print(f"✗ Error deleting raw data for region {region_id}: {e}")
                return False
        else:
            print(
                f"⚠ Raw data directory not found for region {region_id}: {region_path}"
            )
            return True

    def run_generate_synthetic_source(self):
        """
        Run the MATLAB script to generate synthetic source data for all regions
        """
        print(f"\n{'=' * 80}")
        print("STEP 4: Generating synthetic source data for all regions")
        print(f"{'=' * 80}\n")

        matlab_cmd = f"""
        cd('{self.base_path / "forward"}');
        generate_sythetic_source;
        quit;
        """

        try:
            subprocess.run(
                ["matlab", "-nodisplay", "-nosplash", "-nodesktop", "-r", matlab_cmd],
                cwd=self.base_path / "forward",
                check=True,
                capture_output=False,
                text=True,
                timeout=7200,  # 2 hour timeout
            )
            print("✓ Successfully generated synthetic source data")
            return True

        except FileNotFoundError:
            print("✗ MATLAB not found. Trying Octave...")
            try:
                subprocess.run(
                    ["octave", "--no-gui", "--eval", matlab_cmd],
                    cwd=self.base_path / "forward",
                    check=True,
                    capture_output=False,
                    text=True,
                    timeout=7200,
                )
                print("✓ Successfully generated synthetic source data")
                return True
            except FileNotFoundError:
                print("✗ Neither MATLAB nor Octave found. Please install one of them.")
                return False
            except subprocess.CalledProcessError as e:
                print(f"✗ Error generating synthetic source with Octave: {e}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"✗ Error generating synthetic source data: {e}")
            return False
        except subprocess.TimeoutExpired:
            print("✗ Timeout generating synthetic source data")
            return False

    def run(self):
        """
        Run the complete pipeline
        """
        mega = Mega()
        m = mega.login("pasindusankalpa599@gmail.com", "_izzBK7nf:Sd:7C")
        start_time = time.time()

        print("\n" + "=" * 80)
        print("DEEPSIF DATA GENERATION PIPELINE")
        print("=" * 80)
        print(f"Start Region: {self.start_region}")
        print(f"End Region: {self.end_region}")
        print(f"Total Regions: {self.end_region - self.start_region}")
        print(f"Filename: {self.filename}")
        print(f"Leadfield: {self.leadfield_name}")
        print("=" * 80 + "\n")

        # Process each region sequentially
        successful_regions = []
        failed_regions = []

        for region_id in range(self.start_region, self.end_region):
            region_start_time = time.time()

            print(f"\n{'#' * 80}")
            print(
                f"# Processing Region {region_id} ({region_id - self.start_region + 1}/{self.end_region - self.start_region})"
            )
            print(f"{'#' * 80}\n")

            # Step 0: Check if processed spikes already exist
            if self.check_processed_spikes_exist(region_id):
                print(
                    f"✓ Processed spikes already exist for region {region_id}, skipping all processing steps"
                )
                successful_regions.append(region_id)
                continue

            # Step 1: Generate TVB data
            if not self.run_generate_tvb_data(region_id):
                print(
                    f"⚠ Failed to generate TVB data for region {region_id}, skipping..."
                )
                failed_regions.append(region_id)
                continue

            # Step 2: Process raw NMM data
            if not self.run_process_raw_nmm(region_id):
                print(
                    f"⚠ Failed to process raw NMM data for region {region_id}, keeping raw data for debugging..."
                )
                failed_regions.append(region_id)
                continue

            # save processed data to mega
            # create a folder in mega
            # if not m.find(f"source/nmm_spikes/a{region_id}"):
            #     m.create_folder(f"source/nmm_spikes/a{region_id}")
            for file in os.listdir(self.processed_data_path / f"a{region_id}"):
                # folder = m.find(f"source/nmm_spikes/a{region_id}")
                # print("folder ==========", folder)
                m.upload(
                    self.processed_data_path / f"a{region_id}" / file,
                    dest_filename=f"nmm_spikes/a{region_id}/{file}",
                )

            # if not m.find("source/nmm_spikes/clip_info/iter0"):
            #     m.create_folder("source/nmm_spikes/clip_info/iter0")
            for file in os.listdir(
                self.base_path / "source" / "nmm_spikes" / "clip_info/iter0"
            ):
                # folder = m.find(f"source/nmm_spikes/clip_info")
                m.upload(
                    self.base_path
                    / "source"
                    / "nmm_spikes"
                    / "clip_info/iter0"
                    / f"iter_0_i_{region_id}.mat",
                    dest_filename=f"clip_info/iter0/iter_0_i_{region_id}.mat",
                )

            # if not m.find("source/nmm_spikes/clip_info/iter1"):
            #     m.create_folder("source/nmm_spikes/clip_info/iter1")
            for file in os.listdir(
                self.base_path / "source" / "nmm_spikes" / "clip_info/iter1"
            ):
                # folder = m.find(f"source/nmm_spikes/clip_info")
                m.upload(
                    self.base_path
                    / "source"
                    / "nmm_spikes"
                    / "clip_info/iter1"
                    / f"iter_1_i_{region_id}.mat",
                    dest_filename=f"clip_info/iter1/iter_1_i_{region_id}.mat",
                )

            # if not m.find("source/nmm_spikes/clip_info/iter2"):
            #     m.create_folder(
            #         "source/nmm_spikes/clip_info/iter2",
            #     )
            for file in os.listdir(
                self.base_path / "source" / "nmm_spikes" / "clip_info/iter2"
            ):
                # folder = m.find(f"source/nmm_spikes/clip_info")
                m.upload(
                    self.base_path
                    / "source"
                    / "nmm_spikes"
                    / "clip_info/iter2"
                    / f"iter_2_i_{region_id}.mat",
                    dest_filename=f"clip_info/iter2/iter_2_i_{region_id}.mat",
                )

            # Step 3: Delete raw data to save disk space (only if processing succeeded)
            self.delete_raw_data(region_id)

            # delete spikes from local
            os.remove(
                self.base_path
                / "source"
                / "nmm_spikes"
                / f"clip_info/iter0/iter_0_i_{region_id}.mat"
            )
            os.remove(
                self.base_path
                / "source"
                / "nmm_spikes"
                / f"clip_info/iter1/iter_1_i_{region_id}.mat"
            )
            os.remove(
                self.base_path
                / "source"
                / "nmm_spikes"
                / f"clip_info/iter2/iter_2_i_{region_id}.mat"
            )
            shutil.rmtree(self.base_path / "source" / "nmm_spikes" / f"a{region_id}")

            successful_regions.append(region_id)

            region_time = time.time() - region_start_time
            print(f"\n✓ Completed region {region_id} in {region_time:.2f} seconds")

        # Step 4: Generate synthetic source data for all regions
        if successful_regions:
            self.run_generate_synthetic_source()
        else:
            print(
                "\n✗ No regions were successfully processed. Skipping synthetic source generation."
            )

        # Summary
        total_time = time.time() - start_time
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Total time: {total_time:.2f} seconds ({total_time / 60:.2f} minutes)")
        print(
            f"Successful regions: {len(successful_regions)}/{self.end_region - self.start_region}"
        )
        if successful_regions:
            print(f"  Regions: {successful_regions}")
        if failed_regions:
            print(f"Failed regions: {len(failed_regions)}")
            print(f"  Regions: {failed_regions}")
        print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="DeepSIF Data Generation Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate data for regions 0-9
  python pipeline_orchestrator.py --start_region 0 --end_region 10
  
  # Generate data for regions 10-19 with custom filename
  python pipeline_orchestrator.py --start_region 10 --end_region 20 --filename custom_spikes
  
  # Use different leadfield
  python pipeline_orchestrator.py --start_region 0 --end_region 5 --leadfield leadfield_32_20k.mat
        """,
    )

    parser.add_argument(
        "--start_region", type=int, required=True, help="Starting region ID (inclusive)"
    )

    parser.add_argument(
        "--end_region", type=int, required=True, help="Ending region ID (exclusive)"
    )

    parser.add_argument(
        "--filename",
        type=str,
        default="spikes",
        help="Filename prefix for processed data (default: spikes)",
    )

    parser.add_argument(
        "--leadfield",
        type=str,
        default="leadfield_75_20k.mat",
        help="Leadfield filename (default: leadfield_75_20k.mat)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.start_region < 0:
        print("Error: start_region must be >= 0")
        sys.exit(1)

    if args.end_region <= args.start_region:
        print("Error: end_region must be > start_region")
        sys.exit(1)

    # Create and run orchestrator
    orchestrator = PipelineOrchestrator(
        start_region=args.start_region,
        end_region=args.end_region,
        filename=args.filename,
        leadfield_name=args.leadfield,
    )

    orchestrator.run()


if __name__ == "__main__":
    main()
