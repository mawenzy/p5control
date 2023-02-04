from p5control import DataGateway, InstrumentGateway
import numpy as np

from time import sleep, time
from scipy.signal import savgol_filter as sg
from scipy.signal import find_peaks as fp
from scipy.optimize import curve_fit

# Pre - Definitions
def get_min_max_peaks(V, t, frequency, sweep_counts):
    window_length = int(10/frequency)
    smooth_V = sg(V, window_length=window_length, polyorder=1)
    dV = np.gradient(smooth_V)
    smooth_dV = sg(dV, window_length=window_length, polyorder=1)
    ddV = np.gradient(smooth_dV)
    smooth_ddV = sg(ddV, window_length=window_length, polyorder=1)

    symmetrical_ddV = smooth_ddV - np.mean(smooth_ddV)

    min_peaks = fp(symmetrical_ddV, height=.25*np.nanmax(symmetrical_ddV), distance=2*window_length)[0]
    max_peaks = fp(-symmetrical_ddV, height=.25*np.nanmax(symmetrical_ddV), distance=2*window_length)[0]

    if len(min_peaks) == len(max_peaks):
        min_peaks = np.append(min_peaks, [-1])
    return min_peaks, max_peaks

def get_up_down_sweep(array, mins, maxs):
    up = np.array([])
    down = np.array([])
    for i, p in enumerate(maxs):
        up = np.append(up, array[mins[i]:p])
        down = np.append(down, array[p:mins[i+1]])
    return up, down

def get_binned_current(voltage, current, bins):
    bins = np.append(bins, 2 * bins[-1] - bins[-2])
    _count, _ = np.histogram(voltage,
                            bins = bins,
                            weights=None)
    _count = np.array(_count, dtype='float64')
    _count[_count==0] = np.nan
    _sum, _ = np.histogram(voltage,
                        bins =bins,
                        weights=current)
    return _sum/_count

def calc_rms(x):
    return np.sqrt(np.nanmean(np.abs(x)**2))
    
def lin_fit_1(V, R, I_0_1, I_0_2):
        return V / R + I_0_1

def lin_fit_2(V, R, I_0_1, I_0_2):
        return V / R + I_0_2

def combined_lin_fit(VV, R, I_0_1, I_0_2):
    # single data reference passed in, extract separate data
    # assumes biggest jump in voltage to be dividing index
    index = np.argmax(VV[:-1]-VV[1:])
    res1 = lin_fit_1(VV[:index], R, I_0_1, I_0_2)
    res2 = lin_fit_2(VV[index:], R, I_0_1, I_0_2)
    return np.append(res1, res2)


