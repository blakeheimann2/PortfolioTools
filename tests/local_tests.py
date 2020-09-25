import unittest
from library.broker import AMTD
from config import apikey
import pandas as pd
from library.portfolio import Portfolio, StressTest


class TestAmtdPy(unittest.TestCase):
    """Tests For AMTDpy API Client"""
    td = AMTD(apikey)
    def test_prices(self):
        for ticker in ['AAPL', 'TSLA', 'WMT']:
            prices = self.td.get_daily_price_hist(ticker, "daily", 1, "year", 1)
            self.assertIsInstance(prices, pd.DataFrame)
            self.assertLessEqual(prices.shape[0], 260)
            self.assertGreaterEqual(prices.shape[0], 245)
            self.assertAlmostEqual(prices.shape[1], 5)

    def test_fundamentals(self):
        for ticker in ['AAPL', 'TSLA', 'WMT']:
            fundamentals = self.td.get_fundamentals(ticker)
            self.assertIsInstance(fundamentals, pd.DataFrame)
            self.assertLessEqual(fundamentals.shape[0], 50)
            self.assertGreaterEqual(fundamentals.shape[0], 40)
            self.assertAlmostEqual(fundamentals.shape[1], 6)

    def test_price_array(self):
        tick_list = ['UBER', 'WMT', 'TSLA']
        prices = self.td.get_ohlcv_array(tick_list, '2019-01-01', '2020-01-01', 'close')
        self.assertIsInstance(prices, pd.DataFrame)
        self.assertLessEqual(prices.shape[0], 260)
        self.assertGreaterEqual(prices.shape[0], 245)
        self.assertLessEqual(prices.shape[1], 5*len(tick_list))

    def test_risk_free_rates(self):
        rate = self.td.get_risk_free_rate()
        print(rate)
        self.assertIsInstance(rate, float)


class test_portfolio(unittest.TestCase):
    """Test the basics functionality of the portfolio object."""
    def test_portfolio_basic(self):
        assets = {'AAPL':10, 'WMT':20}
        my_portfolio = Portfolio(assets)
        print(my_portfolio.assets)
        my_portfolio.calculate_alloc_from_shares()
        print(my_portfolio.asset_alloc)
        my_portfolio.set_source(apikey)
        starting_money = 10000
        my_portfolio.calculate_shares_from_alloc(starting_money)
        print(my_portfolio.assets)
        print(my_portfolio.asset_alloc)
        my_portfolio.calculate_current_value()
        self.assertEqual(len(my_portfolio.assets),len(assets))
        self.assertEqual(sum(my_portfolio.asset_values.values()),starting_money)
        self.assertEqual(len(my_portfolio.asset_alloc),len(assets))
        self.assertEqual(sum(my_portfolio.asset_alloc.values()),1)

        #my_portfolio.get_ohlcv_array('2020-01-01', '2020-05-01')
        my_portfolio.get_historical_asset_returns('2020-01-01', '2020-05-01')
        self.assertLessEqual(my_portfolio.asset_returns.shape[0], 90)
        self.assertGreaterEqual(my_portfolio.asset_returns.shape[0], 70)
        self.assertEqual(my_portfolio.asset_returns.shape[1], len(assets))

        my_portfolio.get_historical_portfolio_returns()
        self.assertLessEqual(my_portfolio.portfolio_returns.shape[0], 90)
        self.assertGreaterEqual(my_portfolio.portfolio_returns.shape[0], 70)
        self.assertFalse(my_portfolio.portfolio_returns.empty)

        my_portfolio.get_historical_portfolio_value()
        self.assertFalse(my_portfolio.historical_value.empty)

        print("DONE")


    def test_portfolio_adv(self):
        #TODO rename portfolio objects to not be portfolio.portfolio....
        assets = {'AAPL': 10, 'WMT': 20}
        my_portfolio = Portfolio(assets)
        print(my_portfolio.assets)
        my_portfolio.calculate_alloc_from_shares()
        print(my_portfolio.asset_alloc)
        my_portfolio.set_source(apikey)
        my_portfolio.get_historical_asset_returns('2020-01-01', '2020-05-01')
        print(my_portfolio.asset_returns.shape)
        self.assertLessEqual(my_portfolio.asset_returns.shape[0], 90)
        self.assertGreaterEqual(my_portfolio.asset_returns.shape[0], 70)
        self.assertEqual(my_portfolio.asset_returns.shape[1], len(assets))

        my_portfolio.get_historical_portfolio_returns('2020-01-01', '2020-02-01')
        print(my_portfolio.asset_returns.shape)
        print(my_portfolio.portfolio_returns.shape)

        self.assertLessEqual(my_portfolio.portfolio_returns.shape[0], 24)
        self.assertGreaterEqual(my_portfolio.portfolio_returns.shape[0], 19)
        self.assertFalse(my_portfolio.portfolio_returns.empty)
        self.assertLessEqual(my_portfolio.asset_returns.shape[0], 24)
        self.assertGreaterEqual(my_portfolio.asset_returns.shape[0], 19)
        self.assertEqual(my_portfolio.asset_returns.shape[1], len(assets))


        my_portfolio.get_historical_portfolio_value('2020-01-01', '2020-03-01')
        print(my_portfolio.asset_returns.shape)
        print(my_portfolio.portfolio_returns.shape)
        print(my_portfolio.historical_value.shape)

        self.assertLessEqual(my_portfolio.portfolio_returns.shape[0], 48)
        self.assertGreaterEqual(my_portfolio.portfolio_returns.shape[0], 40)
        self.assertFalse(my_portfolio.portfolio_returns.empty)
        self.assertLessEqual(my_portfolio.asset_returns.shape[0], 48)
        self.assertGreaterEqual(my_portfolio.asset_returns.shape[0], 40)
        self.assertEqual(my_portfolio.asset_returns.shape[1], len(assets))
        self.assertFalse(my_portfolio.historical_value.empty)


    def test_vol(self):
        assets = {'AAPL': 10, 'WMT': 20}
        my_portfolio = Portfolio(assets)
        my_portfolio.calculate_alloc_from_shares()
        my_portfolio.set_source(apikey)
        my_portfolio.get_historical_portfolio_value('2020-01-01', '2020-03-01')
        vol = my_portfolio.get_asset_volatility()
        print(vol)
        self.assertEqual(vol.shape, my_portfolio.asset_returns.shape)
        pvol = my_portfolio.get_portfolio_volatility()
        print(pvol)
        self.assertEqual(pvol.shape, my_portfolio.portfolio_returns.shape)

