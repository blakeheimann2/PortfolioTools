"""
Revised implementation of Portfolio Object for better interfacing with stress testing objects, API clients,  portfolio optimization tools
and other objects in an attempt to better separate functionality.
"""

from config import apikey
import pandas as pd
import numpy as np
from library.broker import AMTD
import collections
from scipy.stats import norm
import statsmodels.api as sm


class Portfolio(object):
    """Portfolio Object for calculating risk and return metrics, PnL, VAR, betas, etc."""
    def __init__(self, asset_dict = {}, asset_alloc = {}):
        self.source = None
        self.assets = collections.OrderedDict(asset_dict)
        self.asset_alloc = collections.OrderedDict(asset_alloc)
        self.asset_values = None
        self.asset_returns = pd.DataFrame()
        self.portfolio_ohlcv = pd.DataFrame()
        self.portfolio_returns = pd.DataFrame()
        self.historical_value = pd.DataFrame()
        self.asset_volatilty = pd.DataFrame()
        self.portfolio_volatilty = pd.DataFrame()
        self.benchmark = {}

    def set_source(self, api_key):
        self.source = AMTD(api_key)

    def _test_source(self):
        if self.source is None:
            raise AttributeError("Did not set a datasource. Use set_source method.")

    def calculate_alloc_from_shares(self):
        total_shares = sum(self.assets.values())
        self.asset_alloc = {}
        for key in self.assets.keys():
            self.asset_alloc[key] = self.assets[key] / total_shares

    def calculate_shares_from_alloc(self, total_money):
        self._test_source()
        share_prices = self.source.get_quotes(list(self.asset_alloc.keys()))[['closePrice', 'symbol']] ##COULD BE CLEANED UP
        self.assets = {}
        for key in self.asset_alloc.keys():
            self.assets[key] = self.asset_alloc[key] * total_money / share_prices['closePrice'][share_prices['symbol'] == key].values[0]

    def calculate_current_value(self):
        """Think about implementing to allow bid/ask/mid"""
        self._test_source()
        self.asset_values = {}
        for key in self.assets.keys():
            current_price = self.source.get_quotes([key])[['closePrice', 'symbol']]
            self.asset_values[key] = self.assets[key] * current_price['closePrice'][current_price['symbol'] == key].values[0]

    def _get_ohlcv_array(self, start_date, end_date):
        self._test_source()
        self.portfolio_ohlcv = self.source.get_ohlcv_array(start_date, end_date, list(self.assets.keys()))
        self.portfolio_ohlcv = self.portfolio_ohlcv[::-1]
        return self.portfolio_ohlcv

    def get_historical_asset_returns(self, start_date=None, end_date=None, log = True):
        self._test_source()
        self._recalc_ohlcv_new_dates_check(start_date, end_date)
        self.asset_returns = self.portfolio_ohlcv.filter(like ='close')
        if log:
            self.asset_returns = np.log(self.portfolio_ohlcv.close/ self.portfolio_ohlcv.close.shift(-1))
        else:
            self.asset_returns = self.portfolio_ohlcv.close.pct_chg()
        return self.asset_returns

    def get_historical_portfolio_returns(self, start_date=None, end_date=None):
        self._recalc_ohlcv_new_dates_check(start_date, end_date)
        self._recalc_asset_returns_check(start_date, end_date)
        self.portfolio_returns = self.asset_returns @ np.array(list(self.asset_alloc.values()))
        return self.portfolio_returns

    def get_historical_portfolio_value(self, start_date=None, end_date=None, aggregate = False):
        self._test_source()
        self._recalc_ohlcv_new_dates_check(start_date, end_date)
        self._recalc_asset_returns_check(start_date, end_date)
        self._recalc_portfolio_returns_check(start_date, end_date)
        if aggregate:
            self.historical_value = self.portfolio_ohlcv.filter(like='close') @ np.array(list(self.assets.values()))
        else:
            self.historical_value = self.portfolio_ohlcv.filter(like='close') * np.array(list(self.assets.values()))
        return self.historical_value

    def _recalc_ohlcv_new_dates_check(self, start_date, end_date):
        self._test_source()
        if self.portfolio_ohlcv.empty or (bool(start_date) and bool(end_date)):
            self._get_ohlcv_array(start_date, end_date)
            self.asset_returns = pd.DataFrame()
            self.portfolio_returns = pd.DataFrame()
            self.historical_value = pd.DataFrame()

    def _recalc_asset_returns_check(self, start_date, end_date):
        self._test_source()
        if self.asset_returns.empty:
            self.get_historical_asset_returns(start_date, end_date)

    def _recalc_portfolio_returns_check(self, start_date, end_date):
        self._test_source()
        if self.portfolio_returns.empty:
            self.get_historical_portfolio_returns(start_date, end_date)

    def get_asset_volatility(self, window = 20, annualized=True):
        self.asset_volatility = self.asset_returns[::-1].rolling(window).std()[::-1]
        if annualized:
            self.asset_volatility = self.asset_volatility * np.sqrt(252)
        return self.asset_volatility

    def get_portfolio_volatility(self, window = 20, annualized=True):
        self.portfolio_volatilty = self.portfolio_returns[::-1].rolling(window).std()[::-1]
        if annualized:
            self.portfolio_volatilty = self.portfolio_volatilty * np.sqrt(252)
        return self.portfolio_volatilty

    def asset_corr(self):
        return self.asset_returns.corr()

    def cumm_portfolio_returns(self):
        return self.portfolio_returns[::-1].cumsum()[::-1]

    def cumm_asset_returns(self):
        return self.asset_returns[::-1].cumsum()[::-1]

    def asset_kurtosis(self):
        return self.asset_returns.kurtosis()

    def asset_skew(self):
        return self.asset_returns.skew()

    def portfolio_kurtosis(self):
        return self.portfolio_returns.kurtosis()

    def portfolio_skew(self):
        return self.portfolio_returns.skew()

    def max_drawdown(self):
        portfolio_hist_value = self.historical_value.sum(axis=1)
        peak = portfolio_hist_value.max()
        trough = portfolio_hist_value.min()
        max_drawdown = (trough - peak)/ peak
        return (max_drawdown, portfolio_hist_value.idxmax(), portfolio_hist_value.idxmin())

    def sharpe_ratio(self, risk_free=False):
        if risk_free == False:
            risk_free = self.source.get_risk_free_rate("1 yr")
        sharpe_ratio = (self.portfolio_returns[::-1].sum()- risk_free) / (self.portfolio_returns[::-1].std() * np.sqrt(252))
        return sharpe_ratio

    def var_historic(self, level=5):
        """VAR Historic
        returns the value at risk for a certain alpha level 0-100 of the data"""
        if isinstance(self.portfolio_returns, pd.DataFrame):
            return self.portfolio_returns.dropna().aggregate(self.var_historic, level=level)
        elif isinstance(self.portfolio_returns, pd.Series):
            return -np.percentile(self.portfolio_returns.dropna(), level)
        else:
            raise TypeError("Expected Series or DataFrame")


    def parametric_var(self, level=5, modified=False):
        if isinstance(self.portfolio_returns, pd.DataFrame):
            return self.portfolio_returns.dropna().aggregate(self.parametric_var, level=level, modified=modified)
        elif isinstance(self.portfolio_returns, pd.Series):
            z = norm.ppf(level / 100)
            if modified:
                # mod z score for skew and kurt
                s = self.portfolio_returns.skew()
                k = self.portfolio_returns.kurtosis()
                z = (z +
                     (z ** 2 - 1) * s / 6 +
                     (z ** 3 - 3 * z) * k / 24 -  # they did k-3
                     (2 * z ** 3 - 5 * z) * (s ** 2) / 36)
            return -(self.portfolio_returns.mean() + z * self.portfolio_returns.std())
        else:
            raise TypeError("Expected Series or DataFrame")

    def cvar_historic(self, level=5):
        """CVAR Historic
        returns the conditional value at risk for a certain alpha level 0-100 of the data"""
        if isinstance(self.portfolio_returns, pd.DataFrame):
            return self.portfolio_returns.dropna().aggregate(self.cvar_historic, level=level)
        elif isinstance(self.portfolio_returns, pd.Series):
            is_beyond = self.portfolio_returns.dropna() <= -self.var_historic(level=level)
            return -self.portfolio_returns.dropna()[is_beyond].mean()
        else:
            raise TypeError("Expected Series or DataFrame")

    def portfolio_beta(self, benchmark = "SPY"):
        if benchmark not in self.benchmark.keys():
            self.benchmark = {benchmark: None}
            end = self.portfolio_returns.index[0].strftime('%m-%d-%Y')
            start = self.portfolio_returns.index[-1].strftime('%m-%d-%Y')
            prices = self.source.get_daily_price_timeframe(benchmark,start, end)['close'][::-1]
            self.benchmark[benchmark] = np.log(prices/ prices.shift(-1)).squeeze()
        combo = pd.concat([self.portfolio_returns, self.benchmark[benchmark]], axis = 1)
        beta = combo.cov()/self.benchmark[benchmark].var()
        return beta['SPY'][beta.index != benchmark].item()

    def asset_beta(self, benchmark = "SPY"):
        if benchmark not in self.benchmark.keys():
            self.benchmark = {benchmark: None}
            end = self.asset_returns.index[0].strftime('%m-%d-%Y')
            start = self.asset_returns.index[-1].strftime('%m-%d-%Y')
            prices = self.source.get_daily_price_timeframe(benchmark,start, end)['close'][::-1]
            self.benchmark[benchmark] = np.log(prices/ prices.shift(-1)).squeeze()
        combo = pd.concat([self.asset_returns, self.benchmark[benchmark]], axis = 1)
        beta = combo.cov()/self.benchmark[benchmark].var()
        return beta['SPY'][beta.index != benchmark].copy()

    def portfolio_alpha(self, benchmark):
        portfolio_return = self.portfolio_returns[::-1].cumsum()[::-1][0]
        if not bool(self.source.risk_free):
            self.source.get_risk_free_rate("1 yr")
        beta = self.portfolio_beta(benchmark)
        benchmark_return = self.benchmark[benchmark][::-1].cumsum()[::-1][0]
        alpha = portfolio_return - self.source.risk_free - beta * (benchmark_return - self.source.risk_free)
        return alpha

    def asset_alpha(self, benchmark):
        total_returns = self.asset_returns[::-1].cumsum()[::-1].iloc[0,:]
        if not bool(self.source.risk_free):
            self.source.get_risk_free_rate("1 yr")
        beta = self.portfolio_beta(benchmark)
        benchmark_return = self.benchmark[benchmark][::-1].cumsum()[::-1][0]
        alpha = total_returns - self.source.risk_free - beta * (benchmark_return - self.source.risk_free)
        return alpha


