"""
Verification Script for Pipeline Output

This script verifies that the pipeline completed successfully by checking:
1. Processed spike data exists for each region
2. Synthetic source parameter file exists
3. Data shapes and contents are valid

Usage:
    python verify_output.py --regions 10
    python verify_output.py --regions 10 --filename spikes
"""

import argparse
from pathlib import Path
import sys

try:
    from scipy.io import loadmat
    import numpy as np
except ImportError:
    print("Error: scipy and numpy are required. Install with: pip install scipy numpy")
    sys.exit(1)


def verify_pipeline_output(num_regions, filename="spikes", base_path=None):
    """
    Verify pipeline output for processed regions

    Args:
        num_regions: Number of regions that should have been processed
        filename: Filename prefix used in pipeline
        base_path: Base path to data-generation directory

    Returns:
        bool: True if verification passes, False otherwise
    """
    if base_path is None:
        base_path = Path(__file__).parent.parent
    else:
        base_path = Path(base_path)

    source_path = base_path / "source"

    print("=" * 80)
    print("PIPELINE OUTPUT VERIFICATION")
    print("=" * 80)
    print(f"Base path: {base_path}")
    print(f"Number of regions: {num_regions}")
    print(f"Filename prefix: {filename}")
    print("=" * 80 + "\n")

    all_passed = True

    # Check 1: Verify processed spike data exists for each region
    print("📁 Checking processed spike data...\n")

    for region_id in range(num_regions):
        region_dir = source_path / f"nmm_{filename}" / f"a{region_id}"

        if not region_dir.exists():
            print(f"  ✗ Region {region_id}: Directory not found: {region_dir}")
            all_passed = False
            continue

        # Count number of spike files
        spike_files = list(region_dir.glob("nmm_*.mat"))

        if len(spike_files) == 0:
            print(f"  ✗ Region {region_id}: No spike files found in {region_dir}")
            all_passed = False
            continue

        # Verify a sample file
        try:
            sample_file = spike_files[0]
            data = loadmat(sample_file)

            if "data" not in data:
                print(
                    f"  ✗ Region {region_id}: 'data' key not found in {sample_file.name}"
                )
                all_passed = False
                continue

            spike_data = data["data"]
            expected_shape = (500, 994)  # time x channels

            if spike_data.shape != expected_shape:
                print(
                    f"  ⚠ Region {region_id}: Unexpected shape {spike_data.shape}, expected {expected_shape}"
                )
                print(f"    Files: {len(spike_files)}")
            else:
                print(
                    f"  ✓ Region {region_id}: {len(spike_files)} spike files, shape {spike_data.shape}"
                )

        except Exception as e:
            print(f"  ✗ Region {region_id}: Error loading {sample_file.name}: {e}")
            all_passed = False

    # Check 2: Verify clip_info exists
    print("\n📋 Checking clip info metadata...\n")

    clip_info_found = False
    for region_id in range(num_regions):
        clip_info_dir = source_path / f"nmm_{filename}" / "clip_info" / "iter0"
        clip_info_file = clip_info_dir / f"iter_0_i_{region_id}.mat"

        if clip_info_file.exists():
            try:
                clip_info = loadmat(clip_info_file)
                num_spikes = clip_info.get("num_spike", [0])[0]
                if isinstance(num_spikes, np.ndarray):
                    num_spikes = num_spikes.item()
                print(
                    f"  ✓ Region {region_id}: Clip info found, {num_spikes} total spikes"
                )
                clip_info_found = True
            except Exception as e:
                print(f"  ⚠ Region {region_id}: Error reading clip info: {e}")
        else:
            print(f"  ✗ Region {region_id}: Clip info not found: {clip_info_file}")

    if not clip_info_found:
        print("  ⚠ Warning: No clip info files found")

    # Check 3: Verify synthetic source parameter file
    print("\n🎯 Checking synthetic source parameter file...\n")

    param_file = source_path / "train_sample_source1.mat"

    if not param_file.exists():
        print(f"  ✗ Synthetic source file not found: {param_file}")
        print(
            "  Note: This file is generated in the final step after all regions are processed"
        )
        all_passed = False
    else:
        try:
            params = loadmat(param_file)

            # Check expected keys
            expected_keys = [
                "selected_region",
                "nmm_idx",
                "current_snr",
                "scale_ratio",
                "mag_change",
            ]
            missing_keys = [k for k in expected_keys if k not in params]

            if missing_keys:
                print(f"  ⚠ Warning: Missing keys in parameter file: {missing_keys}")

            # Display information about the parameters
            if "selected_region" in params:
                print(f"  ✓ Synthetic source file found: {param_file}")
                print(f"    Selected region shape: {params['selected_region'].shape}")

            if "nmm_idx" in params:
                print(f"    NMM index shape: {params['nmm_idx'].shape}")

            if "current_snr" in params:
                snr_values = params["current_snr"].flatten()
                print(f"    SNR values: {np.unique(snr_values)} dB")

            print(
                f"    All parameters: {[k for k in params.keys() if not k.startswith('__')]}"
            )

        except Exception as e:
            print(f"  ✗ Error loading synthetic source file: {e}")
            all_passed = False

    # Check 4: Verify raw data was deleted (optional check)
    print("\n🗑️  Checking if raw data was deleted (to verify space savings)...\n")

    raw_data_path = source_path / "raw_nmm"

    if not raw_data_path.exists():
        print(f"  ✓ Raw data directory doesn't exist (all cleaned up)")
    else:
        # Count how many region directories still exist
        remaining_dirs = [
            d for d in raw_data_path.iterdir() if d.is_dir() and d.name.startswith("a")
        ]

        if len(remaining_dirs) == 0:
            print(f"  ✓ Raw data directory exists but is empty (cleaned up)")
        else:
            print(
                f"  ⚠ Warning: {len(remaining_dirs)} raw data directories still exist:"
            )
            for d in remaining_dirs[:5]:  # Show first 5
                print(f"    - {d.name}")
            if len(remaining_dirs) > 5:
                print(f"    ... and {len(remaining_dirs) - 5} more")
            print(f"  Tip: You can delete these to save disk space")

    # Final summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nYour pipeline output is valid and ready to use.")
        print("\nNext steps:")
        print("  1. Use the processed spike data in: source/nmm_spikes/")
        print(
            "  2. Use the parameter file in training: source/train_sample_source1.mat"
        )
        return True
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease review the errors above and:")
        print("  1. Check if the pipeline completed for all regions")
        print("  2. Re-run the pipeline for failed regions")
        print("  3. Verify MATLAB/Octave processing completed successfully")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify DeepSIF pipeline output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--regions",
        type=int,
        required=True,
        help="Number of regions that should have been processed",
    )

    parser.add_argument(
        "--filename",
        type=str,
        default="spikes",
        help="Filename prefix used in pipeline (default: spikes)",
    )

    parser.add_argument(
        "--base_path",
        type=str,
        default=None,
        help="Base path to data-generation directory (default: auto-detect)",
    )

    args = parser.parse_args()

    success = verify_pipeline_output(
        num_regions=args.regions, filename=args.filename, base_path=args.base_path
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
