# Quick Start Guide - Pipeline Orchestrator

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r ../requirements.txt

# Install MATLAB or Octave (choose one)
# macOS:
brew install octave

# Ubuntu/Debian:
sudo apt-get install octave

# Or use MATLAB if you have it installed
```

### Step 2: Verify Anatomy Files

Make sure these files exist in `../anatomy/`:

```bash
ls ../anatomy/
# Should show:
# - connectivity_998.zip
# - leadfield_75_20k.mat
# - fs_cortex_20k_inflated.mat
# - fs_cortex_20k.mat
# - fs_cortex_20k_region_mapping.mat
# - dis_matrix_fs_20k.mat
```

### Step 3: Run the Pipeline

```bash
# Process regions 0-9 (10 regions total
```

That's it! The script will:

1. ✅ Generate TVB data for each region
2. ✅ Process raw NMM data
3. ✅ Delete raw data (to save space)
4. ✅ Generate synthetic source data

## 📊 What to Expect

### Processing Time

- **Per region**: 7-40 minutes
- **10 regions**: ~1-4 hours total
- **Varies by**: CPU speed, available RAM

### Disk Space

- **Peak usage**: ~5-10 GB (for one region at a time)
- **Final output**: ~2-5 GB (processed data)
- **Saved space**: ~50-100 GB (vs. keeping all raw data)

### Output Files

After completion, you'll have:

```
../source/
├── nmm_spikes/              # Extracted spike data
│   ├── a0/
│   │   ├── nmm_1.mat
│   │   ├── nmm_2.mat
│   │   └── ...
│   ├── a1/
│   └── ...
└── train_sample_source1.mat # Synthetic source parameters
```

## 🔍 Monitoring Progress

The script shows detailed progress:

```
################################################################################
# Processing Region 3 (4/10)
################################################################################

================================================================================
STEP 1: Generating TVB data for region 3
================================================================================
------ Generate data of region_id 3 ----------
Processing region 3, mean_iter 0, file 1/10
...
✓ Successfully generated TVB data for region 3

================================================================================
STEP 2: Processing raw NMM data for region 3
================================================================================
[INFO] Processing region 3, iteration 1/3 (iter=0)
[INFO] Downsampled data built and saved
...
✓ Successfully processed raw NMM data for region 3

================================================================================
STEP 3: Deleting raw data for region 3
================================================================================
✓ Successfully deleted raw data for region 3

✓ Completed region 3 in 1234.56 seconds
```

## ⚙️ Common Options

### Process Different Regions

```bash
# Just region 5
python pipeline_orchestrator.py --start_region 5 --end_region 6

# Regions 10-19
python pipeline_orchestrator.py --start_region 10 --end_region 20

# Single region for testing
python pipeline_orchestrator.py --start_region 0 --end_region 1
```

### Change Output Filename

```bash
python pipeline_orchestrator.py \
    --start_region 0 --end_region 10 \
    --filename my_spikes
```

### Use Different Leadfield

```bash
python pipeline_orchestrator.py \
    --start_region 0 --end_region 10 \
    --leadfield leadfield_32_20k.mat
```

### Run in Background

```bash
# Start in background
nohup python pipeline_orchestrator.py \
    --start_region 0 --end_region 10 \
    > pipeline.log 2>&1 &

# Monitor progress
tail -f pipeline.log

# Check if still running
ps aux | grep pipeline_orchestrator
```

## 🛠️ Troubleshooting

### Problem: "Neither MATLAB nor Octave found"

**Solution**: Install Octave or MATLAB

```bash
# macOS
brew install octave

# Ubuntu/Debian
sudo apt-get install octave
```

### Problem: "ModuleNotFoundError: No module named 'tvb'"

**Solution**: Install Python dependencies

```bash
pip install -r ../requirements.txt
```

### Problem: "File not found" errors

**Solution**: Make sure you're in the `forward/` directory

```bash
cd /Users/pasindusankalpa/Documents/dataset_deepSIF/data-generation/forward
python pipeline_orchestrator.py --start_region 0 --end_region 10
```

### Problem: Out of memory

**Solution**:

1. Close other applications
2. Process fewer regions at once
3. Increase system swap space

### Problem: Process seems stuck

**Check**:

- TVB simulations can take 10-30 minutes per region
- MATLAB/Octave processing can take 5-15 minutes
- Be patient, check CPU usage to confirm it's working

## 📝 Testing the Pipeline

### Test with a Single Region First

Before processing many regions, test with one:

```bash
python pipeline_orchestrator.py --start_region 0 --end_region 1
```

This should complete in 10-40 minutes and verify:

- ✅ TVB is working correctly
- ✅ MATLAB/Octave is accessible
- ✅ Anatomy files are present
- ✅ File permissions are correct

## 🔄 Resuming Interrupted Runs

If the pipeline is interrupted, you can resume:

```bash
# Just re-run the same command
python pipeline_orchestrator.py --start_region 0 --end_region 10
```

The pipeline will:

- Skip already processed regions (checks clip_info files)
- Continue from where it left off
- Only process remaining regions

## 📚 Next Steps

After the pipeline completes:

1. **Check output files**:

   ```bash
   ls ../source/nmm_spikes/
   ls ../source/train_sample_source1.mat
   ```

2. **Verify data quality**: Load a sample file to check:

   ```python
   from scipy.io import loadmat
   data = loadmat('../source/nmm_spikes/a0/nmm_1.mat')
   print(data['data'].shape)  # Should be (500, 994)
   ```

3. **Use in training**: Load the generated data for DeepSIF training
   ```python
   from scipy.io import loadmat
   params = loadmat('../source/train_sample_source1.mat')
   print(params.keys())
   ```

## 💡 Tips

1. **Start small**: Test with 1-2 regions before running all
2. **Monitor disk space**: Use `df -h` to check available space
3. **Background execution**: For large runs, use `nohup`
4. **Parallel processing**: Can run multiple batches on different machines
5. **Save logs**: Redirect output to a file for debugging

## 🆘 Getting Help

If you encounter issues:

1. Check the detailed [PIPELINE_README.md](PIPELINE_README.md)
2. Review error messages in the output
3. Check original [README.md](README.md) for parameter details
4. Verify TVB installation: `python -c "import tvb; print(tvb.__version__)"`
5. Test MATLAB/Octave: `matlab -nodisplay -r "quit"` or `octave --version`

## 📋 Complete Example Session

```bash
# 1. Navigate to forward directory
cd /Users/pasindusankalpa/Documents/dataset_deepSIF/data-generation/forward

# 2. Check dependencies
python -c "import tvb, scipy, numpy; print('Dependencies OK')"

# 3. Test with one region
python pipeline_orchestrator.py --start_region 0 --end_region 1

# 4. If successful, run full batch
python pipeline_orchestrator.py --start_region 0 --end_region 10

# 5. Monitor progress (if running in background)
tail -f pipeline.log

# 6. Check results
ls ../source/nmm_spikes/
ls ../source/train_sample_source1.mat
```

## ✨ Success!

When complete, you should see:

```
================================================================================
PIPELINE SUMMARY
================================================================================
Total time: 7234.56 seconds (120.58 minutes)
Successful regions: 10/10
  Regions: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
================================================================================
```

Your data is now ready for DeepSIF training! 🎉
