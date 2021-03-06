# -*- coding: utf-8 -*-
"""
Read_edf
========

Reading data from Elmiko DigiTrack. Integrating time info from XML (.EVX file from digitrack) about time of first EEG sample
with sampling rate info (from .1 file from digitrack) to make timestamps for EEG signal. EEG signal needs to be exported to .edf 
from digitrack, then it can be parsed here.

Use timestamps from experiment log file to cut slices from EEG around events. EEG and events need to be saved with respect to the same 
clock, so best do experiment and recording on the same machine.
"""
from io import open

import pandas as pd
import xml.etree.ElementTree as etree

import pyedflib 
import numpy as np
from datetime import datetime
import random
import struct
import pyseries.Preprocessing.ArtifactRemoval as ar




#TODO Make an organized/relative paths way of maintaining database
#path = '/Users/user/Desktop/Nagrania/rest/Rysiek_03_06/'
def Combine_EDF_XML(path,freq_min = 0, freq_max = 70):
    """Creates a dictionary with eeg signals, timestamps and events. 
       Reads edf file with eeg signal. Uses xml file to add timestamps to eeg. Reads unity_log with experiment events times. 
         
       Parameters
       ----------
       path:str
           directory containing .edf, .xml, and .csv files.
       freq_min, freq_max : int, int, optional
            Deafault to 0, 70
            bandpass filter parameters in Hz.

         Returns
         -------
         signal_dict (dict of Objects): dict
             stores eeg channels, ttimestamps and events.
             Keys:
             "EEG <channel name>" : eeg signal
             "timestamp" : timestamps for eeg
             "events" : names and timestamps of events
    
    """
    signal_dict = Read_EDF(path + "sygnal.edf")

    for chan_name, sig in signal_dict.items():
        signal_dict[chan_name] = ar.band_pass(sig, freq_min,freq_max)
        #signal_dict[chan_name] = sig
    
    log = pd.read_csv(path + 'unity_log.csv',parse_dates = True, index_col = 0, skiprows = 1, skipfooter = 1, engine='python')
    
    signal_dict['events'] = log
#Get the timestamp based on the info from the exact_timestamp field in the .1 file
    e_ts = exact_timestamp(path, GetMaxLength(signal_dict))
#TODO decide which timestamp is correct
    signal_dict['timestamp'] = e_ts

    
    return signal_dict
    
def GetMaxLength(_dict):        
    maks=max(_dict, key=lambda k: len(_dict[k]))
    return len(_dict[maks])



#path = '/Users/user/Desktop/Resty/Ewa_resting_state.edf'

def Read_EDF(path):

#  """Read .edf exported from digitrack and converts them to a dictionary.
#      
#      Parameters
#      ----------
#      path:str
#          directory of .edf
#  
#      Returns
#      -------
#      signal_dict: dict(np.array)
#          Keys are channel names
#  """
    
    
    f = pyedflib.EdfReader(path)
    #n = f.signals_in_file
    signal_labels = f.getSignalLabels()
    
    
    signal_dict = {}
    #print('Channels:')
    for idx, name in enumerate(signal_labels):
        #print(name.decode("utf-8"))
        signal_dict[name.decode("utf-8")] = f.readSignal(idx)
        
    f._close()

    return signal_dict


        

    

    

def Read_XML(path):
#    import xml.etree.cElementTree as ET
#   """Read the header for the signal from .EVX.

#      Returns
#      -------
#      df: DataFrame
#          Contains timestamp marking first EEG sample
#   """
#   
    
    with open(path, mode='r',encoding='utf-8') as xml_file:
        xml_tree = etree.parse(xml_file)        
        root = xml_tree.getroot()
#Get only the relevant fields  
    for child_of_root in root:
        if(child_of_root.attrib['strId'] == 'Technical_ExamStart'):
            time_event = child_of_root.find('event')
            #Timestamp in unix time
            u_time = time_event.attrib['time']
            #Timestamp in DateTime
            dt_time = time_event.find('info').attrib['time']
#store this information in a dataframe in a datetime/timestamp format
            df = pd.DataFrame()            
#HACK changing timezone by manually adding two hours
#TODO make sure the timestamps will be possible to comapre between tz (utc) naive and tz aware formats
            df['UNIXTIME'] = pd.to_datetime([u_time], unit='us') + pd.Timedelta(hours =1)
            df['DateTime'] = pd.to_datetime([dt_time],infer_datetime_format =True) + pd.Timedelta(hours =1)
    return df

    

def exact_timestamp(path, n_samples):
    #Convert to nanoseconds by multiplying to desired resolution and cutting the reminding decimal places using int(). *time units change by order of 10^3
    eaxct_sr_ns = int(1000.0/Get_Exact_Sampling_rate(path)*10**3 *10**3)
   # freq = '2008147ns'
    timestamp = np.empty(n_samples, dtype='datetime64[ns]')
    timestamp[0] =Read_XML(path + 'digi_log.xml')['DateTime'].iloc[0]
    for i in range(n_samples - 1):
        timestamp[i+1] = timestamp[i] + np.timedelta64(eaxct_sr_ns, 'ns')

    return timestamp
    

def Get_Exact_Sampling_rate(path):
    #Read the bytes from .1 file
    with open(path + 'digi_binary.1', "rb") as binary_file:
         #Seek position and read N bytes
        binary_file.seek((490+(89*32)))  # Go to bite nr
        couple_bytes = binary_file.read(8)
        sr = struct.unpack("d", couple_bytes)
        print(sr)
        
    return sr[0]
    #return 497.971446705165
    
