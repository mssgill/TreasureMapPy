# MSSG, 6-22-2020 -- based on code in the orig TreasureMap bin dir from @ddobie
# This is an example taking one of our desgw pointing files from the 2-24-2020 event, and just 
# inserting 2 of the actual pointings into the file below, using actual coords for the first pointing
# I changed below: band and the coords for the pointing from HA and dec to RA and dec (looking up 
# the astropy documentation for SkyCoord)
# At the end it properly seems to print all the contents of 'request'
# Note it doesn't actually submit/upload anything to the real TreasureMap DB because i don't specify any URLs here
# Those are needed inside the treasuremap module to do real uploads

import treasuremap

import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
import json

import datetime as dt

import requests
 

# Set up instrument parameters
graceid = "TEST_EVENT"
instrumentid = 38
band = 'i'
depth_unit = 'flux_jy'

# Set up pointing parameters
S200224_coord = SkyCoord(153.112931, -0.03382 , frame="icrs",  unit="deg")


obs_start = [
    "2020-06-24T14:10:27",
    "2020-06-24T08:10:27"]


obs_length = [
    "10:39:25",
    "10:38:42"]

# Set up depth
rms_vals = np.asarray([35, 39]) * u.uJy


ra = S200224_coord.ra.deg
dec = S200224_coord.dec.deg

# Initialise Pointings class
S200224 = treasuremap.Pointings("completed", graceid, instrumentid, band)

# Loop over each observation and add to Pointings
for start, dur, rms in zip(obs_start, obs_length, rms_vals):
    start_dt = dt.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
    dodgy_delta = dt.datetime.strptime(
        dur, "%H:%M:%S") - dt.datetime.strptime("00:00:00", "%H:%M:%S")

    time = start_dt + dodgy_delta / 2
    time_str = dt.datetime.strftime(time, "%Y-%m-%dT%H:%M:%S.%f")[:-4]

    S200224.add_pointing(
        ra, dec, time_str, rms.to(
            u.Jy).value * 5, depth_unit)

# Build the JSON and submit
S200224.build_json()
request = S200224.submit()
print(request["pointing_ids"])

print(request)


########## doi

BASE = 'http://treasuremap.space/api/v0/'
TARGET = 'request_doi'

json_data = {
    "api_token":'k1M5prGNpnN00RGBHM-Q7LKikAu3RtLTnUjRBQ',
    "graceid":"TEST_EVENT",
    "doi_group_id":6
    
}


'''
"creators":[
        {"name":"MG", "affiliation":"Kipac"},
        {"name":"RM", "affiliation":"UW Madison"}
    ]
'''

r = requests.post(url = BASE+TARGET, json = json_data)

print(r.text)

# Cancel the first pointing
#cancel_id = request["pointing_ids"][0]
#S200224.cancel([cancel_id])

# Cancel all pointings
#S200224.cancel_all()
