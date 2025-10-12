from torch.utils.data import Dataset
import numpy as np
from scipy.io import loadmat
from scipy import interpolate
from utils import add_white_noise, ispadding
import random


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

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if line.startswith("#"):
                if "name:" in line:
                    # Save previous variable if exists
                    if current_var is not None and current_data:
                        if current_type == "matrix":
                            arr = np.array(current_data)
                            if current_dims is not None and len(current_dims) > 1:
                                arr = arr.reshape(
                                    current_dims, order="F"
                                )  # Fortran order for MATLAB compatibility
                            data[current_var] = arr
                        elif current_type == "scalar":
                            data[current_var] = current_data[0] if current_data else 0

                    # Start new variable
                    current_var = line.split("name:")[1].strip()
                    current_data = []
                    current_dims = None
                elif "type:" in line:
                    current_type = line.split("type:")[1].strip()
                elif "ndims:" in line or "rows:" in line or "columns:" in line:
                    continue
                continue

            # Parse dimensions
            if current_dims is None and current_type == "matrix":
                try:
                    dims = [int(x) for x in line.split()]
                    if len(dims) >= 1:
                        current_dims = dims
                        continue
                except ValueError:
                    pass

            # Parse data values
            if line and not line.startswith("#"):
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
            if current_type == "matrix":
                arr = np.array(current_data)
                if current_dims is not None and len(current_dims) > 1:
                    arr = arr.reshape(
                        current_dims, order="F"
                    )  # Fortran order for MATLAB compatibility
                data[current_var] = arr
            elif current_type == "scalar":
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

    # Try Octave text format
    try:
        return load_octave_text_file(file_path)
    except Exception as e:
        raise ValueError(
            f"Could not load file {file_path}. Tried MATLAB v7, v7.3 (HDF5), and Octave text formats. Error: {e}"
        )


