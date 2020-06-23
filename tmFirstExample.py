# from treasuremap.treasuremap import Pointings

import treasuremap

import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
import json

import datetime as dt



# Set up instrument parameters
graceid = "TEST_EVENT"
instrumentid = 65
band = 'i'
depth_unit = 'flux_jy'

# Set up pointing parameters
S200224_coord = SkyCoord(165.112931, -0.03382 , frame="icrs",  unit="deg")


obs_start = [
    "2020-02-24T14:10:27",
    "2020-02-24T08:10:27"]


obs_length = [
    "10:39:25",
    "10:38:42"]

# Set up depth
rms_vals = np.asarray([35, 39]) * u.uJy


ra = S200224_coord.ra.deg
dec = S200224_coord.dec.deg

# Initialise Pointings class
S200224 = treasuremap.Pointings("planned", graceid, instrumentid, band)

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

# Cancel the first pointing
#cancel_id = request["pointing_ids"][0]
#S200224.cancel([cancel_id])

# Cancel all pointings
#S200224.cancel_all()
