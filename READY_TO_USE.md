# ✅ Data Extraction Pipeline - Ready to Use!

## 🎉 Success!

Your data extraction pipeline is now fully functional and ready to extract all labeled data from spikes files.

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Extract all 384 samples
python extract_labeled_data.py

# Or start with a test batch
python extract_labeled_data.py --dataset_len 10 --output_dir output/test_batch
```

## What Was Fixed

1. ✅ **Octave Text Format Support** - Your dataset is in Octave format, now fully supported
2. ✅ **Padding Detection** - Handles padding value 15213
3. ✅ **NaN Handling** - Automatically uses default value (30.0) for NaN scale_ratio
4. ✅ **Array Dimensions** - Handles both 1D and multi-dimensional arrays
5. ✅ **Spikes File Mapping** - Cycles through 16 available spikes files

## Verified Output

✅ All extracted samples contain:
- **Real EEG data** (500 × 75) normalized to [-1, 1]
- **Real source data** (500 × 994) normalized to [0, 1]  
- **Region labels** with 10-11 active regions per sample
- **SNR values** in dB

Example verification:
```
Sample 0: EEG range [-0.89, 1.00], 37,500 non-zero values, 11 active regions, SNR=10dB ✅
Sample 1: EEG range [-0.88, 1.00], 37,500 non-zero values, 11 active regions, SNR=15dB ✅
Sample 2: EEG range [-0.73, 1.00], 37,500 non-zero values, 11 active regions, SNR=20dB ✅
```

## Files Ready to Use

### Main Scripts:
- **`extract_labeled_data.py`** - Extract and save labeled data
- **`verify_extracted_data.py`** - Verify and visualize extracted data
- **`loader.py`** - Updated dataset loader (handles Octave format)
- **`utils.py`** - Utility functions

### Documentation:
- **`EXTRACTION_README.md`** - Comprehensive documentation
- **`QUICKSTART_EXTRACTION.md`** - Quick start guide
- **`EXTRACTION_FIXES.md`** - Technical details of all fixes
- **`READY_TO_USE.md`** - This file

### Examples:
- **`example_extraction.sh`** - Example shell script

## Command Reference

### Extract Data

```bash
# Extract all samples (default settings)
python extract_labeled_data.py

# Extract specific number of samples
python extract_labeled_data.py --dataset_len 100

# Extract with custom output directory
python extract_labeled_data.py --output_dir output/my_data

# Extract samples starting from index 100
python extract_labeled_data.py --start_idx 100 --dataset_len 50

# Full custom command
python extract_labeled_data.py \
    --dataset_path source/train_sample_source1.mat \
    --output_dir output/batch1 \
    --forward_model anatomy/leadfield_75_20k.mat \
    --dataset_len 100 \
    --start_idx 0
```

### Verify Data

```bash
# Verify extracted data
python verify_extracted_data.py --data_dir output/labeled_spikes_data

# Verify with visualizations
python verify_extracted_data.py \
    --data_dir output/labeled_spikes_data \
    --num_samples 5 \
    --plot \
    --plot_dir output/verification_plots
```

## Output Structure

```
output/labeled_spikes_data/
├── sample_00000.mat  (2.0 MB)
├── sample_00001.mat  (2.0 MB)
├── sample_00002.mat  (2.0 MB)
├── ...
├── sample_00383.mat  (2.0 MB)
└── extraction_metadata.mat
```

Each MAT file contains:
```matlab
- eeg_data:     [500 x 75]   % EEG sensor measurements
- source_data:  [500 x 994]  % Brain source activations  
- labels:       [1 x 70]     % Active region IDs (padding >= 10000)
- snr:          scalar       % Signal-to-noise ratio (dB)
- index:        scalar       % Original dataset index
```

## Loading Extracted Data

### Python:
```python
from scipy.io import loadmat
import numpy as np

# Load sample
sample = loadmat('output/labeled_spikes_data/sample_00000.mat')

eeg_data = sample['eeg_data']      # (500, 75)
source_data = sample['source_data']  # (500, 994)
labels = sample['labels']           # (1, 70)
snr = sample['snr'][0, 0]          # scalar

# Get active regions (filter padding)
active_regions = labels[labels < 10000]
print(f"Active regions: {active_regions.flatten()}")
print(f"SNR: {snr} dB")
```

### MATLAB:
```matlab
% Load sample
sample = load('output/labeled_spikes_data/sample_00000.mat');

eeg_data = sample.eeg_data;      % 500 x 75
source_data = sample.source_data; % 500 x 994
labels = sample.labels;           % 1 x 70
snr = sample.snr;                % scalar

% Get active regions (filter padding)
active_regions = labels(labels < 10000);
fprintf('Number of active regions: %d\n', length(active_regions));
fprintf('SNR: %.1f dB\n', snr);
```

## Dataset Statistics

- **Total samples:** 384
- **Spikes files used:** 16 (cycling through a0/ and a1/)
- **Active regions per sample:** 10-11 regions
- **SNR range:** 5-20 dB
- **Output size:** ~2 MB per sample, ~780 MB total

## Important Notes

1. **Octave Format:** The dataset is in Octave text format, automatically detected and parsed
2. **NaN Values:** ~92% of samples have NaN scale_ratio, replaced with default value 30.0
3. **Spikes Cycling:** 16 spikes files are cycled to generate 384 samples
4. **Padding Values:** Region IDs >= 10000 indicate padding (specifically 15213)
5. **Normalization:** EEG data normalized to [-1, 1], source data to [0, 1]

## Need Help?

- See `EXTRACTION_README.md` for detailed documentation
- See `EXTRACTION_FIXES.md` for technical details of fixes
- Check `verify_extracted_data.py --help` for verification options
- Check `extract_labeled_data.py --help` for extraction options

---

**Status:** ✅ Fully functional and tested!

**Ready for:** Model training, data analysis, visualization

**Tested with:** Python 3.12, scipy, numpy, h5py, torch, tqdm

