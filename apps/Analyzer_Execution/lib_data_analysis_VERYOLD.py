"""
Library Features:

Name:          lib_data_analysis
Author(s):     Fabio Delogu (fabio.delogu@cimafoundation.org)
Date:          '20210225'
Version:       '1.0.0'
"""
#######################################################################################
# Library
import logging

import pandas as pd
from copy import deepcopy

from lib_info_args import logger_name

# Logging
log_stream = logging.getLogger(logger_name)
#######################################################################################


# -------------------------------------------------------------------------------------
# method to select discharge columns by tag
def filter_discharge_ts_by_tag(section_dframe,
                            tag_discharge_simulated='discharge_simulated',
                            tag_discharge_observed='discharge_observed'):

    if '{:}' in tag_discharge_simulated:
        tag_root_simulated = tag_discharge_simulated.strip('{:}')
        tag_root_simulated = tag_root_simulated.strip('_')
    else:
        tag_root_simulated = deepcopy(tag_discharge_simulated)
    if '{:}' in tag_discharge_observed:
        tag_root_observed = tag_discharge_simulated.strip('{:}')
        tag_root_observed = tag_root_observed.strip('_')
    else:
        tag_root_observed = deepcopy(tag_discharge_observed)

    section_dframe_simulated = section_dframe[section_dframe.columns[
        section_dframe.columns.str.contains(tag_root_simulated, na=False, case=False)]]
    section_dframe_observed = section_dframe[section_dframe.columns[
        section_dframe.columns.str.contains(tag_root_observed, na=False, case=False)]]

    return section_dframe_simulated, section_dframe_observed

# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# method to select discharge columns by limits
def filter_discharge_ts_by_limits(section_dframe_generic, section_attrs, discharge_min=0, discharge_max=None):

    ts_vars = section_attrs['run_var'].split(',')
    if isinstance(ts_vars, str):
        ts_n_exp = 1
    else:
        ts_n_exp = ts_vars.__len__()

    # remove nans ts
    section_dframe_tmp = section_dframe_generic.dropna(axis=1, how='all')
    # keep ts ge min
    if discharge_min is not None:
        index_finite = section_dframe_tmp.ge(discharge_min).any()
        section_dframe_tmp = section_dframe_tmp.loc[:, index_finite]
    # keep th le max
    if discharge_max is not None:
        index_finite = section_dframe_tmp.le(discharge_max).any()
        section_dframe_tmp = section_dframe_tmp.loc[:, index_finite]

    section_dframe_filtered = deepcopy(section_dframe_tmp)
    if not section_dframe_filtered.empty:
        ts_n_filter = list(section_dframe_filtered.columns).__len__()
    else:
        ts_n_filter = 0
        log_stream.warning(' ===> The filtered DataFrame by limits is empty')

    section_dframe_filtered.attrs['ts_exp'] = ts_n_exp
    section_dframe_filtered.attrs['ts_filter'] = ts_n_filter

    return section_dframe_filtered
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to analyze discharge time series
def analyze_discharge_ts(run_name, file_datasets,
                         tag_discharge_observed='discharge_observed',
                         tag_discharge_simulated='discharge_simulated',
                         tag_discharge_thr_alert='section_discharge_thr_alert',
                         tag_discharge_thr_alarm='section_discharge_thr_alarm',
                         tag_discharge_max_alert_value='discharge_alert_max_value',
                         tag_discharge_max_alert_index='discharge_alert_max_index',
                         tag_discharge_max_alarm_value='discharge_alarm_max_value',
                         tag_discharge_max_alarm_index='discharge_alarm_max_index',
                         tag_section_n='section_n', tag_run_n='run_n',
                         tag_run_type='run_type'):

    log_stream.info(' ----> Analyze discharge time-series  ... ')
    if file_datasets is not None:
        section_n = file_datasets.__len__()

        analysis_datasets_section, attrs_ts_collections = {}, None
        for section_tag, section_datasets in file_datasets.items():

            log_stream.info(' -----> Section "' + section_tag + '" ... ')

            if section_datasets is not None:

                section_dframe = section_datasets[0]
                section_attrs = section_datasets[1]

                section_ts_vars = section_attrs['run_var'].split(',')
                data_thr_alert = float(section_attrs['section_discharge_thr_alert'])
                data_thr_alarm = float(section_attrs['section_discharge_thr_alarm'])

                if data_thr_alert < 0:
                    log_stream.warning(' ===> Threshold alarm is equal to "' + str(data_thr_alert) +
                                       '" is less then 0. The threshold is set to NoneType')
                    data_thr_alert = None
                if data_thr_alarm < 0:
                    log_stream.warning(' ===> Threshold alarm is equal to "' + str(data_thr_alarm) +
                                       '" is less then 0. The threshold is set to NoneType')
                    data_thr_alarm = None


                '''
                # DEBUG
                data_thr_alert, data_thr_alarm = 1, 10
                '''
                section_ts_time = section_dframe.index
                section_ts_days = section_ts_time[1:].normalize().unique()

                # filter dframe according to the tag
                section_dframe_simulated, section_dframe_observed = filter_discharge_ts_by_tag(
                    section_dframe,
                    tag_discharge_simulated=tag_discharge_simulated, tag_discharge_observed=tag_discharge_observed)
                # filter dframe by limits and nans
                section_dframe_simulated = filter_discharge_ts_by_limits(section_dframe_simulated, section_attrs)

                section_thr_collections = {}
                for section_ts_step in section_ts_days:

                    # init thr collections
                    section_thr_collections[section_ts_step] = {}
                    section_thr_collections[section_ts_step][tag_discharge_max_alert_value] = {}
                    section_thr_collections[section_ts_step][tag_discharge_max_alert_index] = {}
                    section_thr_collections[section_ts_step][tag_discharge_max_alarm_value] = {}
                    section_thr_collections[section_ts_step][tag_discharge_max_alarm_index] = {}

                    ts_day, ts_month, ts_year = section_ts_step.day, section_ts_step.month, section_ts_step.year
                    section_dframe_day = section_dframe_simulated.loc[
                                         (section_dframe_simulated.index.day == ts_day) &
                                         (section_dframe_simulated.index.month == ts_month) &
                                         (section_dframe_simulated.index.year == ts_year), :]

                    if data_thr_alert is not None:
                        section_dframe_thr_alert = section_dframe_day.where(
                            section_dframe_day.values > data_thr_alert).dropna()
                        section_value_thr_alert_max = section_dframe_thr_alert.max(skipna=True, axis=1).max()
                        section_value_thr_alert_idxmax = section_dframe_thr_alert.max(skipna=True, axis=1).idxmax()
                    else:
                        section_value_thr_alert_max, section_value_thr_alert_idxmax = None, None
                    if data_thr_alarm is not None:
                        section_dframe_thr_alarm = section_dframe_day.where(
                            section_dframe_day.values > data_thr_alarm).dropna()
                        section_value_thr_alarm_max = section_dframe_thr_alarm.max(skipna=True, axis=1).max()
                        section_value_thr_alarm_idxmax = section_dframe_thr_alarm.max(skipna=True, axis=1).idxmax()
                    else:
                        section_value_thr_alarm_max, section_value_thr_alarm_idxmax = None, None

                    section_thr_collections[section_ts_step][tag_discharge_max_alert_value] = section_ts_alert_max_value
                    section_thr_collections[section_ts_step][tag_discharge_max_alert_index] = section_ts_alert_max_index
                    section_thr_collections[section_ts_step][tag_discharge_max_alarm_value] = section_ts_alarm_max_value
                    section_thr_collections[section_ts_step][tag_discharge_max_alarm_index] = section_ts_alarm_max_index
                    section_thr_collections[section_ts_step][tag_discharge_thr_alert] = data_thr_alert
                    section_thr_collections[section_ts_step][tag_discharge_thr_alarm] = data_thr_alarm
                    section_thr_collections[section_ts_step][tag_run_type] = run_name

                    if attrs_ts_collections is None:
                        attrs_ts_collections = {tag_run_n: run_n, tag_section_n: section_n, tag_run_type: run_name}

                analysis_datasets_section[section_tag] = section_ts_collections

                    if data_thr_alarm is not None:
                        section_ts_thr_alarm_var = section_ts_sim_var.where(section_ts_sim_var > data_thr_alarm)
                        section_ts_alarm_max_value_var = section_ts_thr_alarm_var.max(skipna=True)
                        section_ts_alarm_max_index_var = section_ts_thr_alarm_var.idxmax(skipna=True)
                    else:
                        section_ts_alarm_max_value_var, section_ts_alarm_max_index_var = None, None

                    if section_ts_alert_max_index_var not in section_ts_alert_max_index_list:
                        section_ts_alert_max_value_list.append(section_ts_alert_max_value_var)
                        section_ts_alert_max_index_list.append(section_ts_alert_max_index_var)
                    if section_ts_alarm_max_index_var not in section_ts_alarm_max_index_list:
                        section_ts_alarm_max_value_list.append(section_ts_alarm_max_value_var)
                        section_ts_alarm_max_index_list.append(section_ts_alarm_max_index_var)



                # Create analysis datasets section
                if section_ts_vars.__len__() == 1:

                    run_n = 1

                    section_ts_collections = {}
                    for section_ts_step in section_ts_days:

                        section_ts_collections[section_ts_step] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alert_value] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alert_index] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_value] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_index] = {}

                        ts_day, ts_month, ts_year = section_ts_step.day, section_ts_step.month, section_ts_step.year

                        section_dframe_day = section_dframe.loc[
                                             (section_dframe.index.day == ts_day) &
                                             (section_dframe.index.month == ts_month) &
                                             (section_dframe.index.year == ts_year), :]

                        section_ts_day_sim = section_dframe_day[tag_discharge_simulated]
                        section_ts_day_obs = section_dframe_day[tag_discharge_observed]

                        if data_thr_alert is not None:
                            section_ts_thr_alert = section_ts_day_sim.where(section_ts_day_sim > data_thr_alert)
                            section_ts_alert_max_value = section_ts_thr_alert.max(skipna=True)
                            section_ts_alert_max_index = section_ts_thr_alert.idxmax(skipna=True)
                        else:
                            section_ts_alert_max_value, section_ts_alert_max_index = None, None
                        if data_thr_alarm is not None:
                            section_ts_thr_alarm = section_ts_day_sim.where(section_ts_day_sim > data_thr_alarm)
                            section_ts_alarm_max_value = section_ts_thr_alarm.max(skipna=True)
                            section_ts_alarm_max_index = section_ts_thr_alarm.idxmax(skipna=True)
                        else:
                            section_ts_alarm_max_value, section_ts_alarm_max_index = None, None

                        section_ts_collections[section_ts_step][tag_discharge_max_alert_value] = section_ts_alert_max_value
                        section_ts_collections[section_ts_step][tag_discharge_max_alert_index] = section_ts_alert_max_index
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_value] = section_ts_alarm_max_value
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_index] = section_ts_alarm_max_index
                        section_ts_collections[section_ts_step][tag_discharge_thr_alert] = data_thr_alert
                        section_ts_collections[section_ts_step][tag_discharge_thr_alarm] = data_thr_alarm
                        section_ts_collections[section_ts_step][tag_run_type] = run_name

                    if attrs_ts_collections is None:
                        attrs_ts_collections = {tag_run_n: run_n, tag_section_n: section_n, tag_run_type: run_name}
                else:

                    run_n = section_ts_vars.__len__()

                    section_ts_collections = {}
                    for section_ts_step in section_ts_days:

                        section_ts_collections[section_ts_step] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alert_value] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alert_index] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_value] = {}
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_index] = {}
                        section_ts_collections[section_ts_step][tag_discharge_thr_alert] = {}
                        section_ts_collections[section_ts_step][tag_discharge_thr_alarm] = {}

                        ts_day, ts_month, ts_year = section_ts_step.day, section_ts_step.month, section_ts_step.year

                        section_ts_alert_max_value_list, section_ts_alert_max_index_list = [], []
                        section_ts_alarm_max_value_list, section_ts_alarm_max_index_list = [], []
                        for section_ts_var in section_ts_vars:

                            tag_discharge_simulated_var = tag_discharge_simulated.format(section_ts_var)
                            tag_discharge_observed_var = tag_discharge_observed.format(section_ts_var)

                            section_dframe_day = section_dframe.loc[
                                                 (section_dframe.index.day == ts_day) &
                                                 (section_dframe.index.month == ts_month) &
                                                 (section_dframe.index.year == ts_year), :]

                            section_ts_sim_var = section_dframe_day[tag_discharge_simulated_var]
                            section_ts_obs_var = section_dframe_day[tag_discharge_observed_var]

                            if data_thr_alert is not None:
                                section_ts_thr_alert_var = section_ts_sim_var.where(section_ts_sim_var > data_thr_alert)
                                section_ts_alert_max_value_var = section_ts_thr_alert_var.max(skipna=True)
                                section_ts_alert_max_index_var = section_ts_thr_alert_var.idxmax(skipna=True)
                            else:
                                section_ts_alert_max_value_var, section_ts_alert_max_index_var = None, None
                            if data_thr_alarm is not None:
                                section_ts_thr_alarm_var = section_ts_sim_var.where(section_ts_sim_var > data_thr_alarm)
                                section_ts_alarm_max_value_var = section_ts_thr_alarm_var.max(skipna=True)
                                section_ts_alarm_max_index_var = section_ts_thr_alarm_var.idxmax(skipna=True)
                            else:
                                section_ts_alarm_max_value_var, section_ts_alarm_max_index_var = None, None

                            if section_ts_alert_max_index_var not in section_ts_alert_max_index_list:
                                section_ts_alert_max_value_list.append(section_ts_alert_max_value_var)
                                section_ts_alert_max_index_list.append(section_ts_alert_max_index_var)
                            if section_ts_alarm_max_index_var not in section_ts_alarm_max_index_list:
                                section_ts_alarm_max_value_list.append(section_ts_alarm_max_value_var)
                                section_ts_alarm_max_index_list.append(section_ts_alarm_max_index_var)

                        '''
                        # DEBUG
                        section_ts_alert_max_value_list = [2.65, 2.71, 2.74]
                        section_ts_alert_max_index_list = [pd.Timestamp('2021-03-18 00:00:00'), pd.Timestamp('2021-03-18 19:00:00'), pd.Timestamp('2021-03-18 20:00:00')]
                        '''

                        if section_ts_alert_max_value_list.__len__() > 1:
                            idx_max = section_ts_alert_max_value_list.index(max(section_ts_alert_max_value_list))
                            section_ts_alert_max_value_list = [section_ts_alert_max_value_list[idx_max]]
                            section_ts_alert_max_index_list = [section_ts_alert_max_index_list[idx_max]]

                        if section_ts_alarm_max_value_list.__len__() > 1:
                            idx_max = section_ts_alarm_max_value_list.index(max(section_ts_alarm_max_value_list))
                            section_ts_alarm_max_value_list = [section_ts_alarm_max_value_list[idx_max]]
                            section_ts_alarm_max_index_list = [section_ts_alarm_max_index_list[idx_max]]

                        section_ts_thr_alert_max = pd.Series([section_ts_alert_max_value_list])
                        section_ts_thr_alert_max.index = section_ts_alert_max_index_list
                        section_ts_thr_alarm_max = pd.Series([section_ts_alarm_max_value_list])
                        section_ts_thr_alarm_max.index = section_ts_alarm_max_index_list

                        if section_ts_thr_alert_max.shape[0] == 1:
                            section_ts_alert_max_value = section_ts_thr_alert_max.values[0]
                            section_ts_alert_max_index = section_ts_thr_alert_max.index[0]
                        else:
                            section_ts_alert_max_value = section_ts_thr_alert_max.max(skipna=True)
                            section_ts_alert_max_index = section_ts_thr_alert_max.idxmax(skipna=True)

                        if section_ts_thr_alarm_max.shape[0] == 1:
                            section_ts_alarm_max_value = section_ts_thr_alarm_max.values[0]
                            section_ts_alarm_max_index = section_ts_thr_alarm_max.index[0]
                        else:
                            section_ts_alarm_max_value = section_ts_thr_alarm_max.max(skipna=True)
                            section_ts_alarm_max_index = section_ts_thr_alarm_max.idxmax(skipna=True)

                        if isinstance(section_ts_alert_max_value, list):
                            if section_ts_alert_max_value.__len__() == 1:
                                section_ts_alert_max_value = section_ts_alert_max_value[0]
                            else:
                                log_stream.error(' ===> Analysis has defined the max alert value in unsupported format')
                                raise NotImplemented('Case not implemented yet')

                        if isinstance(section_ts_alarm_max_value, list):
                            if section_ts_alarm_max_value.__len__() == 1:
                                section_ts_alarm_max_value = section_ts_alarm_max_value[0]
                            else:
                                log_stream.error(' ===> Analysis has defined the max alarm value in unsupported format')
                                raise NotImplemented('Case not implemented yet')

                        section_ts_collections[section_ts_step][tag_discharge_max_alert_value] = section_ts_alert_max_value
                        section_ts_collections[section_ts_step][tag_discharge_max_alert_index] = section_ts_alert_max_index
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_value] = section_ts_alarm_max_value
                        section_ts_collections[section_ts_step][tag_discharge_max_alarm_index] = section_ts_alarm_max_index
                        section_ts_collections[section_ts_step][tag_discharge_thr_alert] = data_thr_alert
                        section_ts_collections[section_ts_step][tag_discharge_thr_alarm] = data_thr_alarm
                        section_ts_collections[section_ts_step][tag_run_type] = run_name

                        if attrs_ts_collections is None:
                            attrs_ts_collections = {tag_run_n: run_n, tag_section_n: section_n, tag_run_type: run_name}

                analysis_datasets_section[section_tag] = section_ts_collections

                log_stream.info(' -----> Section "' + section_tag + '" ... DONE')

            else:
                analysis_datasets_section[section_tag] = None
                log_stream.info(' -----> Section "' + section_tag + '" ... SKIPPED. Datasets is undefined')

        log_stream.info(' ----> Analyze discharge time-series  ... DONE')

    else:
        log_stream.info(' ----> Analyze discharge time-series  ... SKIPPED. Datasets are undefined')
        analysis_datasets_section, attrs_ts_collections = None, None

    return analysis_datasets_section, attrs_ts_collections

# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# Method to analyze time information
def analyze_time_info(file_info_start, file_info_end, tag_file_reference='file_create'):

    time_ref_start = define_time_reference(
        file_info_start, tag_file_reference=tag_file_reference)
    time_ref_end = define_time_reference(
        file_info_end, tag_file_reference=tag_file_reference)

    if (time_ref_start is not None) and (time_ref_end is not None):
        time_ref_elapsed = time_ref_end[0] - time_ref_start[0]

        if isinstance(time_ref_start, list) and (time_ref_start.__len__() == 1):
            time_ref_start = time_ref_start[0]
        else:
            log_stream.error(' ===> The format of "time_ref_start" is not supported')
            raise NotImplemented('Case not implemented yet')

        if isinstance(time_ref_end, list) and (time_ref_end.__len__() == 1):
            time_ref_end = time_ref_end[0]
        else:
            log_stream.error(' ===> The format of "time_ref_end" is not supported')
            raise NotImplemented('Case not implemented yet')

        if time_ref_start > time_ref_end:
            log_stream.warning(' ===> The case between "time_ref_start" < "time_ref_end" is not expected')
            time_ref_end, time_ref_elapsed = None, None
        elif time_ref_start <= time_ref_end:
            pass
        else:
            log_stream.error(' ===> The case between "time_ref_start" and "time_ref_end" is not supported')
            raise NotImplemented('Case not implemented yet')

    elif (time_ref_start is not None) and (time_ref_end is None):
        time_ref_end, time_ref_elapsed = None, None
    else:
        log_stream.error(' ===> The case of "time_ref_start" and ""time_ref_end" is not supported')
        raise NotImplemented('Case not implemented yet')

    return time_ref_start, time_ref_end, time_ref_elapsed

# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# Method to define file reference
def define_time_reference(file_info, tag_file_reference='file_create'):

    if file_info is not None:
        if isinstance(file_info, dict):

            if tag_file_reference in list(file_info.keys()):
                file_time_reference = [file_info[tag_file_reference]]
            else:
                file_time_list = []
                for file_key, file_values in file_info.items():
                    if file_values is not None:
                        if tag_file_reference in list(file_values.keys()):
                            file_time_step = file_values[tag_file_reference]
                            file_time_list.append(file_time_step)
                    else:
                        log_stream.warning(' ===> Define time reference for section "' +
                                           file_key + '" is not possible. All fields are undefined.')
                if file_time_list:
                    file_time_idx = pd.DatetimeIndex(file_time_list)
                    file_time_reference = [file_time_idx.max()]
                else:
                    file_time_reference = None
                    log_stream.warning(' ===> Time list object is not defined, All datasets are undefined.')
        else:
            log_stream.error(' ===> Define time reference is not possible; the info object format is not supported')
            raise NotImplemented('Case not implemented yet')
    else:
        file_time_reference = None

    return file_time_reference
# -------------------------------------------------------------------------------------
