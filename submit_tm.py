# A script to submit DECam pointings to Treasure Map

import datetime
import getpass
import glob
import json
import logging
from optparse import OptionParser
import sys
sys.path.append('treasuremap')

from astropy.coordinates import SkyCoord
import pandas as pd
from treasuremap import Pointings

# Get username of user
USERNAME = getpass.getuser()

# Set up logging
logging.basicConfig(filename="submit_tm.log",
                    filemode="a+",
                    format="|%(levelname)s\t| %(asctime)s -- %(message)s",
                    datefmt="20%y-%m-%d %I:%M:%S %p",
                    level=logging.DEBUG)
logging.info("[" + USERNAME + "] " + "submit_tm.py started")
logging.debug("[" + USERNAME + "] " + "program command: " + ' '.join(sys.argv))

# Handle command line arguments
parser = OptionParser(__doc__)
parser.add_option('--infile', default=None, help="Name of file with pointing info")
parser.add_option('--preview', action='store_true', help="Prompt before submitting")
parser.add_option('--test', action='store_true', help="Run without submitting")
parser.add_option('--graceid', default=None, help="Name of the GraceDB event")
options, args = parser.parse_args(sys.argv[1:])

if not options.infile:
    print("Use '--infile' to specify the file with pointing info")
    logging.critical("[" + USERNAME + "] " + "Missing --infile argument")
    logging.info("[" + USERNAME + "] " + "Program terminating")
    logging.shutdown()
    sys.exit()

if not options.graceid:
    print("Use '--graceid' to specify the GraceDB event name")
    logging.critical("[" + USERNAME + "] " + "Missing --graceid argument")
    logging.info("[" + USERNAME + "] " + "Program terminating")
    logging.shutdown()
    sys.exit()

logging.debug("[" + USERNAME + "] " + "--infile set to {}".format(options.infile))
logging.debug("[" + USERNAME + "] " + "--graceid set to {}".format(options.graceid))
logging.debug("[" + USERNAME + "] " + "--preview set to {}".format(options.preview))
logging.debug("[" + USERNAME + "] " + "--test set to {}".format(options.test))
if options.test:
    options.preview = True
    logging.info("[" + USERNAME + "] " + "Setting --preview to True for testing")

# API token - Get your own by making a TreasureMap account
try:
    API_TOKEN = glob.glob('api_tokens/{}/*.api_token'.format(USERNAME))[0].split('/')[-1].split('.')[0]
    logging.debug("[" + USERNAME + "] " + "API_TOKEN set to {}".format(API_TOKEN))
except IndexError:
    logging.error("[" + USERNAME + "] " + "Unable to find user-specific API_TOKEN")
    logging.info("[" + USERNAME + "] " + "M. Gill's token will be used as a default")
    try:
        API_TOKEN = glob.glob('api_tokens/mssgill/*.api_token')[0].split('/')[-1].split('.')[0]
        logging.debug("[" + USERNAME + "] " + "API_TOKEN set to {}".format(API_TOKEN))
    except IndexError:
        logging.error("[" + USERNAME + "] " + "Unable to find M. Gill's default API_TOKEN")
        logging.critical("[" + USERNAME + "] " + "Program needs a valid API_token and will terminate")
        logging.shutdown()
        sys.exit()

# Read the pointing information into a Pandas DataFrame
try:
    pointings_df = pd.read_csv(options.infile)
    logging.info("[" + USERNAME + "] " + "Successfully read {}".format(options.infile))
except FileNotFoundError:
    logging.error("[" + USERNAME + "] " + "Unable to find specified infile")
    logging.critical("[" + USERNAME + "] " + "Progams needs a valid pointing file")
    logging.info("[" + USERNAME + "] " + "Program terminating")
    logging.shutdown()
    sys.exit()

# Instantiate the treasuremap.Pointing class
#  -- looks like treasuremap requires a different object per band
pointings = {}
logging.info("[" + USERNAME + "] " + "Initializing treasuremap.Pointings")
for flt in set(pointings_df['band'].values):
    pointings[flt] = Pointings(status="completed",
                               graceid=options.graceid,
                               instrumentid=38, # 38 == DECam
                               band=flt,
                               api_token=API_TOKEN)
