# A script to submit DECam pointings to Treasure Map

import datetime
import getpass
import glob
import json
import logging
from optparse import OptionParser
import sys

from astropy.coordinates import SkyCoord
import pandas as pd
from treasuremap import Pointings

# Get username of user
USERNAME = getpass.getuser()

# Set up logging
logging.basicConfig(filename="submit_tm.log",
                    filemode="a+",
                    format="|%(levelname)s:%(USERNAME)s\t| %(asctime)s -- %(message)s",
                    datefmt="%y%m%d %I:%M:%S %p",
                    level=logging.DEBUG)
logging.info("submit_tm.py started")

# Handle command line arguments
parser = OptionParser(__doc__)
parser.add_option('--infile', default=None, help="Name of file with pointing info")
parser.add_option('--preview', action='store_true', help="Prompt before submitting")
parser.add_option('--graceid', default=None, help="Name of the GraceDB event")
options, args = parser.parse_args(sys.argv[1:])

if not options.infile:
    print("Use '--infile' to specify the file with pointing info")
    logging.critical("Missing --infile argument")
    logging.info("Program terminating")
    logging.shutdown()
    sys.exit()

if not options.graceid:
    print("Use '--graceid' to specify the GraceDB event name")
    logging.critical("Missing --graceid argument")
    logging.info("Program terminating")
    logging.shutdown()
    sys.exit()

logging.debug("--infile set to {}".format(options.infile))
logging.debug("--graceid set to {}".format(options.graceid))
logging.debug("--preview set to {}".format(options.preview))

# API token - Get you own by making a TreasureMap account
try:
    API_TOKEN = glob.glob('api_tokens/{}/*.api_token')[0].split('/')[-1].split('.')[0]
    logging.debug("API_TOKEN set to {}".format(API_TOKEN))
except IndexError:
    logging.error("Unable to find user-specific API_TOKEN")
    logging.info("M. Gill's token will be used as a default")
    try:
        API_TOKEN = glob.glob('api_tokens/mssgill/*.api_token')[0].split('/')[-1].split('.')[0]
        logging.debug("API_TOKEN set to {}".format(API_TOKEN))
    except IndexError:
        logging.error("Unable to find M. Gill's default API_TOKEN")
        logging.critical("Program needs a valid API_token and will terminate")
        logging.shutdown()
        sys.exit()

# Read the pointing information into a Pandas DataFrame
try:
    pointings_df = pd.read_csv(options.infile)
    logging.info("Successfully read {}".format(options.infile))

except FileNotFoundError:
    logging.error("Unable to find specified infile")
    logging.critical("Progams needs a valid pointing file")
    logging.info("Program terminating")
    logging.shutdown()
    sys.exit()

# Instantiate the treasuremap.Pointing class
#  -- looks like treasuremap requires a different object per band
pointings = {}
logging.info("Initializing treasuremap.Pointings")
for flt in set(pointings_df['band'].values):
    pointings[flt] = Pointings(status="completed",
                               graceid=options.graceid,
                               instrumentid=38, # 38 == DECam
                               band=flt,
                               api_token=API_TOKEN)
logging.debug("Made pointings for " + ','.join(list(pointings.keys())) + " bands")

logging.info("Starting processing of DECam pointings")
# Iterate through our pointings and add them
for index, row in pointings_df.iterrows():
    # Format RA and Dec as proper data type
    coord = SkyCoord(row['ra'], row['dec'], frame="icrs",  unit="deg")

    # Add the pointing based on the filter used
    pointings[row['band']].add_pointing(ra=coord.ra.deg, 
                                        dec=coord.dec.deg,
                                        time=row['time'],
                                        depth=row['depth'],
                                        depth_unit=row['depth_unit'])
    logging.debug("Added pointing for index {}".format(index))
logging.info("Finished making pointings")

logging.info("Starting generation of json data")
# Build all jsons
for pointing in pointings.values():
    pointing.build_json()
logging.info("Finished building json data")

# If the preview argument was used, wait for approval before submitting
if options.preview:
    logging.info("Preview argument passed, requesting user approval")
    for flt in pointings.keys():
        logging.debug("Showing user {} band pointings".format(flt))
        # Display pointings
        print('\n\n\n\tShowing {}-band pointings\n\n\n'.format(flt))
        print(pointings[flt].json_data)

        # Ask if the pointings look okay
        user_input = input("Does the JSON data look okay? (y/n)").strip().lower()
        while user_input not in ['y', 'n']:
            print("Please enter 'y' or 'n'")
            user_input = input("Does the JSON data look okay? (y/n)").strip().lower()
        logging.debug("user_input set to {}".format(user_input))

        if user_input == 'n':
            print("Please make your corrections and restart")
            logging.info("User has identified error in pointings")
            logging.info("Program will terminate to allow for correction")
            logging.shutdown()
            sys.exit()

logging.info("Beginning submission process")
# Submit jsons
requests = {}
for flt in pointings.keys():
    try:
        request = pointings[flt].submit()
        logging.info("Submitted {} band pointing".format(flt))
        requests[flt] = request
    except Exception:
        logging.info("There was a prolem with the submisison.")
        logging.exception("The traceback for the submission is below")
        logging.warning("The {} band pointings may not have submitted properly".format(flt))
logging.info("Finished submisison")

# Save requests
logging.info("Saving submission requests")
time = datatime.datetime.now()
request_filename = 'requests_{%y%m%d_%H%M%S}.json'.foramt(time)
request_file = open(request_filename, 'w+')
logging.debug("request file set to {}".format(request_filename))

for flt in requests.keys():
    request_file.write(json.dumps(requests[flt], indent=4))
    request_file.write('\n\n')
    
    logging.info("Wrote requests for {} band".format(flt))

# Conclude the program
logging.info("Progam finished")
logging.shutdown()
