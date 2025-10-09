"""
Script to extract and save labeled data from spikes files as MAT files.

This script:
1. Loads the dataset using the SpikeEEGBuild loader with spikes data
2. Iterates through all samples
3. Saves each sample as a MAT file with labels, EEG data, source data, and SNR

Usage:
    python extract_labeled_data.py --dataset_path source/train_sample_source1.mat \
                                   --output_dir output/labeled_data \
                                   --forward_model anatomy/leadfield_75_20k.mat
"""

import os
import argparse
import numpy as np
from scipy.io import loadmat, savemat
import h5py
from loader import SpikeEEGBuild
from tqdm import tqdm


def load_octave_text_file(file_path):
    """Load Octave text format file
    
    Parameters
    ----------
    file_path : str
        Path to Octave text file
        
    Returns
    -------
    dict
        Dictionary containing the data
    """
    data = {}
    current_var = None
    current_type = None
    current_dims = None
    current_data = []
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('#'):
                if 'name:' in line:
                    # Save previous variable if exists
                    if current_var is not None and current_data:
                        if current_type == 'matrix':
                            arr = np.array(current_data)
                            if current_dims is not None and len(current_dims) > 1:
                                arr = arr.reshape(current_dims, order='F')  # Fortran order for MATLAB compatibility
                            data[current_var] = arr
                        elif current_type == 'scalar':
                            data[current_var] = current_data[0] if current_data else 0
                    
                    # Start new variable
                    current_var = line.split('name:')[1].strip()
                    current_data = []
                    current_dims = None
                elif 'type:' in line:
                    current_type = line.split('type:')[1].strip()
                elif 'ndims:' in line or 'rows:' in line or 'columns:' in line:
                    continue
                continue
            
            # Parse dimensions
            if current_dims is None and current_type == 'matrix':
                try:
                    dims = [int(x) for x in line.split()]
                    if len(dims) >= 1:
                        current_dims = dims
                        continue
                except ValueError:
                    pass
            
            # Parse data values
            if line and not line.startswith('#'):
                try:
                    values = [float(x) for x in line.split()]
                    current_data.extend(values)
                except ValueError:
                    # Try as single value
                    try:
                        current_data.append(float(line))
                    except ValueError:
                        pass
        
        # Save last variable
        if current_var is not None and current_data:
            if current_type == 'matrix':
                arr = np.array(current_data)
                if current_dims is not None and len(current_dims) > 1:
                    arr = arr.reshape(current_dims, order='F')  # Fortran order for MATLAB compatibility
                data[current_var] = arr
            elif current_type == 'scalar':
                data[current_var] = current_data[0] if current_data else 0
    
    return data