#######################################################################################
class Measurements:
    def __init__(self):
        self.gw = InstrumentGateway()
        self.dgw = DataGateway()

        self.gw.connect()
        self.dgw.connect()

    def get_dataset(self, tic, toc, multi_keyword, hdf5_path='m000000'):
        # TODO slices
        multi = self.dgw.get_data(f"/measurement/{hdf5_path}/multi_{multi_keyword}/")
        time, V = multi['time'], multi['V']
        indices = np.argmin(np.abs(time-tic)), np.argmin(np.abs(time-toc))
        return time[indices[0]:indices[1]], V[indices[0]:indices[1]]

    def offset_measurement(self,
                            hdf5_path='m000000', parental_name='meta_data', name='offsets',
                            delay_time = .1, mean_fetch_time = .7,
                            offset_time = 1, max_current = .1):

        # setup bias_source to CV 0V output
        # TODO: if not setupped and not busy
        self.gw.source_bias.setup_offset_measurement(max_current=max_current)

        # wait for measurement
        if delay_time != 0:
            sleep(delay_time)
        tic = time()
        toc = tic + offset_time
        sleep(offset_time+mean_fetch_time)

        # get data from dgw
        ref_t, ref_V = self.get_dataset(tic, toc, multi_keyword='reference', hdf5_path=hdf5_path)
        sample_t, sample_V = self.get_dataset(tic, toc, multi_keyword='sample', hdf5_path=hdf5_path)
        source_t, source_V = self.get_dataset(tic, toc, multi_keyword='source', hdf5_path=hdf5_path)

        # get calculations done
        offset_source = np.mean(source_V)
        offset_sample = np.mean(sample_V)
        offset_ref = np.mean(ref_V)

        std_source = np.std(source_V)
        std_sample = np.std(sample_V)
        std_ref = np.std(ref_V)

        # save to data gateway
        path = f"{parental_name}/{hdf5_path}/{name}"

        my_dict = {'time': tic,
                'offset_source': offset_source,
                'offset_sample':offset_sample,
                'offset_ref': offset_ref,
                'std_source': std_source,
                'std_sample': std_sample,
                'std_ref': std_ref
                }

        self.dgw.append(
            path,
            my_dict,
            delay_time = delay_time,
            mean_fetch_time = mean_fetch_time,
            offset_time = offset_time,
            max_current = max_current
        )

    def sweep_measurement(self, 
                            hdf5_path='m000000', parental_name='meta', name='sweeps',
                            delay_time = .1, mean_fetch_time = .7,
                            amplitude = .3, frequency = 1, 
                            sweep_counts = 10, max_current = .3,
                            amplification_sample = 100,
                            amplification_reference = 100,
                            reference_resistance = 4.7E4,
                            bin_min=0, bin_max=0, bin_points=0,
                            exclusion_voltage=3.4E-4*5):

    
        # TODO
            # setup just if not setup and busy
            # divide in measurement and calc
                # measurement is opt. setup + performing
                # calculation is rest
            # make _save_data
            # get stuff from femto
            # get ref resistance from somewhere



        # setup bias_source to sweep mode
        # TODO: if not setupped and busy (implement in driver)
        self.gw.source_bias.setup_sweep_measurement(amplitude = amplitude,
                                                frequency = frequency,
                                                sweep_counts = sweep_counts, 
                                                max_current = max_current)

        # wait for measurement
        if delay_time != 0:
            sleep(delay_time)
        self.gw.source_bias.trigger_measurment()
        tic = time()
        tic = tic - delay_time
        toc = tic + sweep_counts / frequency + 2 * delay_time
        sleep(sweep_counts / frequency + mean_fetch_time)

        # get data from dgw
        ref_t, ref_V = self.get_dataset(tic, toc, multi_keyword='reference', hdf5_path=hdf5_path)
        sample_t, sample_V = self.get_dataset(tic, toc, multi_keyword='sample', hdf5_path=hdf5_path)
        source_t, source_V = self.get_dataset(tic, toc, multi_keyword='source', hdf5_path=hdf5_path)

        print(len(ref_t), len(sample_t), len(source_t))
        # while not "same" ask again

        # get Offsets
        offset_sample = 0
        offset_reference = 0

        # get current and voltage
        voltage = ( sample_V - offset_sample ) / amplification_sample
        current = ( ref_V - offset_reference ) / amplification_reference / reference_resistance

        # get min und max peak indices
        mins, maxs = get_min_max_peaks(source_V, source_t, frequency, sweep_counts)

        # get up and down sweeps
        voltage_upsweep, voltage_downsweep = get_up_down_sweep(voltage, mins, maxs)
        current_upsweep, current_downsweep = get_up_down_sweep(current, mins, maxs)

        sample_upsweep_t, sample_downsweep_t = get_up_down_sweep(sample_t, mins, maxs)
        ref_upsweep_t, ref_downsweep_t = get_up_down_sweep(ref_t, mins, maxs)

        # get binned voltage and currents
        ## get binned voltage
        if bin_min==0:
            bin_min = np.max([np.nanmin(voltage_downsweep), np.nanmin(voltage_upsweep)])
        if bin_max==0:
            bin_max = np.min([np.nanmax(voltage_downsweep), np.nanmax(voltage_upsweep)])
        if bin_points==0:
            bin_points = sweep_counts / frequency * 500
            # sampling rate / 2 weil up and down
        binned_voltage = np.linspace(bin_min, bin_max, int(bin_points))

        ## get binned currents
        binned_current_downsweep = get_binned_current(voltage_downsweep, current_downsweep, binned_voltage)
        binned_current_upsweep = get_binned_current(voltage_upsweep, current_upsweep, binned_voltage)

        # get resistances
        ## exclude gap data
        _logic_binned = (np.abs(binned_voltage) <= exclusion_voltage)

        binned_voltage_excluded = binned_voltage
        binned_current_upsweep_excluded = binned_current_upsweep
        binned_current_downsweep_excluded = binned_current_downsweep

        binned_voltage_excluded[_logic_binned] = np.nan
        binned_current_upsweep_excluded[_logic_binned] = np.nan
        binned_current_downsweep_excluded[_logic_binned] = np.nan

        ## get from min and max
        min_binned_voltage_excluded = np.nanmin(binned_voltage_excluded)
        max_binned_voltage_excluded = np.nanmax(binned_voltage_excluded)
        min_binned_current_excluded = np.nanmin([np.nanmin(binned_current_upsweep_excluded),
                                                np.nanmin(binned_current_downsweep_excluded)])
        max_binned_current_excluded = np.nanmax([np.nanmax(binned_current_upsweep_excluded),
                                                np.nanmax(binned_current_downsweep_excluded)])
        R_max = ( max_binned_voltage_excluded - min_binned_voltage_excluded ) / (
                max_binned_current_excluded - min_binned_current_excluded )

        ## get from rms
        rms_binned_voltage_excluded = calc_rms(binned_voltage_excluded)
        rms_binned_current_excluded = calc_rms(np.append(binned_current_upsweep_excluded,
                                                        binned_current_downsweep_excluded))
        R_rms = rms_binned_voltage_excluded / rms_binned_current_excluded

        ## get from lin fit
        ### remove nans
        _logic = ~np.isnan(binned_voltage_excluded)
        binned_voltage_excluded_without_nan = binned_voltage_excluded[_logic]
        binned_current_upsweep_excluded_without_nan = binned_current_upsweep_excluded[_logic]
        binned_current_downsweep_excluded_without_nan = binned_current_downsweep_excluded[_logic]

        _logic_C1 = ~np.isnan(binned_current_upsweep_excluded_without_nan)
        binned_voltage_upsweep_excluded_without_nan = binned_voltage_excluded_without_nan[_logic_C1]
        binned_current_upsweep_excluded_without_nan = binned_current_upsweep_excluded_without_nan[_logic_C1]

        _logic_C2 = ~np.isnan(binned_current_downsweep_excluded_without_nan)
        binned_voltage_downsweep_excluded_without_nan = binned_voltage_excluded_without_nan[_logic_C2]
        binned_current_downsweep_excluded_without_nan = binned_current_downsweep_excluded_without_nan[_logic_C2]

        ### combined arrays
        _voltages_to_fit = np.append(binned_voltage_upsweep_excluded_without_nan,
                                    binned_voltage_downsweep_excluded_without_nan)
        
        _currents_to_fit = np.append(binned_current_upsweep_excluded_without_nan,
                                    binned_current_downsweep_excluded_without_nan)

        ### get R from combined fit
        [R_lin, I_0_1, I_0_2], _ = curve_fit(combined_lin_fit, 
                                            _voltages_to_fit,
                                            _currents_to_fit)

        # save to data gateway (TODO)
        path = f"{parental_name}/{hdf5_path}/{name}"

        ## save resistances   
        my_dict = {'time': tic,
                'R_max': R_max,
                'R_rms': R_rms,
                'R_lin': R_lin,
                'I_0_1': I_0_1,
                'I_0_2': I_0_2,
                }
        self.dgw.append(
            f"{path}/resistances",
            my_dict,
            test_keyword = 'test'
        )

