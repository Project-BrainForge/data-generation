#!/bin/bash

# Example script to extract labeled data from spikes files
# This script demonstrates different usage scenarios

echo "======================================"
echo "Labeled Data Extraction Examples"
echo "======================================"
echo ""

# Example 1: Extract all samples (default)
echo "Example 1: Extract all samples with default settings"
echo "--------------------------------------"
echo "Command: python extract_labeled_data.py"
echo ""
# python extract_labeled_data.py

# Example 2: Extract first 10 samples for testing
echo "Example 2: Extract first 10 samples for testing"
echo "--------------------------------------"
echo "Command: python extract_labeled_data.py --dataset_len 10 --output_dir output/test_extraction"
echo ""
python extract_labeled_data.py --dataset_len 10 --output_dir output/test_extraction

# Example 3: Extract samples in batches (useful for large datasets)
echo ""
echo "Example 3: Extract samples in batches"
echo "--------------------------------------"
echo "Batch 1: Samples 0-99"
# python extract_labeled_data.py --dataset_len 100 --start_idx 0 --output_dir output/batch1

echo "Batch 2: Samples 100-199"
# python extract_labeled_data.py --dataset_len 100 --start_idx 100 --output_dir output/batch2

echo ""
echo "======================================"
echo "Extraction examples complete!"
echo "======================================"

