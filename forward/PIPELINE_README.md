# DeepSIF Data Generation Pipeline Orchestrator

## Overview

The `pipeline_orchestrator.py` script automates the complete data generation workflow for DeepSIF, processing regions sequentially to save disk space by deleting raw data after processing each region.

## Pipeline Steps

The orchestrator performs the following steps for each region:

1. **Generate TVB Data** - Runs `generate_tvb_data.py` for a single region
2. **Process Raw NMM** - Processes the raw NMM data to extract spikes (MATLAB/Octave)
3. **Delete Raw Data** - Removes raw NMM files for the processed region to save disk space
4. **Generate Synthetic Source** - After all regions are processed, generates synthetic source data (MATLAB/Octave)

## Prerequisites

### Python Dependencies

```bash
pip install -r ../requirements.txt
```

### MATLAB or Octave

You need either MATLAB or GNU Octave installed and accessible from the command line:

- **MATLAB**: Ensure `matlab` command is in your PATH
- **Octave**: Install via `brew install octave` (macOS) or package manager

### Required Files

Ensure the following anatomy files are present in `../anatomy/`:

- `connectivity_998.zip`
- `leadfield_75_20k.mat` (or your chosen leadfield file)
- `fs_cortex_20k_inflated.mat`
- `fs_cortex_20k.mat`
- `fs_cortex_20k_region_mapping.mat`
- `dis_matrix_fs_20k.mat`

## Usage

### Basic Usage

```bash
python pipeline_orchestrator.py --start_region 0 --end_region 10
```

This will process regions 0 through 9 (end_region is exclusive).

### Advanced Options

```bash
python pipeline_orchestrator.py \
    --start_region 0 \
    --end_region 10 \
    --filename spikes \
    --leadfield leadfield_75_20k.mat
```

### Arguments

| Argument         | Required | Default                | Description                        |
| ---------------- | -------- | ---------------------- | ---------------------------------- |
| `--start_region` | Yes      | -                      | Starting region ID (inclusive)     |
| `--end_region`   | Yes      | -                      | Ending region ID (exclusive)       |
| `--filename`     | No       | `spikes`               | Filename prefix for processed data |
| `--leadfield`    | No       | `leadfield_75_20k.mat` | Leadfield matrix filename          |

## Examples

### Example 1: Process regions 0-9

```bash
python pipeline_orchestrator.py --start_region 0 --end_region 10
```

### Example 2: Process regions 10-19 with custom filename

```bash
python pipeline_orchestrator.py \
    --start_region 10 \
    --end_region 20 \
    --filename custom_spikes
```

### Example 3: Process a single region

```bash
python pipeline_orchestrator.py --start_region 5 --end_region 6
```

### Example 4: Use different leadfield (76-region connectivity)

```bash
python pipeline_orchestrator.py \
    --start_region 0 \
    --end_region 10 \
    --leadfield leadfield_32_20k.mat
```

## Output Structure

The pipeline creates the following directory structure:

```
../source/
├── raw_nmm/              # Temporary - deleted after processing each region
│   ├── a0/
│   ├── a1/
│   └── ...
├── nmm_spikes/           # Processed spike data
│   ├── a0/
│   │   ├── nmm_1.mat
│   │   ├── nmm_2.mat
│   │   └── ...
│   ├── a1/
│   ├── clip_info/        # Processing metadata
│   │   └── iter0/
│   │       ├── iter_0_i_0.mat
│   │       └── ...
│   └── ...
└── train_sample_source1.mat  # Final synthetic source parameters
```

## Processing Time

Processing time varies by region but typically:

- TVB data generation: 5-30 minutes per region
- Raw NMM processing: 2-10 minutes per region
- Synthetic source generation: 10-30 minutes (all regions)

**Estimated total time for 10 regions: 1-4 hours**

## Disk Space Management

The orchestrator is designed to minimize disk space usage:

1. **Before orchestrator**: Processing all regions at once requires storing all raw NMM data simultaneously (~50-100 GB for 10 regions)

2. **With orchestrator**: Only one region's raw data exists at a time (~5-10 GB peak usage)

## Error Handling

The pipeline handles errors gracefully:

- If a region fails, it logs the error and continues with the next region
- Failed regions are reported in the final summary
- Partial progress is saved (via clip_info files)

## Resuming Interrupted Runs