class SpikeEEGBuild(Dataset):
    """Dataset, generate input/output on the run

    Attributes
    ----------
    data_root : str
        Dataset file location
    fwd : np.array
        Size is num_electrode * num_region
    data : np.array
        TVB output data
    dataset_meta : dict
        Information needed to generate data
        selected_region: spatial model for the sources; num_examples * num_sources * max_size
                         num_examples: num_examples in this dataset
                         num_sources: num_sources in one example
                         max_size: cortical regions in one source patch; first value is the center region id; variable length, padded to max_size
                            (set to 70, an arbitrary number)
        nmm_idx:         num_examples * num_sources: index of the TVB data to use as the source
        scale_ratio:     scale the waveform maginitude in source region; num_examples * num_sources * num_scale_ratio (num_snr_level)
        mag_change:      magnitude changes inside a source patch; num_examples * num_sources * max_size
                         weight decay inside a patch; equals to 1 in the center region; variable length; padded to max_size
        sensor_snr:      the Gaussian noise added to the sensor space; num_examples * 1;

    dataset_len : int
        size of the dataset, can be set as a small value during debugging
    """

    def __init__(self, data_root, fwd, transform=None, args_params=None):
        # args_params: optional parameters; can be dataset_len, use_spikes

        self.file_path = data_root
        self.fwd = fwd
        self.transform = transform

        self.data = []
        self.dataset_meta = load_mat_file(self.file_path)
        if "dataset_len" in args_params:
            self.dataset_len = args_params["dataset_len"]
        else:  # use the whole dataset
            self.dataset_len = self.dataset_meta["selected_region"].shape[0]
        if "num_scale_ratio" in args_params:
            self.num_scale_ratio = args_params["num_scale_ratio"]
        else:
            self.num_scale_ratio = self.dataset_meta["scale_ratio"].shape[2]

        # Option to use spikes data instead of raw NMM data
        self.use_spikes = args_params.get("use_spikes", False) if args_params else False

    def __getitem__(self, index):
        # if not self.data:
        #     self.data = h5py.File(
        #         "/Users/pasindusankalpa/Documents/DeepSIF/raw_nmm_combined.h5", "r"
        #     )["data"]  # test_sample_nmm_h5.mat

        raw_lb = self.dataset_meta["selected_region"][index].astype(
            np.int64
        )  # labels with padding   # 2D Arrray with 2 sources
        lb = raw_lb[
            np.logical_not(ispadding(raw_lb))
        ]  # labels without padding # [  0   1   2  39  46  48   9  19  45  49  50   6   8  11  12  14  16  23 3  10 857 852 853 855 856 858 859 867 837 850 851 854 861 862 864]
        raw_nmm = np.zeros((500, self.fwd.shape[1]))  # 75 *  994 ===>  500 * 994

        for kk in range(raw_lb.shape[0]):  # iterate through number of  sources # 2
            curr_lb = raw_lb[
                kk, np.logical_not(ispadding(raw_lb[kk]))
            ]  # [ 0  1  2 39 46 48  9 19 45 49 50  6  8 11 12 14 16 23  3 10]

            # Check if curr_lb is empty (all padding)
            if len(curr_lb) == 0:
                print(f"Skipping source {kk} with all padding labels")
                continue

            print(f"Processing source {kk} with labels {curr_lb}")
            # Handle both 1D and 2D nmm_idx arrays
            if self.dataset_meta["nmm_idx"].ndim == 1:
                nmm_idx = self.dataset_meta["nmm_idx"][index]
            else:
                nmm_idx = self.dataset_meta["nmm_idx"][index][kk]
            # Use spikes data if configured, otherwise use raw NMM data
            current_nmm = self.load_nmm_data(int(nmm_idx), use_spikes=self.use_spikes)
            # current_nmm = self.data[
            #     self.dataset_meta["nmm_idx"][index][kk]  # 19902
            # ]  # rows * 2 columns     # 500 * 994

            ssig = current_nmm[:, [curr_lb[0]]]  # waveform in the center region
            # set source space SNR
            if np.max(ssig) > 0:
                print(f"Setting SNR for source {kk}")
                # Handle both 2D and 3D scale_ratio arrays
                if self.dataset_meta["scale_ratio"].ndim == 2:
                    scale_ratio_val = self.dataset_meta["scale_ratio"][index][
                        random.randint(0, self.num_scale_ratio - 1)
                    ]
                else:
                    scale_ratio_val = self.dataset_meta["scale_ratio"][index][kk][
                        random.randint(0, self.num_scale_ratio - 1)
                    ]

                # Handle NaN scale_ratio values by using a default value
                if np.isnan(scale_ratio_val):
                    print(
                        f"Warning: scale_ratio is NaN for sample {index}, using default value 30.0"
                    )
                    scale_ratio_val = 30.0

                ssig = ssig / np.max(ssig) * scale_ratio_val
            else:
                print(f"Skipping source {kk} with all zeros signal")
                # If ssig is all zeros, skip this source
                continue
            current_nmm[:, curr_lb] = ssig.reshape(-1, 1)
            # set weight decay inside one source patch
            # Handle both 2D and 3D mag_change arrays
            if self.dataset_meta["mag_change"].ndim == 2:
                weight_decay = self.dataset_meta["mag_change"][index]
            else:
                weight_decay = self.dataset_meta["mag_change"][index][kk]
            weight_decay = weight_decay[np.logical_not(ispadding(weight_decay))]
            current_nmm[:, curr_lb] = ssig.reshape(-1, 1) * weight_decay

            raw_nmm = raw_nmm + current_nmm
        # =======================================================
        eeg = np.matmul(
            self.fwd,
            raw_nmm.transpose(),  # ( 75 * 994 ) * (500 * 994)' = 75 * 500
        )  # project data to sensor space; num_electrode * num_time
        csnr = self.dataset_meta["current_snr"][index]
        noisy_eeg = add_white_noise(eeg, csnr).transpose()  # 500 * 75

        noisy_eeg = noisy_eeg - np.mean(noisy_eeg, axis=0, keepdims=True)  # time
        noisy_eeg = noisy_eeg - np.mean(noisy_eeg, axis=1, keepdims=True)  # channel
        if np.max(np.abs(noisy_eeg)) > 0:
            noisy_eeg = noisy_eeg / np.max(np.abs(noisy_eeg))
            print(noisy_eeg.shape)
        else:
            noisy_eeg = np.zeros_like(noisy_eeg)

        # get the training output
        empty_nmm = np.zeros_like(raw_nmm)
        empty_nmm[:, lb] = raw_nmm[:, lb]
        if np.max(empty_nmm) > 0:
            empty_nmm = empty_nmm / np.max(empty_nmm)
        else:
            empty_nmm = np.zeros_like(empty_nmm)
        # Each data sample
        sample = {
            "data": noisy_eeg.astype("float32"),  # 500 * 75
            "nmm": empty_nmm.astype("float32"),  # 500 * 994
            "label": raw_lb,  # 2 * 70
            "snr": csnr,  # float
        }
        if self.transform:
            sample = self.transform(sample)

        # savemat('{}/data{}.mat'.format(self.file_path[0][:-4],index),{'data':noisy_eeg,'label':raw_lb,'nmm':empty_nmm[:,lb]})
        return sample

    def __len__(self):
        return self.dataset_len

    def load_nmm_data(
        self, nmm_idx, use_spikes=False
    ):  # raw tvb = 20000 time points * 998
        """Load NMM data from file based on index

        Parameters
        ----------
        nmm_idx : int
            Index to map to file parameters
        use_spikes : bool, optional
            If True, load from nmm_spikes directory instead of raw_nmm directory
        """
        if use_spikes:
            return self.load_spikes_data(nmm_idx)

        # Try to find the file by index across all directories
        # The file pattern is: mean_iter_{iter}_a_iter_{a_num}_{file_num}.mat
        print("Loading NMM data for index {} in load_nmm_data".format(nmm_idx))

        # Map index to file parameters
        # Try different mappings based on the index
        mappings = [
            # Mapping 1: direct mapping
            {
                "a_num": (nmm_idx % 4) + 1,
                "iter": (nmm_idx // 4) % 3,
                "file_num": nmm_idx % 20,
            },
            # Mapping 2: different iteration
            {
                "a_num": (nmm_idx % 4) + 1,
                "iter": ((nmm_idx // 4) + 1) % 3,
                "file_num": nmm_idx % 20,
            },
            # Mapping 3: different a_num
            {
                "a_num": ((nmm_idx % 4) + 1) % 4 + 1,
                "iter": (nmm_idx // 4) % 3,
                "file_num": nmm_idx % 20,
            },
        ]

        for mapping in mappings:
            a_num = mapping["a_num"]
            iter_num = mapping["iter"]
            file_num = mapping["file_num"]

            file_path = f"source/raw_nmm/a{a_num}/mean_iter_{iter_num}_a_iter_{a_num}_{file_num}.mat"
            try:
                data = load_mat_file(file_path)
                nmm_data = data["data"]  # Return the actual NMM data
                # Truncate to 994 regions to match forward matrix
                if nmm_data.shape[1] > 994:
                    nmm_data = nmm_data[:, :994]

                # Resample from 20000 time points to 500 time points
                if nmm_data.shape[0] == 20000:
                    # Use every 40th sample to get 500 time points
                    nmm_data = nmm_data[::40, :]
                elif nmm_data.shape[0] != 500:
                    # If not 20000, try to resample to 500
                    original_time = np.linspace(0, 1, nmm_data.shape[0])
                    new_time = np.linspace(0, 1, 500)
                    resampled_data = np.zeros((500, nmm_data.shape[1]))
                    for region in range(nmm_data.shape[1]):
                        f = interpolate.interp1d(original_time, nmm_data[:, region])
                        resampled_data[:, region] = f(new_time)
                    nmm_data = resampled_data

                print(f"Successfully loaded NMM data from {file_path}")
                return nmm_data
            except Exception as e:
                print(f"Failed to load {file_path}: {e}")
                continue

        # If all attempts fail, return zeros
        print(f"Warning: Could not load NMM data for index {nmm_idx}")
        return np.zeros((500, 994))  # Default size

    def load_spikes_data(self, nmm_idx):
        """Load spikes data from MAT files in the nmm_spikes directory

        Parameters
        ----------
        nmm_idx : int
            Index to map to file parameters

        Returns
        -------
        np.ndarray
            Spikes data with shape (500, 994)
        """
        print("Loading spikes data for index {}".format(nmm_idx))

        # Available files:
        # a0: nmm_1, nmm_2, nmm_3 (3 files)
        # a1: nmm_1 to nmm_13 (13 files)
        # Total: 16 files

        # Create a list of all available spikes files
        available_files = []
        # a0 files
        for i in [1, 2, 3]:
            available_files.append(("a0", i))
        # a1 files
        for i in range(1, 14):
            available_files.append(("a1", i))

        # Cycle through available files based on nmm_idx
        file_idx = nmm_idx % len(available_files)
        a_dir, file_num = available_files[file_idx]

        file_path = f"source/nmm_spikes/{a_dir}/nmm_{file_num}.mat"
        try:
            data = load_mat_file(file_path)
            spikes_data = data["data"]  # Return the actual spikes data

            # Ensure correct shape (500, 994)
            if spikes_data.shape != (500, 994):
                print(f"Warning: Spikes data shape {spikes_data.shape} != (500, 994)")
                # Truncate or pad as needed
                if spikes_data.shape[1] > 994:
                    spikes_data = spikes_data[:, :994]
                elif spikes_data.shape[1] < 994:
                    # Pad with zeros
                    padded_data = np.zeros((spikes_data.shape[0], 994))
                    padded_data[:, : spikes_data.shape[1]] = spikes_data
                    spikes_data = padded_data

                if spikes_data.shape[0] != 500:
                    # Resample time dimension if needed
                    original_time = np.linspace(0, 1, spikes_data.shape[0])
                    new_time = np.linspace(0, 1, 500)
                    resampled_data = np.zeros((500, spikes_data.shape[1]))
                    for region in range(spikes_data.shape[1]):
                        f = interpolate.interp1d(original_time, spikes_data[:, region])
                        resampled_data[:, region] = f(new_time)
                    spikes_data = resampled_data

            print(f"Successfully loaded spikes data from {file_path}")
            return spikes_data
        except Exception as e:
            print(f"Failed to load {file_path}: {e}")
            # If loading fails, return zeros
            print(f"Warning: Could not load spikes data for index {nmm_idx}")
            return np.zeros((500, 994))  # Default size
