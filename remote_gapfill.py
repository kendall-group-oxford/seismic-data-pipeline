# Author: J Asplet, U of Oxford, 20/11/2023

## Python script to remotely query data from NYMAR array stations
## This script is desgined to target explict (small) data gaps i.e, 1 or 2 channels in 1 day
## Each set of channel, station, date must be given explicitly.
# If download faitl for entire day, split into hour chunks and attempt to recombine at the end.

from pathlib import Path
from obspy import UTCDateTime
import obspy
import timeit
import datetime
import requests
import logging

def hour_by_hour_query(request, query_date):

    hour_shift = datetime.timedelta(hours=1)
    end = query_date + datetime.timedelta(days=1)
    chunk_start = query_date + hour_shift
    chunk_end = query_date
    while chunk_start < end:
        query_start = chunk_start - 150
        query_end = chunk_end + 150
        startUNIX = query_start.timestamp
        endUNIX = query_end.timestamp
        year = chunk_start.year
        month = chunk_start.month
        day = chunk_start.day
        hour = chunk_start.hour

        ddir = Path(f'{path_cwd}/{year}/{month:02d}/{day:02d}')
        outfile = Path(ddir, f"{request}.{year}{month:02d}{day:02d}T{hour:02d}0000_tmp.mseed")
        if outfile.is_file():
            log.info(f'Data chunk {outfile} exists')
        else:
            try:
                timer_start = timeit.default_timer()
                #time.sleep(5) # for testing directory creation
            
                r = requests.get(f"http://{station_ip}:8080/data?channel={request}&from={startUNIX}&to={endUNIX}", f"{outfile}")
                with open(outfile, "wb") as f:
                    f.write(r.content)
            
                timer_end = timeit.default_timer()
                runtime = timer_end - timer_start
                log.info(f'Request took {runtime:4.2f} seconds')
            except:
                log.error(f'Unable to request hour {hour}')

        chunk_start += day_shift
        # Iterate otherwise we will have an infinite loop!
    
    #collect into day file
    data = obspy.read(f'{ddir}/{request}.{year}{month:02d}{day:02d}T*tmp.mseed')
    data.merge(fill_value=0)
    data.write(f'{ddir}/{request}.{query_date.year}{query_date.month:02d}{query_date.day:02d}T000000.mseed')
    
    return

log = logging.getLogger(__name__)

script_start = timeit.default_timer()
logging.basicConfig(filename='/home/joseph/logs/nymar_gapfill.log', level=logging.INFO)
log.info(f'Starting download. Time is {datetime.datetime.now()}')

nym_zt_ips = {'NYM1':'172.24.59.19', 'NYM2':'172.24.239.162',
              'NYM3':'172.24.40.146', 'NYM4':'172.24.77.181',
              'NYM5':'172.24.43.200', 'NYM6':'172.24.150.216',
              'NYM7':'172.24.194.185', 'NYM8':'172.24.3.251' }

######### Start of variable to set #############

network = "OX"
station_list = ['NYM8']
channel_list = ["HHZ"] 
#SET TO CORRECT CODE. should be '00' for veloctity data
# will be somehing different for voltage, check status page (https://{your-ip-here})
location = "00" 
# try to get previous 2 days of data (current day will not be available)
day_list = [UTCDateTime(2024, 4, 1, 0, 0, 0)]

if len(station_list) == len(channel_list) == len(day_list):

    for i in range(0, len(station_list)):
        log.info(f'Gap fill for: {station_list[i]}, {channel_list[i]}, {day_list[i]}.')
        station = station_list[i] 
        channel = channel_list[i]
        query_date = day_list[i]
        day_shift = datetime.timedelta(days=1)
        station_ip = nym_zt_ips[station]
        # path_cwd = Path('/Volumes/NYMAR_DATA/NYMAR/data_dump') / station
        path_cwd = Path('/home/joseph/data')

        # add a 2.5 minute buffer either side of date query to reduce gap risk
        query_start = query_date - 150
        query_end = query_date + day_shift + 150
        startUNIX = query_start.timestamp
        endUNIX = query_end.timestamp
        year = query_date.year
        month = query_date.month
        day = query_date.day
        hour = query_date.hour
        ddir = Path(f'{path_cwd}/{year}/{month:02d}/{day:02d}')
        ddir.mkdir(exist_ok=True, parents=True)

        request = f"{network}.{station}.{location}.{channel}"
        # Make filename to wirte out to
        outfile = Path(ddir, f"{request}.{year}{month:02d}{day:02d}T{hour:02d}0000.mseed")
        #Test if we have already downloaded this chunk
        if outfile.is_file():
            log.info(f'Data chunk {outfile} exists')
        else:
            timer_start = timeit.default_timer()
            #time.sleep(5) # for testing directory creation
            try:
                r = requests.get(f"http://{station_ip}:8080/data?channel={request}&from={startUNIX}&to={endUNIX}", f"{outfile}")
                with open(outfile, "wb") as f:
                    f.write(r.content)
                timer_end = timeit.default_timer()
                runtime = timer_end - timer_start
                log.info(f'Request took {runtime:4.2f} seconds')
            except:
                try:
                    hour_by_hour_query(request, query_date)
                except:
                    log.error('Unable to download data even doing hourly')
                    continue
# Get dataless (not really neccesary but its nice)

script_end = timeit.default_timer()
runtime = script_end - script_start

log.info(f'Runtime is {runtime:4.2f} seconds, or {runtime/60:4.2f} minutes, or {runtime/3600:4.2f} hours')