The pipeline can resume from where it left off:

- Already processed regions (with clip_info files) are skipped
- You can re-run the same command to continue processing

## Monitoring Progress

The pipeline provides detailed progress information:

- Current region being processed
- Step-by-step status updates
- Time taken per region
- Final summary with success/failure counts

Example output:

```
################################################################################
# Processing Region 3 (4/10)
################################################################################

================================================================================
STEP 1: Generating TVB data for region 3
================================================================================
...
✓ Successfully generated TVB data for region 3

================================================================================
STEP 2: Processing raw NMM data for region 3
================================================================================
...
✓ Successfully processed raw NMM data for region 3

================================================================================
STEP 3: Deleting raw data for region 3
================================================================================
...
✓ Successfully deleted raw data for region 3

✓ Completed region 3 in 1234.56 seconds
```

## Troubleshooting

### MATLAB/Octave not found

**Error**: `Neither MATLAB nor Octave found`

**Solution**: Install MATLAB or Octave and ensure it's in your PATH:

```bash
# For Octave on macOS
brew install octave

# For Octave on Linux
sudo apt-get install octave
```

### Missing anatomy files

**Error**: File loading errors in TVB or MATLAB steps

**Solution**: Ensure all required anatomy files are in `../anatomy/` directory

### Out of memory errors

**Solution**:

- Process fewer regions at once
- Increase available RAM
- Close other applications

### Python package errors

**Error**: `ModuleNotFoundError`

**Solution**: Install required packages:

```bash
pip install -r ../requirements.txt
```

## Comparison with Manual Workflow

### Manual Workflow (Original)

```bash
# Step 1: Generate ALL raw data (requires lots of disk space)
python generate_tvb_data.py --a_start 0 --a_end 10

# Step 2: Process all regions in MATLAB
matlab -nodisplay -r "process_raw_nmm; quit"

# Step 3: Manually delete raw data
rm -rf ../source/raw_nmm/

# Step 4: Generate synthetic source in MATLAB
matlab -nodisplay -r "generate_sythetic_source; quit"
```

**Disadvantages**:

- Requires 50-100 GB disk space for raw data
- Must complete all TVB simulations before processing
- Manual intervention between steps
- All-or-nothing processing

### Orchestrated Workflow (New)

```bash
# Single command does everything
python pipeline_orchestrator.py --start_region 0 --end_region 10
```

**Advantages**:

- Minimal disk space (5-10 GB peak)
- Automated end-to-end
- Region-by-region processing
- Graceful error handling
- Progress tracking

## Configuration

You can modify the following parameters in the script if needed:

### TVB Simulation Parameters

Edit `generate_tvb_data.py`:

- `a_range`: Excitability parameter
- `siml`: Simulation length per segment
- `mean_and_std`: Mean and standard deviation parameters

### NMM Processing Parameters

In the orchestrator's MATLAB code:

- `iter_list`: Iteration list (default: 0:2)
- `target_SNR`: Target signal-to-noise ratio (default: 15)

### Synthetic Source Parameters

Edit `generate_sythetic_source.m`:

- `nper`: Number of NMM spike samples
- `n_data`: Number of data samples
- `n_iter`: Number of variations per source center

## Advanced Usage

### Running in Background

```bash
nohup python pipeline_orchestrator.py --start_region 0 --end_region 10 > pipeline.log 2>&1 &
```

### Monitoring Background Process

```bash
tail -f pipeline.log
```

### Processing Multiple Batches in Parallel

You can run multiple batches on different machines or at different times:

```bash
# Machine 1
python pipeline_orchestrator.py --start_region 0 --end_region 50

# Machine 2
python pipeline_orchestrator.py --start_region 50 --end_region 100
```

## Notes

1. **Region Indexing**: Regions are 0-indexed (region 0 is the first region)
2. **Exclusive End**: `--end_region` is exclusive (e.g., `--end_region 10` processes up to region 9)
3. **Leadfield Compatibility**: Ensure leadfield matrix size matches connectivity profile
4. **MATLAB vs Octave**: MATLAB is preferred for full compatibility; Octave may have minor differences
5. **Checkpointing**: The pipeline saves progress via clip_info files for crash recovery

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the original README.md files in the forward directory
3. Check TVB and MATLAB/Octave documentation

## License

Same as parent project - see LICENSE file in repository root.
