"""Utility functions for the dataset loader"""

import numpy as np


def add_white_noise(signal, snr_db):
    """Add white noise to signal with specified SNR in dB
    
    Parameters
    ----------
    signal : np.ndarray
        Input signal
    snr_db : float
        Signal-to-noise ratio in decibels
        
    Returns
    -------
    np.ndarray
        Signal with added noise
    """
    # Calculate signal power
    signal_power = np.mean(signal ** 2)
    
    # Convert SNR from dB to linear scale
    snr_linear = 10 ** (snr_db / 10)
    
    # Calculate noise power
    noise_power = signal_power / snr_linear
    
    # Generate white noise
    noise = np.random.normal(0, np.sqrt(noise_power), signal.shape)
    
    # Add noise to signal
    noisy_signal = signal + noise
    
    return noisy_signal


def ispadding(arr):
    """Check if array elements are padding values
    
    Padding values are either:
    - Negative numbers
    - Values >= 10000 (like 15213 used in Octave format)
    
    Parameters
    ----------
    arr : np.ndarray
        Input array
        
    Returns
    -------
    np.ndarray
        Boolean array indicating padding values
    """
    return (arr < 0) | (arr >= 10000)