'''
# probably class?
from time import sleep, time
from numpy import mean, std


# Pre - Definitions
def get_dataset(dgw, tic, toc, multi_keyword, hdf5_path='m000000'):
    # TODO slices
    multi = dgw.get_data(f"/measurement/{hdf5_path}/multi_{multi_keyword}/")
    time, V = multi['time'], multi['V']
    indices = np.argmin(np.abs(time-tic)), np.argmin(np.abs(time-toc))
    return time[indices[0]:indices[1]], V[indices[0]:indices[1]]

# Definition of the Offset Measurement Function
def offset_measurement(gw, dgw, 
                        hdf5_path='m000000', parental_name='meta_data', name='offsets',
                        delay_time = .1, mean_fetch_time = .7,
                        offset_time = 1, max_current = .1):

    # setup bias_source to CV 0V output
    # TODO: if not setupped and not busy
    gw.source_bias.setup_offset_measurement(max_current=max_current)

    # wait for measurement
    if delay_time != 0:
        sleep(delay_time)
    tic = time()
    toc = tic + offset_time
    sleep(offset_time+mean_fetch_time)

    # get data from dgw
    ref_t, ref_V = get_dataset(dgw, tic, toc, multi_keyword='reference', hdf5_path=hdf5_path)
    sample_t, sample_V = get_dataset(dgw, tic, toc, multi_keyword='sample', hdf5_path=hdf5_path)
    source_t, source_V = get_dataset(dgw, tic, toc, multi_keyword='source', hdf5_path=hdf5_path)

    # get calculations done
    offset_source = mean(source_V)
    offset_sample = mean(sample_V)
    offset_ref = mean(ref_V)

    std_source = std(source_V)
    std_sample = std(sample_V)
    std_ref = std(ref_V)

    # save to data gateway
    path = f"{parental_name}/{hdf5_path}/{name}"

    my_dict = {'time': tic,
               'offset_source': offset_source,
               'offset_sample':offset_sample,
               'offset_ref': offset_ref,
               'std_source': std_source,
               'std_sample': std_sample,
               'std_ref': std_ref
            }

    dgw.append(
        path,
        my_dict,
        delay_time = delay_time,
        mean_fetch_time = mean_fetch_time,
        offset_time = offset_time,
        max_current = max_current
    )


'''


