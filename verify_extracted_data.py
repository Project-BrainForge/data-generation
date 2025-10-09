"""
Script to verify and inspect extracted labeled data from MAT files.

This script loads and displays information about the extracted samples
to help verify that the extraction process completed successfully.

Usage:
    python verify_extracted_data.py --data_dir output/labeled_spikes_data
"""

import os
import argparse
import numpy as np
from scipy.io import loadmat
import h5py
import matplotlib.pyplot as plt


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
        return load_octave_text_file(file_path)
    except Exception as e:
        raise ValueError(f"Could not load file {file_path}. Tried MATLAB v7, v7.3 (HDF5), and Octave text formats. Error: {e}")


def verify_sample(file_path, verbose=True):
    """Verify a single sample file
    
    Parameters
    ----------
    file_path : str
        Path to the MAT file
    verbose : bool
        Whether to print detailed information
        
    Returns
    -------
    dict
        Dictionary with verification results
    """
    try:
        sample = load_mat_file(file_path)
        
        # Check required fields
        required_fields = ['eeg_data', 'source_data', 'labels', 'snr', 'index']
        missing_fields = [f for f in required_fields if f not in sample]
        
        if missing_fields:
            return {
                'valid': False,
                'error': f"Missing fields: {missing_fields}",
                'file': file_path
            }
        
        # Get data shapes
        eeg_shape = sample['eeg_data'].shape
        source_shape = sample['source_data'].shape
        labels_shape = sample['labels'].shape
        
        # Get active regions
        labels = sample['labels']
        active_regions = labels[labels >= 0]
        
        # Get statistics
        eeg_range = (np.min(sample['eeg_data']), np.max(sample['eeg_data']))
        source_range = (np.min(sample['source_data']), np.max(sample['source_data']))
        snr_value = float(sample['snr'][0, 0]) if sample['snr'].shape == (1, 1) else float(sample['snr'])
        
        if verbose:
            print("\n" + "="*60)
            print(f"File: {os.path.basename(file_path)}")
            print("="*60)
            print(f"EEG data shape: {eeg_shape}")
            print(f"Source data shape: {source_shape}")
            print(f"Labels shape: {labels_shape}")
            print(f"Number of active regions: {len(active_regions)}")
            print(f"Active region IDs: {sorted(active_regions.flatten())[:20]}{'...' if len(active_regions) > 20 else ''}")
            print(f"EEG data range: [{eeg_range[0]:.4f}, {eeg_range[1]:.4f}]")
            print(f"Source data range: [{source_range[0]:.4f}, {source_range[1]:.4f}]")
            print(f"SNR: {snr_value:.2f} dB")
            print(f"Dataset index: {sample['index'][0, 0]}")
        
        return {
            'valid': True,
            'file': file_path,
            'eeg_shape': eeg_shape,
            'source_shape': source_shape,
            'num_active_regions': len(active_regions),
            'snr': snr_value,
            'eeg_range': eeg_range,
            'source_range': source_range,
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'file': file_path
        }


