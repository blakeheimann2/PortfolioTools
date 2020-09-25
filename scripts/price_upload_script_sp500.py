"""
Script for uploading SP500 Price Data to the Local DB.
"""

from library import DBA as db, broker as td
import pandas as pd
import datetime
import time
from datetime import timedelta
import logging

#add something to kill it if refresh token is expired

logger = logging.getLogger('pricing_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('C:/Users/bheim/PythonProjects/bat_files/logs/SP500_prices_{}.log'.format(time.strftime("%Y%m%d")))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.debug('Starting SP500 Pricing Program {}'.format(datetime.datetime.now()))


all_ticks = db.get_sp500()
all_ticks = all_ticks.rename(columns = {0:'symb'})
logger.debug('Successfully queried SP500 ticks {}'.format(datetime.datetime.now()))


#query last update and set start and end dates
q = "select max(datetime) from public.ohclv_daily_10_yr_hist"
last_dt = db.query_db(q)
logger.debug('Successfully queried old end as {}'.format(str(last_dt)))
dayaft = pd.to_datetime(last_dt.values.item()[:10]) + timedelta(days=1)
start = dayaft.strftime("%Y-%m-%d")
tmrw = datetime.datetime.today() + timedelta(days=1)
end = tmrw.strftime("%Y-%m-%d")
logger.debug('Successfully set start as {}'.format(str(start)))
logger.debug('Successfully set end as {}'.format(str(end)))
print("Last date in db, query start, query end:")
print((last_dt, start, end))


#create table -- do not upload data
#data = td.get_price_hist('AAPL', "daily", 1, "year", 10)
#db.create_postgres_table(data, "OHCLV_daily_10_yr_hist")

##start getting prices and upload to DB
success = []
fail = []
print('Beginning to Call TDA API')

A = pd.DataFrame()
for i in (all_ticks.symb):
    time.sleep(1)
    try:
        newdata =td.get_price_daily_timeframe(str(i), start, end)   #need to fix time issue for conversions look at pd.to_datetime(last_dt.values.item()).timestamp()
        A = pd.concat([A, newdata], axis = 0, sort =True)
        success.append(str(i))
    except:
        print(str(i)+" failed.")
        fail.append(str(i))
        logger.debug('{} failed.'.format(str(i)))
        pass
    if (len(success) + len(fail)) % 100 == 0:
        print((len(success) + len(fail)) / len(all_ticks.symb))
    else:
        continue

logger.debug('Finished creating dataframe of pricing data {}'.format(datetime.datetime.now()))
logger.debug('Failed Ticks: {}'.format(str(len(fail))))
logger.debug('Successful Ticks: {}'.format(str(len(success))))

print("Dataframe MIN and MAX dates:")
print((A.datetime.min(), A.datetime.max()))
print("Shape: {}".format(A.shape))
input("Press Enter to upload to the database..")
db.data_upload_pg(A, "OHCLV_daily_10_yr_hist")
logger.debug('Finished uploading data to table {}'.format(datetime.datetime.now()))

pd.Series(fail).to_csv('price_fail.csv')
pd.Series(success).to_csv('price_success.csv')