'''from time import sleep, time
from scipy.signal import savgol_filter as sg
from scipy.signal import find_peaks as fp
from scipy.optimize import curve_fit
import numpy as np


# Pre - Definitions

def get_dataset(dgw, tic, toc, multi_keyword, hdf5_path='m000000'):
    # TODO slices
    multi = dgw.get_data(f"/measurement/{hdf5_path}/multi_{multi_keyword}/")
    time, V = multi['time'], multi['V']
    indices = np.argmin(np.abs(time-tic)), np.argmin(np.abs(time-toc))
    return time[indices[0]:indices[1]], V[indices[0]:indices[1]]

def get_min_max_peaks(V, t, frequency, sweep_counts):
    window_length = int(10/frequency)
    smooth_V = sg(V, window_length=window_length, polyorder=1)
    dV = np.gradient(smooth_V)
    smooth_dV = sg(dV, window_length=window_length, polyorder=1)
    ddV = np.gradient(smooth_dV)
    smooth_ddV = sg(ddV, window_length=window_length, polyorder=1)

    symmetrical_ddV = smooth_ddV - np.mean(smooth_ddV)

    min_peaks = fp(symmetrical_ddV, height=.25*np.nanmax(symmetrical_ddV), distance=2*window_length)[0]
    max_peaks = fp(-symmetrical_ddV, height=.25*np.nanmax(symmetrical_ddV), distance=2*window_length)[0]

    if len(min_peaks) == len(max_peaks):
        min_peaks = np.append(min_peaks, [-1])
    return min_peaks, max_peaks

def get_up_down_sweep(array, mins, maxs):
    up = np.array([])
    down = np.array([])
    for i, p in enumerate(maxs):
        up = np.append(up, array[mins[i]:p])
        down = np.append(down, array[p:mins[i+1]])
    return up, down

def get_binned_current(voltage, current, bins):
    bins = np.append(bins, 2 * bins[-1] - bins[-2])
    _count, _ = np.histogram(voltage,
                            bins = bins,
                            weights=None)
    _count = np.array(_count, dtype='float64')
    _count[_count==0] = np.nan
    _sum, _ = np.histogram(voltage,
                        bins =bins,
                        weights=current)
    return _sum/_count

def calc_rms(x):
    return np.sqrt(np.nanmean(np.abs(x)**2))
    
def lin_fit_1(V, R, I_0_1, I_0_2):
        return V / R + I_0_1

def lin_fit_2(V, R, I_0_1, I_0_2):
        return V / R + I_0_2

def combined_lin_fit(VV, R, I_0_1, I_0_2):
    # single data reference passed in, extract separate data
    # assumes biggest jump in voltage to be dividing index
    index = np.argmax(VV[:-1]-VV[1:])
    res1 = lin_fit_1(VV[:index], R, I_0_1, I_0_2)
    res2 = lin_fit_2(VV[index:], R, I_0_1, I_0_2)
    return np.append(res1, res2)



# Definition of the Offset Measurement Function

def sweep_measurement(gw, dgw, 
                        hdf5_path='m000000', parental_name='meta', name='sweeps',
                        delay_time = .1, mean_fetch_time = .7,
                        amplitude = .3, frequency = 1, 
                        sweep_counts = 10, max_current = .3,
                        amplification_sample = 100,
                        amplification_reference = 100,
                        reference_resistance = 4.7E4,
                        bin_min=0, bin_max=0, bin_points=0,
                        exclusion_voltage=3.4E-4*5):
    
    # TODO
        # setup just if not setup and busy
        # divide in measurement and calc
            # measurement is opt. setup + performing
            # calculation is rest
        # make _save_data
        # get stuff from femto
        # get ref resistance from somewhere



    # setup bias_source to sweep mode
    # TODO: if not setupped and busy
    gw.source_bias.setup_sweep_measurement(amplitude = amplitude,
                                            frequency = frequency,
                                            sweep_counts = sweep_counts, 
                                            max_current = max_current)

    # wait for measurement
    if delay_time != 0:
        sleep(delay_time)
    gw.source_bias.trigger_measurment()
    tic = time()
    tic = tic - delay_time
    toc = tic + sweep_counts / frequency + 2 * delay_time
    sleep(sweep_counts / frequency + mean_fetch_time)

    # get data from dgw
    ref_t, ref_V = get_dataset(dgw, tic, toc, multi_keyword='reference', hdf5_path=hdf5_path)
    sample_t, sample_V = get_dataset(dgw, tic, toc, multi_keyword='sample', hdf5_path=hdf5_path)
    source_t, source_V = get_dataset(dgw, tic, toc, multi_keyword='source', hdf5_path=hdf5_path)

    print(len(ref_t), len(sample_t), len(source_t))
    # while not "same" ask again

    # get Offsets
    offset_sample = 0
    offset_reference = 0

    # get current and voltage
    voltage = ( sample_V - offset_sample ) / amplification_sample
    current = ( ref_V - offset_reference ) / amplification_reference / reference_resistance

    # get min und max peak indices
    mins, maxs = get_min_max_peaks(source_V, source_t, frequency, sweep_counts)

    # get up and down sweeps
    voltage_upsweep, voltage_downsweep = get_up_down_sweep(voltage, mins, maxs)
    current_upsweep, current_downsweep = get_up_down_sweep(current, mins, maxs)

    sample_upsweep_t, sample_downsweep_t = get_up_down_sweep(sample_t, mins, maxs)
    ref_upsweep_t, ref_downsweep_t = get_up_down_sweep(ref_t, mins, maxs)

    # get binned voltage and currents
    ## get binned voltage
    if bin_min==0:
        bin_min = np.max([np.nanmin(voltage_downsweep), np.nanmin(voltage_upsweep)])
    if bin_max==0:
        bin_max = np.min([np.nanmax(voltage_downsweep), np.nanmax(voltage_upsweep)])
    if bin_points==0:
        bin_points = sweep_counts / frequency * 500
        # sampling rate / 2 weil up and down
    binned_voltage = np.linspace(bin_min, bin_max, int(bin_points))

    print(np.shape(voltage_downsweep), np.shape(current_downsweep))
    ## get binned currents
    binned_current_downsweep = get_binned_current(voltage_downsweep, current_downsweep, binned_voltage)
    binned_current_upsweep = get_binned_current(voltage_upsweep, current_upsweep, binned_voltage)

    # get resistances
    ## exclude gap data
    _logic_binned = (np.abs(binned_voltage) <= exclusion_voltage)

    binned_voltage_excluded = binned_voltage
    binned_current_upsweep_excluded = binned_current_upsweep
    binned_current_downsweep_excluded = binned_current_downsweep

    binned_voltage_excluded[_logic_binned] = np.nan
    binned_current_upsweep_excluded[_logic_binned] = np.nan
    binned_current_downsweep_excluded[_logic_binned] = np.nan

    ## get from min and max
    min_binned_voltage_excluded = np.nanmin(binned_voltage_excluded)
    max_binned_voltage_excluded = np.nanmax(binned_voltage_excluded)
    min_binned_current_excluded = np.nanmin([np.nanmin(binned_current_upsweep_excluded),
                                             np.nanmin(binned_current_downsweep_excluded)])
    max_binned_current_excluded = np.nanmax([np.nanmax(binned_current_upsweep_excluded),
                                             np.nanmax(binned_current_downsweep_excluded)])
    R_max = ( max_binned_voltage_excluded - min_binned_voltage_excluded ) / (
              max_binned_current_excluded - min_binned_current_excluded )

    ## get from rms
    rms_binned_voltage_excluded = calc_rms(binned_voltage_excluded)
    rms_binned_current_excluded = calc_rms(np.append(binned_current_upsweep_excluded,
                                                     binned_current_downsweep_excluded))
    R_rms = rms_binned_voltage_excluded / rms_binned_current_excluded

    ## get from lin fit
    ### remove nans
    _logic = ~np.isnan(binned_voltage_excluded)
    binned_voltage_excluded_without_nan = binned_voltage_excluded[_logic]
    binned_current_upsweep_excluded_without_nan = binned_current_upsweep_excluded[_logic]
    binned_current_downsweep_excluded_without_nan = binned_current_downsweep_excluded[_logic]

    _logic_C1 = ~np.isnan(binned_current_upsweep_excluded_without_nan)
    binned_voltage_upsweep_excluded_without_nan = binned_voltage_excluded_without_nan[_logic_C1]
    binned_current_upsweep_excluded_without_nan = binned_current_upsweep_excluded_without_nan[_logic_C1]

    _logic_C2 = ~np.isnan(binned_current_downsweep_excluded_without_nan)
    binned_voltage_downsweep_excluded_without_nan = binned_voltage_excluded_without_nan[_logic_C2]
    binned_current_downsweep_excluded_without_nan = binned_current_downsweep_excluded_without_nan[_logic_C2]

    ### combined arrays
    _voltages_to_fit = np.append(binned_voltage_upsweep_excluded_without_nan,
                                 binned_voltage_downsweep_excluded_without_nan)
    
    _currents_to_fit = np.append(binned_current_upsweep_excluded_without_nan,
                                 binned_current_downsweep_excluded_without_nan)

    ### get R from combined fit
    [R_lin, I_0_1, I_0_2], _ = curve_fit(combined_lin_fit, 
                                        _voltages_to_fit,
                                        _currents_to_fit)

    # save to data gateway (TODO)
    path = f"{parental_name}/{hdf5_path}/{name}"

    ## save resistances   
    my_dict = {'time': tic,
               'R_max': R_max,
               'R_rms': R_rms,
               'R_lin': R_lin,
               'I_0_1': I_0_1,
               'I_0_2': I_0_2,
            }
    dgw.append(
        f"{path}/resistances",
        my_dict,
        test_keyword = 'test'
    )


    # Arrays
    
    # Single Values

    # keywords
        # delay_time = delay_time,
        # mean_fetch_time = mean_fetch_time,
        # amplitude = amplitude,
        # frequency = frequency,
        # sweep_counts = sweep_counts,
        # max_current = max_current,
        # amplification_sample=amplification_sample,
        # amplification_reference=amplification_reference,
        # reference_resistance = reference_resistance,
        # voltage_bin_min = bin_min,
        # voltage_bin_max = bin_max,
        # voltage_bin_points = bin_points,
        # exclusion_voltage = exclusion_voltage,

    # dgw.append(
    #     path,
    #     my_dict,
    #     test='test'
    # )

'''