class StressTest(object):
    def __init__(self, portfolio :Portfolio):
        self.portfolio = portfolio
        self.end_date = portfolio.portfolio_returns.index[0].strftime('%m-%d-%Y')
        self.start_date = portfolio.portfolio_returns.index[-1].strftime('%m-%d-%Y')
        self.factors = None

    def set_factors(self, list_of_tickers: list):
        self.factors = list_of_tickers
        factors = {key: 1 for key in list_of_tickers}
        self.factor_portfolio = Portfolio(factors)
        self.factor_portfolio.calculate_alloc_from_shares()

    def get_factor_data(self):
        self.factor_portfolio.set_source(apikey)
        self.factor_portfolio.get_historical_portfolio_value(self.start_date, self.end_date)

    def regress(self, factors = None):
        if not bool(factors):
            model = sm.OLS(self.portfolio.portfolio_returns.dropna(), (self.factor_portfolio.asset_returns.dropna()))
        else:
            model = sm.OLS(self.portfolio.portfolio_returns.dropna(),(self.factor_portfolio.asset_returns.dropna()[factors]))
        results = model.fit()
        self.regression_results = results
        print(results.summary())


class FinMetrics(object):
    """Pass in array of prices, either of a single asset or entire portfolio.
    This object leverages numpy indices for portfolio calculations."""
    def __init__(self, price_array, shares_array, alloc_array):
        self.alloc_array = alloc_array
        self.shares_array = shares_array
        self.prices_array = price_array
        self.asset_val_array = None
        self.returns_array = None
        self.portfolio_returns = None
        self.metrics = {}

    def get_returns_array(self, log_returns = True):
        if log_returns:
            self.returns_array = np.log(self.prices_array/self.prices_array.shift(1))
        else:
            self.returns_array = self.prices_array.pct_chg()

    def calculate_volatility(self):
        NotImplementedError

    def _calculate_cummulative_returns(self):
        self.metrics['Cummulative Returns'] = self.returns_array.cumsum()

    def _calculate_asset_val_array(self):
        self.asset_val_array = self.shares_array @ self.prices_array

    def _calculate_gain_loss(self):
        self.metrics['Gain/Loss'] = self.asset_val_array[-1,:].sum() - self.asset_val_array[0,:].sum()




