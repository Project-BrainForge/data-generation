# Labeled Data Extraction from Spikes Files

This document explains how to use the `extract_labeled_data.py` script to extract and save labeled data from spikes files as MAT files.

## Overview

The extraction script:
1. Loads the dataset using the `SpikeEEGBuild` loader with spikes data enabled
2. Iterates through all samples in the dataset
3. Generates EEG sensor data using the forward model
4. Saves each sample as a separate MAT file with labels, EEG data, source data, and SNR

## Files Created

- **`utils.py`**: Utility functions required by the loader (add_white_noise, ispadding)
- **`extract_labeled_data.py`**: Main extraction script
- **`EXTRACTION_README.md`**: This documentation file

## Prerequisites

Make sure you have the required Python packages installed:

```bash
pip install numpy scipy torch tqdm mne h5py
```

## Usage

### Basic Usage

Extract all samples from the dataset:

```bash
python extract_labeled_data.py
```

This will:
- Use the default dataset: `source/train_sample_source1.mat`
- Use the default forward model: `anatomy/leadfield_75_20k.mat`
- Save output to: `output/labeled_spikes_data/`
- Extract all available samples

### Custom Options

```bash
python extract_labeled_data.py \
    --dataset_path source/train_sample_source1.mat \
    --output_dir output/my_labeled_data \
    --forward_model anatomy/leadfield_75_20k.mat \
    --dataset_len 100 \
    --start_idx 0
```

### Command-line Arguments

- `--dataset_path`: Path to dataset metadata file (default: `source/train_sample_source1.mat`)
- `--output_dir`: Directory to save output MAT files (default: `output/labeled_spikes_data`)
- `--forward_model`: Path to forward model (leadfield) MAT file (default: `anatomy/leadfield_75_20k.mat`)
- `--dataset_len`: Number of samples to extract (default: all samples)
- `--start_idx`: Starting index for extraction (default: 0)

## Output Format

Each sample is saved as a MAT file with the following structure:

```matlab
sample_00000.mat:
  - eeg_data:     [500 x 75]  EEG sensor data (time points x electrodes)
  - source_data:  [500 x 994] Source space data (time points x regions)
  - labels:       [2 x 70]    Labels for active source regions (with padding)
  - snr:          [1 x 1]     Signal-to-noise ratio
  - index:        [1 x 1]     Original dataset index
```

### Output Directory Structure

```
output/labeled_spikes_data/
├── sample_00000.mat
├── sample_00001.mat
├── sample_00002.mat
├── ...
└── extraction_metadata.mat
```

The `extraction_metadata.mat` file contains information about the extraction process:
- Total samples extracted
- Number of failed extractions
- Starting index
- Dataset path
- Forward model path
- Forward matrix shape

## Data Details

### EEG Data (`eeg_data`)
- Shape: (500, 75)
- 500 time points
- 75 electrodes
- Normalized to [-1, 1]
- Mean-centered across time and channels
- Includes Gaussian noise based on SNR

### Source Data (`source_data`)
- Shape: (500, 994)
- 500 time points
- 994 cortical regions
- Only active regions (specified in labels) contain non-zero values
- Normalized to [0, 1]

### Labels (`labels`)
- Shape: (2, 70)
- First dimension: number of sources (typically 2)
- Second dimension: cortical regions in each source patch (variable length, padded to 70)
- Negative values indicate padding
- First value in each row is the center region ID

### SNR (`snr`)
- Signal-to-noise ratio in decibels (dB)
- Applied to the sensor space (EEG) data

## Example: Loading Extracted Data in Python

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

print(f"EEG data shape: {eeg_data.shape}")
print(f"Source data shape: {source_data.shape}")
print(f"Active regions: {active_regions}")
print(f"SNR: {snr[0, 0]} dB")
```

## Example: Loading Extracted Data in MATLAB

```matlab
% Load a sample
sample = load('output/labeled_spikes_data/sample_00000.mat');

eeg_data = sample.eeg_data;      % 500 x 75
source_data = sample.source_data; % 500 x 994
labels = sample.labels;           % 2 x 70
snr = sample.snr;                % scalar

% Get active regions (remove padding)
active_regions = labels(labels >= 0);

fprintf('EEG data shape: %d x %d\n', size(eeg_data));
fprintf('Source data shape: %d x %d\n', size(source_data));
fprintf('Number of active regions: %d\n', length(active_regions));
fprintf('SNR: %.2f dB\n', snr);
```

## Troubleshooting

### Issue: "Could not find forward matrix in file"

**Solution**: Check the forward model file and ensure it contains one of the expected keys:
- `fwd`
- `forward`
- `leadfield`
- `L`

You can inspect the file in Python:
```python
from scipy.io import loadmat
data = loadmat('anatomy/leadfield_75_20k.mat')
print(data.keys())
```

### Issue: "Failed to load spikes data"

**Solution**: Ensure the spikes files are present in the correct directory structure:
```
source/nmm_spikes/
├── a0/
│   ├── nmm_1.mat
│   ├── nmm_2.mat
│   └── ...
├── a1/
│   ├── nmm_1.mat
│   ├── nmm_2.mat
│   └── ...
└── ...
```

### Issue: Memory errors

**Solution**: Process the dataset in batches using `--dataset_len` and `--start_idx`:
```bash
# Extract first 100 samples
python extract_labeled_data.py --dataset_len 100 --start_idx 0

# Extract next 100 samples
python extract_labeled_data.py --dataset_len 100 --start_idx 100
```

## Notes

- The script uses spikes data from `source/nmm_spikes/` directory
- Progress is displayed using tqdm progress bar
- Failed samples are logged but don't stop the extraction process
- All output files use 5-digit zero-padded indices (e.g., `sample_00042.mat`)

## Citation

If you use this data extraction pipeline, please cite the original DeepSIF paper and TVB framework.