class test_portfolio_metrics(unittest.TestCase):
    """Test the metrics calculations in the portfolio object"""
    assets = {'AAPL': 10, 'WMT': 20}
    my_portfolio = Portfolio(assets)
    my_portfolio.calculate_alloc_from_shares()
    my_portfolio.set_source(apikey)
    my_portfolio.get_historical_portfolio_value('2020-01-01', '2020-03-01')
    def test_metrics1(self):
        ac = self.my_portfolio.asset_corr()
        self.assertEqual(ac.shape, (len(self.assets), len(self.assets)))

        ar = self.my_portfolio.cumm_asset_returns()
        self.assertEqual(ar.shape, self.my_portfolio.asset_returns.shape)

        pr = self.my_portfolio.cumm_portfolio_returns()
        self.assertEqual(pr.shape, self.my_portfolio.portfolio_returns.shape)

        drawdown = self.my_portfolio.max_drawdown()
        print(drawdown)
        self.assertEqual(len(drawdown), 3)

        sharpe = self.my_portfolio.sharpe_ratio()
        print(float)
        self.assertIsInstance(sharpe, float)

    def test_metrics2(self):
        pf_skew =self.my_portfolio.portfolio_skew()
        print(pf_skew)
        self.assertIsInstance(pf_skew, float)

        pf_kurtosis = self.my_portfolio.portfolio_kurtosis()
        print(pf_kurtosis)
        self.assertIsInstance(pf_kurtosis, float)

        a_skew =self.my_portfolio.asset_skew()
        print(a_skew)
        self.assertEqual(len(a_skew), len(self.assets))

        a_kurtosis = self.my_portfolio.asset_kurtosis()
        print(a_kurtosis)
        self.assertEqual(len(a_kurtosis), len(self.assets))

    def test_vars(self):
        gvar = self.my_portfolio.parametric_var(modified=True)
        hvar = self.my_portfolio.var_historic()
        cvar = self.my_portfolio.cvar_historic()


        print(cvar)
        print(gvar)
        print(hvar)
        self.assertIsInstance(gvar, float)
        self.assertIsInstance(cvar, float)
        self.assertIsInstance(hvar, float)

    def test_beta(self):
        beta = self.my_portfolio.portfolio_beta()
        print(beta)
        self.assertIsInstance(beta, float)

        a_beta = self.my_portfolio.asset_beta()
        print(a_beta)
        self.assertIs(len(a_beta), len(self.assets))

    def test_alpha(self):
        alpha = self.my_portfolio.portfolio_alpha("SPY")
        self.assertIsInstance(alpha, float)
        alpha = self.my_portfolio.asset_alpha("SPY")
        self.assertEqual(len(alpha), len(self.assets))
        self.assertIsInstance(alpha, pd.Series)

class TestST(unittest.TestCase):
    """Test the StressTester"""
    def test_stress_test(self):
        assets = {'AAPL': 10, 'WMT': 20}
        my_portfolio = Portfolio(assets)
        my_portfolio.calculate_alloc_from_shares()
        my_portfolio.set_source(apikey)
        my_portfolio.get_historical_portfolio_value('2020-01-01', '2020-03-01')
        Stress = StressTest(my_portfolio)
        #factors = ['XLB', 'XLY', 'XLF', 'IYR', 'XLP', 'XLV', 'XLU', 'IYZ', 'XLE', 'XLI', 'XLK']
        factors = ['USO', 'GLD', 'BIL', 'VIX']
        Stress.set_factors(factors)
        Stress.get_factor_data()
        Stress.regress()
        self.assertEqual(len(Stress.portfolio.asset_returns), len(Stress.factor_portfolio.asset_returns))
        self.assertNotEqual(Stress.regression_results,None)