def plot_sample(file_path, output_path=None):
    """Create a visualization of a sample
    
    Parameters
    ----------
    file_path : str
        Path to the MAT file
    output_path : str, optional
        Path to save the plot
    """
    sample = load_mat_file(file_path)
    
    eeg_data = sample['eeg_data']
    source_data = sample['source_data']
    labels = sample['labels']
    snr = sample['snr'][0, 0] if sample['snr'].shape == (1, 1) else sample['snr']
    
    # Get active regions
    active_regions = labels[labels >= 0].flatten()
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot EEG data
    axes[0, 0].imshow(eeg_data.T, aspect='auto', cmap='RdBu_r', 
                      interpolation='nearest', vmin=-1, vmax=1)
    axes[0, 0].set_title(f'EEG Sensor Data (75 electrodes x 500 time points)')
    axes[0, 0].set_xlabel('Time points')
    axes[0, 0].set_ylabel('Electrodes')
    axes[0, 0].colorbar = plt.colorbar(axes[0, 0].images[0], ax=axes[0, 0])
    
    # Plot source data (only active regions)
    active_source_data = source_data[:, active_regions.astype(int)]
    axes[0, 1].imshow(active_source_data.T, aspect='auto', cmap='hot', 
                      interpolation='nearest')
    axes[0, 1].set_title(f'Source Data ({len(active_regions)} active regions x 500 time points)')
    axes[0, 1].set_xlabel('Time points')
    axes[0, 1].set_ylabel('Active regions')
    axes[0, 1].colorbar = plt.colorbar(axes[0, 1].images[0], ax=axes[0, 1])
    
    # Plot sample EEG channels
    num_channels_to_plot = 10
    for ch in range(num_channels_to_plot):
        axes[1, 0].plot(eeg_data[:, ch] + ch * 2, linewidth=0.5)
    axes[1, 0].set_title(f'Sample EEG Channels (first {num_channels_to_plot})')
    axes[1, 0].set_xlabel('Time points')
    axes[1, 0].set_ylabel('Channel (offset)')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot sample source activations
    num_sources_to_plot = min(10, len(active_regions))
    for src in range(num_sources_to_plot):
        axes[1, 1].plot(active_source_data[:, src] + src * 0.3, linewidth=0.5)
    axes[1, 1].set_title(f'Sample Source Activations (first {num_sources_to_plot})')
    axes[1, 1].set_xlabel('Time points')
    axes[1, 1].set_ylabel('Source (offset)')
    axes[1, 1].grid(True, alpha=0.3)
    
    fig.suptitle(f'{os.path.basename(file_path)} - SNR: {snr:.2f} dB', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Verify and inspect extracted labeled data"
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        default="output/labeled_spikes_data",
        help="Directory containing extracted MAT files",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=5,
        help="Number of samples to verify in detail (default: 5)",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Create visualizations for verified samples",
    )
    parser.add_argument(
        "--plot_dir",
        type=str,
        default="output/verification_plots",
        help="Directory to save plots",
    )
    
    args = parser.parse_args()
    
    # Check if data directory exists
    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory not found: {args.data_dir}")
        return
    
    # Get list of MAT files
    mat_files = sorted([
        os.path.join(args.data_dir, f) 
        for f in os.listdir(args.data_dir) 
        if f.startswith('sample_') and f.endswith('.mat')
    ])
    
    if not mat_files:
        print(f"Error: No sample files found in {args.data_dir}")
        return
    
    print("\n" + "="*60)
    print("Verification Report")
    print("="*60)
    print(f"Data directory: {args.data_dir}")
    print(f"Total samples found: {len(mat_files)}")
    
    # Verify all samples (quick check)
    valid_samples = 0
    invalid_samples = []
    
    print(f"\nQuick verification of all samples...")
    for file_path in mat_files:
        result = verify_sample(file_path, verbose=False)
        if result['valid']:
            valid_samples += 1
        else:
            invalid_samples.append(result)
    
    print(f"\nValid samples: {valid_samples}/{len(mat_files)}")
    
    if invalid_samples:
        print(f"\nInvalid samples ({len(invalid_samples)}):")
        for result in invalid_samples:
            print(f"  - {os.path.basename(result['file'])}: {result['error']}")
    
    # Detailed verification of first N samples
    print("\n" + "="*60)
    print(f"Detailed verification of first {args.num_samples} samples")
    print("="*60)
    
    for i, file_path in enumerate(mat_files[:args.num_samples]):
        verify_sample(file_path, verbose=True)
    
    # Create plots if requested
    if args.plot and valid_samples > 0:
        os.makedirs(args.plot_dir, exist_ok=True)
        print("\n" + "="*60)
        print("Creating visualizations...")
        print("="*60)
        
        for i, file_path in enumerate(mat_files[:args.num_samples]):
            if verify_sample(file_path, verbose=False)['valid']:
                output_path = os.path.join(
                    args.plot_dir, 
                    f"sample_{i:05d}_visualization.png"
                )
                plot_sample(file_path, output_path)
        
        print(f"\nVisualizations saved to: {args.plot_dir}")
    
    # Load and display metadata if available
    metadata_file = os.path.join(args.data_dir, 'extraction_metadata.mat')
    if os.path.exists(metadata_file):
        print("\n" + "="*60)
        print("Extraction Metadata")
        print("="*60)
        metadata = load_mat_file(metadata_file)
        for key in metadata.keys():
            if not key.startswith('__'):
                value = metadata[key]
                if isinstance(value, np.ndarray):
                    if value.size == 1:
                        print(f"{key}: {value[0, 0]}")
                    elif value.ndim == 1:
                        print(f"{key}: {value}")
                    else:
                        print(f"{key}: {value.shape}")
                else:
                    print(f"{key}: {value}")
    
    print("\n" + "="*60)
    print("Verification complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