def load_mat_file(file_path):
    """Load MAT file, handling v7, v7.3 (HDF5), and Octave text formats
    
    Parameters
    ----------
    file_path : str
        Path to MAT file
        
    Returns
    -------
    dict
        Dictionary containing the MAT file data
    """
    try:
        # Try loading with scipy first (for MAT files v7 and earlier)
        return loadmat(file_path)
    except (ValueError, NotImplementedError, OSError):
        pass
    
    # Try h5py (for MAT files v7.3)
    try:
        print(f"Trying to load {file_path} as HDF5 format (MATLAB v7.3)...")
        data = {}
        with h5py.File(file_path, 'r') as f:
            for key in f.keys():
                if not key.startswith('__'):
                    # Handle different data types
                    dataset = f[key]
                    if isinstance(dataset, h5py.Dataset):
                        # Load the data and transpose if needed (MATLAB uses column-major)
                        arr = dataset[:]
                        # Handle references
                        if arr.dtype == np.object_:
                            data[key] = arr
                        else:
                            # Transpose for MATLAB compatibility
                            if arr.ndim == 2:
                                data[key] = arr.T
                            else:
                                data[key] = arr
                    else:
                        data[key] = dataset
        return data
    except (OSError, Exception):
        pass
    
    # Try Octave text format
    try:
        print(f"Trying to load {file_path} as Octave text format...")
        return load_octave_text_file(file_path)
    except Exception as e:
        raise ValueError(f"Could not load file {file_path}. Tried MATLAB v7, v7.3 (HDF5), and Octave text formats. Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and save labeled data from spikes files"
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        default="source/train_sample_source1.mat",
        help="Path to dataset metadata file",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="output/labeled_spikes_data",
        help="Directory to save output MAT files",
    )
    parser.add_argument(
        "--forward_model",
        type=str,
        default="anatomy/leadfield_75_20k.mat",
        help="Path to forward model (leadfield) MAT file",
    )
    parser.add_argument(
        "--dataset_len",
        type=int,
        default=None,
        help="Number of samples to extract (default: all)",
    )
    parser.add_argument(
        "--start_idx",
        type=int,
        default=0,
        help="Starting index for extraction (default: 0)",
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load forward model
    print(f"Loading forward model from {args.forward_model}...")
    fwd_data = load_mat_file(args.forward_model)
    
    # Try different possible keys for the forward matrix
    fwd = None
    for key in ["fwd", "forward", "leadfield", "L"]:
        if key in fwd_data:
            fwd = fwd_data[key]
            print(f"Found forward matrix with key '{key}', shape: {fwd.shape}")
            break
    
    if fwd is None:
        # Print available keys
        print("Available keys in forward model file:")
        for key in fwd_data.keys():
            if not key.startswith("__"):
                print(f"  - {key}: shape {fwd_data[key].shape}")
        raise ValueError("Could not find forward matrix in file")

    # Ensure forward matrix has correct shape (num_electrodes x num_regions)
    if fwd.shape[1] > fwd.shape[0]:  # More columns than rows suggests correct orientation
        print(f"Forward matrix shape: {fwd.shape} (electrodes x regions)")
    else:
        print(f"Warning: Forward matrix shape {fwd.shape} may need transposing")

    # Load dataset metadata to determine length
    dataset_meta = load_mat_file(args.dataset_path)
    total_samples = dataset_meta["selected_region"].shape[0]
    
    # Determine dataset length
    if args.dataset_len is None:
        dataset_len = total_samples
    else:
        dataset_len = min(args.dataset_len, total_samples)
    
    print(f"\nDataset information:")
    print(f"  Total samples in metadata: {total_samples}")
    print(f"  Samples to extract: {dataset_len}")
    print(f"  Starting from index: {args.start_idx}")

    # Initialize dataset with spikes data
    args_params = {
        "use_spikes": True,
        "dataset_len": dataset_len,
    }
    
    print("\nInitializing dataset with spikes data...")
    dataset = SpikeEEGBuild(
        data_root=args.dataset_path,
        fwd=fwd,
        transform=None,
        args_params=args_params,
    )

    print(f"Dataset initialized with {len(dataset)} samples\n")

    # Extract and save each sample
    successful_saves = 0
    failed_saves = 0
    
    print("Extracting and saving labeled data...")
    for idx in tqdm(range(args.start_idx, min(args.start_idx + dataset_len, len(dataset)))):
        try:
            # Get sample from dataset
            sample = dataset[idx]
            
            # Prepare data to save
            save_data = {
                "eeg_data": sample["data"],  # EEG sensor data (time x electrodes)
                "source_data": sample["nmm"],  # Source space data (time x regions)
                "labels": sample["label"],  # Labels for active regions
                "snr": sample["snr"],  # SNR value
                "index": idx,  # Original index
            }
            
            # Save as MAT file
            output_filename = os.path.join(args.output_dir, f"sample_{idx:05d}.mat")
            savemat(output_filename, save_data)
            successful_saves += 1
            
        except Exception as e:
            print(f"\nError processing sample {idx}: {e}")
            failed_saves += 1
            continue

    # Print summary
    print("\n" + "="*60)
    print("Extraction complete!")
    print(f"  Successfully saved: {successful_saves} samples")
    print(f"  Failed: {failed_saves} samples")
    print(f"  Output directory: {args.output_dir}")
    print("="*60)

    # Save extraction metadata
    metadata = {
        "total_extracted": successful_saves,
        "failed": failed_saves,
        "start_index": args.start_idx,
        "dataset_path": args.dataset_path,
        "forward_model_path": args.forward_model,
        "forward_matrix_shape": fwd.shape,
        "use_spikes": True,
    }
    metadata_file = os.path.join(args.output_dir, "extraction_metadata.mat")
    savemat(metadata_file, metadata)
    print(f"\nMetadata saved to: {metadata_file}")


if __name__ == "__main__":
    main()

