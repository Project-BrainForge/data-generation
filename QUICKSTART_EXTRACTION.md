# Quick Start: Extract Labeled Data from Spikes Files

## Overview

I've created a complete data extraction pipeline for you that:

- ✅ Reads labeled data from spikes files (`source/nmm_spikes/`)
- ✅ Generates EEG sensor data using forward model
- ✅ Saves each sample as a separate MAT file with labels
- ✅ Handles both MATLAB v7 and v7.3 (HDF5) format files
- ✅ Includes verification and visualization tools

## Files Created

1. **`utils.py`** - Utility functions (add_white_noise, ispadding)
2. **`extract_labeled_data.py`** - Main extraction script
3. **`verify_extracted_data.py`** - Verification and visualization script
4. **`example_extraction.sh`** - Example shell script with usage examples
5. **`EXTRACTION_README.md`** - Detailed documentation
6. **`QUICKSTART_EXTRACTION.md`** - This quick start guide

## Quick Start

### Step 1: Run the Extraction

Extract a small test sample (10 samples):

```bash
python extract_labeled_data.py --dataset_len 10 --output_dir output/test_extraction
```

Extract all samples:

```bash
python extract_labeled_data.py
```

### Step 2: Verify the Output

Verify the extracted data:

```bash
python verify_extracted_data.py --data_dir output/labeled_spikes_data --num_samples 5
```

Create visualizations:

```bash
python verify_extracted_data.py --data_dir output/labeled_spikes_data --num_samples 5 --plot
```

## What Fixed the Error

The error you saw:

```
ValueError: Unknown mat file type, version 105, 111
```

This happened because your `train_sample_source1.mat` file is in MATLAB v7.3 format (HDF5), which requires `h5py` instead of `scipy.io.loadmat`.

**Solution:** I added a `load_mat_file()` function that:

1. First tries loading with scipy (for v7 and earlier)
2. If that fails, uses h5py for v7.3 HDF5 format
3. Handles proper transposes for MATLAB compatibility

This function is now used in:

- `loader.py` (updated)
- `extract_labeled_data.py`
- `verify_extracted_data.py`

## Output Format

Each extracted sample is saved as: `sample_00000.mat`, `sample_00001.mat`, etc.

Each file contains:

```
- eeg_data:     [500 x 75]  EEG sensor data
- source_data:  [500 x 994] Source space data
- labels:       [2 x 70]    Active region labels (with padding)
- snr:          scalar      Signal-to-noise ratio (dB)
- index:        scalar      Original dataset index
```

## Command-Line Options

### extract_labeled_data.py

```bash
--dataset_path      Path to dataset metadata (default: source/train_sample_source1.mat)
--output_dir        Output directory (default: output/labeled_spikes_data)
--forward_model     Forward model file (default: anatomy/leadfield_75_20k.mat)
--dataset_len       Number of samples to extract (default: all)
--start_idx         Starting index (default: 0)
```

### verify_extracted_data.py

```bash
--data_dir          Directory with extracted files (default: output/labeled_spikes_data)
--num_samples       Number of samples to verify in detail (default: 5)
--plot              Create visualizations
--plot_dir          Directory for plots (default: output/verification_plots)
```

## Processing in Batches

For large datasets, process in batches:

```bash
# Batch 1: Samples 0-99
python extract_labeled_data.py --dataset_len 100 --start_idx 0 --output_dir output/batch1

# Batch 2: Samples 100-199
python extract_labeled_data.py --dataset_len 100 --start_idx 100 --output_dir output/batch2

# Batch 3: Samples 200-299
python extract_labeled_data.py --dataset_len 100 --start_idx 200 --output_dir output/batch3
```

## Loading Extracted Data

### Python

```python
from scipy.io import loadmat

# Load a sample
sample = loadmat('output/labeled_spikes_data/sample_00000.mat')

eeg_data = sample['eeg_data']      # (500, 75)
source_data = sample['source_data']  # (500, 994)
labels = sample['labels']           # (2, 70)
snr = sample['snr']                # scalar

# Get active regions (remove padding)
active_regions = labels[labels >= 0]
print(f"Active regions: {active_regions}")
```

### MATLAB

```matlab
% Load a sample
sample = load('output/labeled_spikes_data/sample_00000.mat');

eeg_data = sample.eeg_data;      % 500 x 75
source_data = sample.source_data; % 500 x 994
labels = sample.labels;           % 2 x 70
snr = sample.snr;                % scalar

% Get active regions (remove padding)
active_regions = labels(labels >= 0);
fprintf('Number of active regions: %d\n', length(active_regions));
```

## Troubleshooting

### Issue: "Could not find forward matrix in file"

Check available keys in your forward model file:

```python
from scipy.io import loadmat
data = loadmat('anatomy/leadfield_75_20k.mat')
print(data.keys())
```

### Issue: "Failed to load spikes data"

Verify spikes files exist:

```bash
ls -R source/nmm_spikes/
```

Expected structure:

```
source/nmm_spikes/
├── a0/
│   ├── nmm_1.mat
│   ├── nmm_2.mat
│   └── ...
├── a1/
│   ├── nmm_1.mat
│   └── ...
```

### Issue: Memory errors

Process in smaller batches using `--dataset_len` and `--start_idx`.

## Next Steps

1. **Extract your data**: Run `extract_labeled_data.py`
2. **Verify outputs**: Run `verify_extracted_data.py`
3. **Check visualizations**: Use `--plot` flag to see sample data
4. **Use in your model**: Load the MAT files in your training pipeline

## Full Documentation

See `EXTRACTION_README.md` for complete documentation with detailed examples.

## Dependencies

All required packages are in `requirements.txt`:

- numpy
- scipy
- h5py
- torch
- tqdm
- matplotlib (for visualizations)

Install with:

```bash
pip install -r requirements.txt
```

---

**Ready to go!** The extraction script is now compatible with your HDF5 MAT files and will work out of the box.
