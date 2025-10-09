function process_region(region_id, filename, leadfield_name, base_path)
    % Process a specific region for NMM spike detection
    % 
    % Args:
    %   region_id: Region ID to process (0-based indexing from Python)
    %   filename: Filename prefix for processed data
    %   leadfield_name: Name of the leadfield file
    %   base_path: Base path to the project

    pkg load signal; 
    
    fprintf('[INFO] Starting processing for region %d\n', region_id);
    
    % Load headmodel
    headmodel = load([base_path '/anatomy/' leadfield_name]);
    fwd = headmodel.fwd;
    savefile_path = [base_path '/source/'];
    
    % Process parameters
    iter_list = 0:2;
    previous_iter_spike_num = zeros(1, 994);
    
    for i_iter = 1:length(iter_list)
        iter = iter_list(i_iter);
        fprintf('[INFO] Processing region %d, iteration %d/%d (iter=%d)\n', region_id, i_iter, length(iter_list), iter);
        
        clipinfo_dir = [savefile_path 'nmm_' filename '/clip_info/iter' int2str(iter)];
        if isempty(dir(clipinfo_dir))
           mkdir(clipinfo_dir)
        end
        
        % Check if already processed
        done_file = [savefile_path 'nmm_' filename '/clip_info/iter' int2str(iter) '/iter_' int2str(iter) '_i_' int2str(region_id) '.mat'];
        if isfile(done_file)
            fprintf('[INFO] Region %d iter %d already processed, skipping...\n', region_id, iter);
            continue;
        end
        
        i = region_id + 1; % MATLAB uses 1-based indexing
        
        % Create folders
        region_folder = [savefile_path 'nmm_' filename '/a' int2str(region_id)];
        if isempty(dir(region_folder))
            mkdir(region_folder)
        end
        
        fn = [savefile_path 'raw_nmm/a' int2str(region_id) '/mean_iter_' int2str(iter) '_a_iter_' int2str(region_id)];
        
        % Check if raw data exists
        if ~isfile([fn '_0.mat'])
            fprintf('[WARNING] Raw data not found for region %d iter %d\n', region_id, iter);
            continue;
        end
        
        % Load or create downsampled data
        if isfile([fn '_ds.mat'])
           raw_data = load([fn '_ds.mat']);
           nmm = raw_data.all_data;
        else
           sub_iter_nmm_files = dir([fn '_*.mat']);
           all_data = [];
           all_time = [];
           for sub_iter_i = 1:length(sub_iter_nmm_files)
               d = load(fullfile(sub_iter_nmm_files(sub_iter_i).folder, sub_iter_nmm_files(sub_iter_i).name));
               all_data = [all_data; d.data];
               all_time = [all_time; d.time'];
           end
           all_data = all_data(1001:end,:);
           all_time = all_time(1001:end);
           all_data = downsample(all_data, 4);
           all_time = downsample(all_time, 4);
           all_data = all_data(:, 1:994);
           save([fn '_ds.mat'], 'all_data', 'all_time')
           nmm = all_data;
        end
        
        % Find spikes
        [spike_time, spike_chan] = find_spike_time(nmm);
        
        % Select spikes from this region
        rule1 = (spike_chan == i);
        start_time = floor(spike_time(rule1)/500) * 500 + 1;
        clear_ind = repmat(start_time, [900, 1]) + (-200:699)';
        rule2 = (sum(ismember(clear_ind, spike_time(~rule1)), 1) == 0);
        spike_time = spike_time(rule1);
        spike_time = spike_time(rule2);
        
        % Scale NMM
        alpha_value = find_alpha(nmm, fwd, i, spike_time, 15);
        nmm = rescale_nmm_channel(nmm, i, spike_time, alpha_value);
        
        % Save spike data
        start_time = floor(spike_time/500) * 500 + 1;
        spike_ind = repmat(start_time, [500, 1]) + (0:499)';
        nmm_data = reshape(nmm(spike_ind,:), 500, [], size(nmm,2));
        save_spikes_(nmm_data, [savefile_path 'nmm_' filename '/a' int2str(region_id) '/nmm_'], previous_iter_spike_num(i));
        previous_iter_spike_num(i) = previous_iter_spike_num(i) + length(spike_time);
        
        % Save clip info
        save_struct = struct();
        save_struct.num_spike = previous_iter_spike_num(i);
        save_struct.spike_time = spike_time;
        save(done_file, '-struct', 'save_struct');
        
        fprintf('[INFO] Finished region %d, iter %d, total spikes: %d\n', region_id, iter, previous_iter_spike_num(i));
    end
    
    fprintf('✓ Successfully processed region %d\n', region_id);
end

% Helper functions
function local_max = islocalmax_octave(data)
    % Octave-compatible implementation of islocalmax
    % Finds local maxima along the first dimension (rows) of a matrix
    [rows, cols] = size(data);
    local_max = false(rows, cols);
    
    for col = 1:cols
        for row = 2:(rows-1)
            % A point is a local maximum if it's greater than its neighbors
            if data(row, col) > data(row-1, col) && data(row, col) > data(row+1, col)
                local_max(row, col) = true;
            end
        end
    end
end

function [spike_time, spike_chan] = find_spike_time(nmm)
    pkg load signal; 
    spikes_nmm = nmm;
    spikes_nmm(nmm < 8) = 0;
    pkg load signal; 
    local_max = islocalmax_octave(spikes_nmm);
    [spike_time, spike_chan] = find(local_max);
    [spike_time, sort_ind] = sort(spike_time);
    spike_chan = spike_chan(sort_ind);
    use_ind = (spike_time-249 > 0) & (spike_time+250 < size(nmm, 1) & [1 diff(spike_time)'>100]');
    spike_time = spike_time(use_ind)';
    spike_chan = spike_chan(use_ind)';
end

function [alpha] = find_alpha(nmm, fwd, region_id, time_spike, target_SNR)
    pkg load signal; 
    spike_ind = repmat(time_spike, [200, 1]) + (-99:100)';
    spike_ind = min(max(spike_ind(:),0), size(nmm,1));
    spike_shape = nmm(:,region_id);
    nmm(:, region_id) = spike_shape;
    [Ps, Pn, ~] = calcualate_SNR(nmm, fwd, region_id, spike_ind);
    alpha = sqrt(10^(target_SNR/10)*Pn/Ps);
end

function scaled_nmm = rescale_nmm_channel(nmm, region_id, spike_time, alpha_value)
    pkg load signal; 
    nmm_rm = nmm - mean(nmm, 1);
    for i=1:length(spike_time)
        sig = nmm_rm(spike_time(i)-249:spike_time(i)+250, region_id);
        thre = 0.1;
        small_ind = find(abs(sig)<thre);
        small_ind((small_ind>450) | (small_ind < 50)) = [];
        start_ind = find((small_ind-250)<0);
        while isempty(start_ind)
            thre = thre+0.05;
            small_ind = find(abs(sig)<thre);
            small_ind((small_ind>450) | (small_ind < 50)) = [];
            start_ind = find((small_ind-250)<0);
        end
        start_sig = small_ind(start_ind(end));
        [~, min_ind] = min(sig(301:400));
        min_ind = min_ind + 301;
        end_ind = find((small_ind-min_ind)>0);
        while isempty(end_ind)
            thre = thre+0.05;
            small_ind = find(abs(sig)<thre);
            small_ind((small_ind>450) | (small_ind < 50)) = [];
            end_ind = find((small_ind-min_ind)>0);
        end
        end_sig = small_ind(end_ind(1));
        sig(start_sig:end_sig) = sig(start_sig:end_sig) * alpha_value;
        nmm_rm(spike_time(i)-249:spike_time(i)+250, region_id) = sig;
    end
    scaled_nmm = nmm_rm + mean(nmm, 1);
end

function [Ps, Pn, cur_snr] = calcualate_SNR(nmm, fwd, region_id, spike_ind)
    pkg load signal; 
    sig_eeg = (fwd(:, region_id)*nmm(:, region_id)')';
    sig_eeg_rm = sig_eeg - mean(sig_eeg, 1);
    dd = 1:size(nmm,2);
    dd(region_id) = [];
    noise_eeg = (fwd(:,dd)*nmm(:,dd)')';
    noise_eeg_rm = noise_eeg - mean(noise_eeg, 1);
    Ps = norm(sig_eeg_rm(spike_ind,:),'fro')^2/length(spike_ind);
    Pn = norm(noise_eeg_rm(spike_ind,:),'fro')^2/length(spike_ind);
    cur_snr = 10*log10(Ps/Pn);
end

function save_spikes_(spike_data, savefile_path, previous_iter_spike_num)
    pkg load signal; 
    for iii = 1:size(spike_data,2)
        data = squeeze(spike_data(:,iii,:));
        save([savefile_path int2str(iii+previous_iter_spike_num) '.mat'], 'data', '-v7')
    end
end