logging.debug("[" + USERNAME + "] " + "Made pointings for " + ','.join(list(pointings.keys())) + " bands")

logging.info("[" + USERNAME + "] " + "Starting processing of DECam pointings")
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
    logging.debug("[" + USERNAME + "] " + "Added pointing for index {}".format(index))
logging.info("[" + USERNAME + "] " + "Finished making pointings")


# Build all jsons
logging.info("[" + USERNAME + "] " + "Starting generation of json data")
for pointing in pointings.values():
    pointing.build_json()
logging.info("[" + USERNAME + "] " + "Finished building json data")

# If the preview argument was used, wait for approval before submitting
if options.preview:
    logging.info("[" + USERNAME + "] " + "Preview argument passed, requesting user approval")
    for flt in pointings.keys():
        logging.debug("[" + USERNAME + "] " + "Showing user {} band pointings".format(flt))
        # Display pointings
        print('\n\n\n\tShowing {}-band pointings\n\n\n'.format(flt))
        print(json.dumps(pointings[flt].json_data, indent=4))

        # Ask if the pointings look okay
        user_input = input("Does the JSON data look okay? (y/n) ").strip().lower()
        while user_input not in ['y', 'n']:
            print("Please enter 'y' or 'n'")
            user_input = input("Does the JSON data look okay? (y/n) ").strip().lower()
        logging.debug("[" + USERNAME + "] " + "user_input set to {}".format(user_input))

        if user_input == 'n':
            print("Please make your corrections and restart")
            logging.info("[" + USERNAME + "] " + "User has identified error in pointings")
            logging.info("[" + USERNAME + "] " + "Program will terminate to allow for correction")
            logging.shutdown()
            sys.exit()

if not options.test:
    # Submit jsons
    logging.info("[" + USERNAME + "] " + "Beginning submission process")
    requests = {}
    for flt in pointings.keys():
        try:
            request = pointings[flt].submit()
            logging.info("[" + USERNAME + "] " + "Submitted {} band pointing".format(flt))
            requests[flt] = request
        except Exception:
            logging.info("[" + USERNAME + "] " + "There was a prolem with the submisison.")
            logging.exception("[" + USERNAME + "] " + "The traceback for the submission is below")
            logging.warning("[" + USERNAME + "] " + "The {} band pointings may not have submitted properly".format(flt))
    logging.info("[" + USERNAME + "] " + "Finished submisison")

    # Save pointings
    time = datetime.datetime.now()
    logging.info("[" + USERNAME + "] " + "Saving submission pointings")
    pointing_filename = "pointings_{}.json".format(time.strftime("%y%m%d_%H%M%S")) 
    pointing_file = open(pointing_filename, 'w+')
    logging.debug("[" + USERNAME + "] " + "pointing file set to {}".format(pointing_filename))

    for flt in pointings.keys():
        pointing_file.write(json.dumps(pointings[flt], indent=4))
        pointing_file.write('\n\n')

        logging.info("[" + USERNAME + "] " + "Wrote pointings for {} band".format(flt))

    # Save requests
    logging.info("[" + USERNAME + "] " + "Saving submission requests")
    request_filename = 'requests_{}.json'.format(time.strftime("%y%m%d_%H%M%S"))
    request_file = open(request_filename, 'w+')
    logging.debug("[" + USERNAME + "] " + "request file set to {}".format(request_filename))
    
    for flt in requests.keys():
        request_file.write(json.dumps(requests[flt], indent=4))
        request_file.write('\n\n')
        
        logging.info("[" + USERNAME + "] " + "Wrote requests for {} band".format(flt))

    # Close open file streams
    request_file.close()
    pointing_file.close()

else:
    logging.info("[" + USERNAME + "] " + "Skipping submission process due to --test argument")

# Conclude the program
logging.info("[" + USERNAME + "] " + "Progam finished")
logging.shutdown()
