import datetime
import urllib.parse
import pandas as pd
import time
import requests


class AMTD(object):
    """Class for hitting TD Ameritrade API and getting data."""
    def __init__(self, apikey):
        self._api_key = apikey
        self._access_tkn = None
        self.price_hist_url = "https://api.tdameritrade.com/v1/marketdata/{}/pricehistory"
        self.quote_url = "https://api.tdameritrade.com/v1/marketdata/quotes"
        self.instr_url = "https://api.tdameritrade.com/v1/instruments"
        self.auth_url = "https://api.tdameritrade.com/v1/oauth2/token"
        self.initial_balances = None
        self.projected_balances = None
        self.current_balances = None
        self.current_positions = None
        self.risk_free = None
        self._raw_rates = None

    def generate_access_token(self, refresh_tkn):
        """Need to do this to pull data from API as well as log in to see account info"""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = "grant_type=refresh_token&refresh_token="+urllib.parse.quote_plus(refresh_tkn)+"&access_type=&code=&client_id="+str(self._api_key)+"&redirect_uri="
        response = requests.post(self.auth_url, headers=headers, data=data)
        r = response.json()
        df = pd.DataFrame.from_dict(r, orient='index')
        tkn = df.T.access_token
        self._access_tkn = tkn.item()

    def get_fundamentals(self, symbol: str):
        """Input ticker string and returns a dataframe of fundamental ratios """
        raw = self._get_fundamentals_raw(symbol)
        fundamentals = self._transform_fundamentals(raw, symbol)
        return fundamentals

    def get_daily_price_hist(self, symbol, freq_type, freq, prd_type, prd, reindex = True):
        """Gets price data from the API. Example: One year price history - get_price_hist('AAPL', 'daily', 1, 'year', 1)"""
        raw = self._get_price_hist_raw(symbol, freq_type, freq, prd_type, prd)
        prices = self._transform_prices(raw, symbol)
        if reindex:
            prices['datetime'] = prices['datetime'].astype('datetime64[D]')
            prices = prices.set_index(['datetime'], drop=True)
            prices = prices.pivot(columns='symbol')
        return prices

    def get_daily_price_timeframe(self, symbol, start, end, reindex = True):
        """Gets dataframe of daily prices for a single symbol given a start and end date.
         Example: get_price_daily_timeframe('AAPL', '2019-01-01', '2019-05-01')"""
        raw = self._get_price_daily_timeframe_raw(symbol, start, end)
        prices = self._transform_prices(raw, symbol)
        if reindex:
            prices['datetime'] = prices['datetime'].astype('datetime64[D]')
            prices = prices.set_index(['datetime'], drop=True)
            prices = prices.pivot(columns='symbol')
        return prices


    def get_30min_price_timeframe(self, symbol, start, end):
        """Returns 30 minute price tick data from start to end date in a dataframe"""
        raw = self._get_price_30minute_timeframe_raw(symbol, start, end)
        prices = self._transform_prices(raw, symbol)
        return prices

    def get_quotes(self, symbol_list: list):
        """Inputs a list of ticker strings and returns a dataframe of quotes"""
        raw = self._get_quotes_raw(symbol_list)
        quotes = self._transform_quotes(raw)
        return quotes

    def get_account_info(self, account, initial_bal=True, projected_bal=True, current_bal=True, current_pos=True):
        """Input a retail account number and returns balances and positions"""
        raw = self._get_account_info_raw(account)
        self._transform_account_inf(raw, initial_bal, projected_bal, current_bal, current_pos)
        data = self._return_desired_account_data(initial_bal, projected_bal, current_bal, current_pos)
        return data

    def _get_fundamentals_raw(self, symbol):
        """Gets raw data in dictionary from the API"""
        payload = {'apikey': self._api_key,
                   'symbol': symbol,
                   'projection': 'fundamental'}
        content = requests.get(self.instr_url, params=payload)
        data = content.json()
        return data

    def _transform_fundamentals(self, data, symbol):
        """Transforms the dictionary of fundamental values into a consumable dataframe"""
        df = pd.DataFrame.from_dict(data)
        dft = df.T
        base_df = dft.drop('fundamental', axis = 1)
        fund_dict = dft.fundamental.to_dict()
        funds = pd.DataFrame.from_dict(fund_dict)
        funds['update_ts'] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        for i in base_df.columns:
            funds[i] = base_df[i].item()
        funds = funds.reset_index().rename(columns={'index': 'fundamental', str(symbol): 'value'})
        funds = funds[~funds.fundamental.str.contains("Date")]      ##.reset_index(drop=True)
        funds = funds[funds.fundamental != 'symbol'].reset_index(drop=True)
        funds = funds.astype({'value': 'float', 'update_ts': 'datetime64'})
        funds = funds.drop(columns=['description','exchange'])
        return funds

    def _get_price_hist_raw(self, symbol, freq_type, freq, prd_type, prd):
        """Gets raw dictionary of price history from the API"""
        url = self.price_hist_url.format(str(symbol))
        payload = {'apikey' : self._api_key,
                   'frequencyType' : freq_type,
                   'frequency' : freq,
                   'periodType': prd_type,
                   'period' : prd}
        content = requests.get(url, params=payload)
        data = content.json()
        return data

    def _transform_prices(self, data, symbol):
        """Transforms raw price data to consumable dataframe"""
        df = pd.DataFrame.from_dict(data['candles'])
        df['symbol'] = str(symbol)
        df['datetime'] = df['datetime'].astype(float)
        df['datetime'] = pd.to_datetime(df['datetime'],unit='ms')
        return df

    def _get_price_daily_timeframe_raw(self, symbol, start, end): #end is not inclusive
        """Calls the API and returns dictionary of raw daily time frame data from start to end dates"""
        url = self.price_hist_url.format(str(symbol))
        startint = (int(pd.to_datetime(start).timestamp()) + 18000)*1000
        endint = (int(pd.to_datetime(end).timestamp()) + 18000)*1000
        payload = {'apikey' : self._api_key,
                   'frequencyType' : 'daily',
                   'frequency' : "1",
                   'periodType': 'year',
                   #'period' : "1",
                   'startDate' : str(startint),
                   'endDate' : str(endint)}
        content = requests.get(url, params=payload)
        data = content.json()
        return data


    def _get_price_30minute_timeframe_raw(self, symbol, start, end):
        """Gets 30 minute tick data from API in dictionary form"""
        url = self.price_hist_url.format(str(symbol))
        #startint = (int(pd.to_datetime(start).timestamp()) + 18000)*1000
        #endint = (int(pd.to_datetime(end).timestamp()) + 18000)*1000
        startint = int(pd.to_datetime(start).timestamp())*1000
        endint = int(pd.to_datetime(end).timestamp())*1000
        payload = {'apikey': self._api_key,
               'frequencyType': 'minute',
               'frequency': "30",
               'periodType': 'day',
               #'period' : "1",
               'startDate': str(startint),
               'endDate': str(endint)}
        content = requests.get(url, params=payload)
        data = content.json()
        return data

    def _get_quotes_raw(self, symbol_list: list):
        """Gets raw quote data from API in form of a dictionary"""
        url = self.quote_url
        symbs = ','.join(str(e) for e in symbol_list)
        payload = {'apikey': self._api_key,
                   'symbol' : symbs}
        content = requests.get(url, params=payload)
        data = content.json()
        return data

    def _transform_quotes(self, data):
        """Transforms quote dictionary to dataframe with a timestamp"""
        df = pd.DataFrame.from_dict(data)
        dft = df.T
        dft['update_ts'] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        return dft

    def _get_account_info_raw(self, account):
        url = "https://api.tdameritrade.com/v1/accounts/{}?fields=positions".format(account)
        headers = {'Authorization': "Bearer " + str(self._access_tkn)}
        content = requests.get(url, headers=headers)
        data = content.json()
        return data

    def _transform_account_inf(self, data, initial_bal, projected_bal, current_bal, current_pos):
        df = pd.DataFrame(list(data['securitiesAccount'].items()))
        df.columns = ['title', 'data']
        d = {}
        for i in df['title'].values:
            d[i] = df['data'][df['title'] == i].apply(pd.Series).T
        if initial_bal:
            self.initial_balances = pd.DataFrame(d['initialBalances'])
        if projected_bal:
            self.projected_balances = pd.DataFrame(d['projectedBalances'])
        if current_bal:
            self.current_balances = pd.DataFrame(d['currentBalances'])
        if current_pos:
            positions = pd.DataFrame(df['data'][df['title'] == 'positions'].item())  # this is touchy
            instruments = positions.instrument.apply(pd.Series)[['symbol', 'cusip', 'assetType']]
            self.current_positions = pd.concat([instruments, positions.drop(columns='instrument')], axis=1)

    def _return_desired_account_data(self, initial_bal, projected_bal, current_bal, current_pos):
        data = []
        if initial_bal:
            data.append(self.initial_balances)
        if projected_bal:
            data.append(self.projected_balances)
        if current_bal:
            data.append(self.current_balances)
        if current_pos:
            data.append(self.current_positions)
        return data

    #This needs review
    def generate_new_refresh_token(self, refresh_tkn):
        return NotImplementedError



    def get_ohlcv_array(self, start, end, list_of_tickers, filter = 0):
        prices = {}
        first = list_of_tickers[0]
        prices[first] = self.get_daily_price_timeframe(first, start, end)
        p_array = prices[first]
        for i in list_of_tickers[1:]:
            time.sleep(1)
            prices[i] = self.get_daily_price_timeframe(i, start, end)
            p_array = pd.concat([p_array,prices[i]], axis = 1)
        if bool(filter):
            p_array = p_array.filter(like=filter)
        return p_array

    def get_risk_free_rate(self, time_prd = "1 yr"):
        url = "https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/textview.aspx?data=yield"
        r_data = pd.read_html(url)
        rfr = r_data[1]
        rfr.columns = list(rfr[:1].values)
        rdf = rfr[1:]
        self._raw_rates = rdf[::-1].reset_index(drop=True)
        risk_free = self._raw_rates.iloc[0,:]
        if bool(time_prd) == True:
            self.risk_free = float(risk_free[str(time_prd)].values)/100
            return self.risk_free
        else:
            return self._raw_rates