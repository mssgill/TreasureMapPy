# A tool to extract information from DES Follow-ups to
# be uploaded to Treasure Map

## USAGE:
# S190814bv: python treasue_map_query.py --outfile S190814bv_TM_pointings.csv --start 20190813 --end 20190905 --propid 2019B-0372

import glob
from optparse import OptionParser
import sys

import pandas as pd
import psycopg2

# Handle command-line arguments
parser = OptionParser(__doc__)
parser.add_option('--outfile', default=None, help="Name of file to write pointing info")
parser.add_option('--start', default=None, help="YYYYMMDD lower time bound of observations")
parser.add_option('--end', default=None, help="YYYYMMDD upper time bound of observations")
parser.add_option('--propid', default=None, help="PROPID of observations")
options, args = parser.parse_args(sys.argv[1:])

if not options.outfile:
    print("Use '--outfile' to specify where you want the pointing info written.")
    sys.exit()
if not options.start:
    print("Use '--start' to specify the date to begin the query (fmt YYYYMMDD)")
    sys.exit()
if not options.end:
    print("Use '--end' to specify the date to end the query (fmt YYYYMMDD)")
    sys.exit()
if not options.propid:
    print("Use '--propid' to specify the PROPID of the observations")
    sys.exit()

# Write query
query = """
select filter,
       night,
       ra, 
       dec,
       time,
       sum(exptime) as sumexptime, 
       to_char(case when filter='g' then 23.4 
                    when filter='r' then 23.1 
                    when filter='i' then 22.5 
                    when filter='z' then 21.8 
                    when filter='Y' then 20.3 
                    end + 1.25*log(sum(qc_teff*exptime)/90.), '99.99') as depth,
       hex 
from (select id as expnum,
             exptime, 
             filter,
             to_char(date::timestamp - interval '1 DAY' ,'YYYYMMDD') as night, 
             to_char(date::timestamp,'HH24:MI:SS') as time,
             qc_teff,
             to_char(ra,'09.999999') as ra, 
             to_char(declination,'99.99999') as dec,
             substring(object from 'x(.......)t') as hex 
      from exposure.exposure 
      where flavor = 'object' and 
            propid = '{propid}' and 
            qc_teff>0 
      order by id) as explist 
where cast(night as int) < {end} and 
      cast(night as int) > {start} 
group by night, 
         filter, 
         hex, 
         ra, 
         dec, 
         time
order by night; 
""".format(propid=options.propid, start=options.start, end=options.end)

# Get DECam database password
password = glob.glob(".*.password")[0].split('.')[1]

# Execute query
conn =  psycopg2.connect(database='decam_prd',
                           user='decam_reader',
                           host='des61.fnal.gov',
                           password=password,
                           port=5443) 
df = pd.read_sql(query, conn)
conn.close()

# Format output DataFrame
df['instrumentid'] = 38 # DECam
df['date'] = pd.to_datetime(df['night'].values, format='%Y%m%d')
df['time'] = pd.to_datetime(df['time'].values, format='%H:%M:%S')
df['time'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d')) + 'T' + df['time'].apply(lambda x: x.strftime('%H:%M:%S') + '.0')
df['band'] = df['filter'].values
df['status'] = 'completed'
df['depth_unit'] = 'ab_mag'

# Select columns for printing
cols = ['ra', 'dec', 'time', 'band', 'status', 'instrumentid', 'depth', 'depth_unit']

# Save to an outfile or print
df[cols].to_csv(options.outfile, index=False)
