"""
Older implementation of Portfolio (tightly coupled with AMTDpy API Client)
"""

from library import broker as td
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time

class portfolio(object):
    """Portfolio Object to get data from TD Ameritrade API, calculate returns, and get Mean-Variance Portfolio."""
    def __init__(self, refresh_tkn = None):
        if bool(refresh_tkn) == True:
            self.at = td.generate_access_token(refresh_tkn)
            self.IB, self.PB, self.CB, self.Cpos = td.get_retail_account_info(self.at)
    ##THIS NEEDS A SECOND LOOK

    def get_portfolio(self, pf_dict = None):
        if bool(pf_dict) == True:
            pf_df = pd.DataFrame()
            pf_df['symbol'] = pf_dict.keys()
            pf_df['settledLongQuantity'] = pf_dict.values()
            self.folio = pf_df
        else:
            self.folio = self.Cpos[['symbol', 'settledLongQuantity']]
            self.folio = self.folio[~self.folio.symbol.str.contains("MMDA1")]
        return self.folio

    def get_timeframe_returns(self, start, end):
        self.prices = {}
        date_indices = {}
        indices_len = {}
        for i in self.folio.symbol:
            time.sleep(1)
            self.prices[i] = td.get_price_daily_timeframe(i, start, end)
            self.prices[i] = self.prices[i].set_index('datetime', drop=True)  # may have to remove minutes / hours here...
            self.prices[i].columns = self.prices[i].columns + '_' + str(i)
            # grab all date indexes and set the longet to the index of new df
            date_indices[i] = self.prices[i].index
            indices_len[i] = len(self.prices[i].index)

        self.price_df = pd.DataFrame(index=date_indices[max(indices_len)])
        for i in self.folio.symbol:
            self.price_df = pd.concat([self.price_df, self.prices[i]], axis=1)
        self.close = self.price_df.filter(like='close')
        self.close = self.close.rename(columns={col: col.split('_')[1] for col in self.close.columns})
        self.returns = np.log(self.close.shift(1) / self.close)
        self.current_ps = self.close.tail(1)
        return self.returns

    def get_returns(self, year):
        self.prices = {}
        date_indices = {}
        indices_len = {}
        for i in self.folio.symbol:
            time.sleep(1)
            self.prices[i] = td.get_price_hist(i, "daily", 1, "year", year)
            self.prices[i] = self.prices[i].set_index('datetime', drop=True)  # may have to remove minutes / hours here...
            self.prices[i].columns = self.prices[i].columns + '_' + str(i)
            # grab all date indexes and set the longet to the index of new df
            date_indices[i] = self.prices[i].index
            indices_len[i] = len(self.prices[i].index)

        self.price_df = pd.DataFrame(index=date_indices[max(indices_len)])
        for i in self.folio.symbol:
            self.price_df = pd.concat([self.price_df, self.prices[i]], axis=1)
        self.close = self.price_df.filter(like='close')
        self.close = self.close.rename(columns={col: col.split('_')[1] for col in self.close.columns})
        self.returns = np.log(self.close.shift(1) / self.close)
        self.current_ps = self.close.tail(1)
        return self.returns

    def markowitz_ef(self, num_folios):
        #input is the list of symbols and the dataframe of close prices
        port_returns = []
        port_volatility = []
        stock_weights = []
        sharpe_ratio = []
        num_assets = len(self.folio.symbol)
        num_portfolios = num_folios

        self.returns_daily = self.close.pct_change()
        self.returns_annual = self.returns_daily.mean() * 250
        self.cov_daily = self.returns_daily.cov()
        self.cov_annual = self.cov_daily * 250
        for single_portfolio in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights = weights / np.sum(weights)
            returns = np.dot(weights, self.returns_annual)
            volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_annual, weights)))
            port_returns.append(returns)
            port_volatility.append(volatility)
            sharpe = returns / volatility
            sharpe_ratio.append(sharpe)
            stock_weights.append(weights)
        self.portfolio = {'Returns': port_returns,
                     'Volatility': port_volatility,
                     'Sharpe Ratio': sharpe_ratio}
        # extend original dictionary to accomodate each ticker and weight in the portfolio
        for counter, symbol in enumerate(self.folio.symbol):
            self.portfolio[symbol + ' Weight'] = [Weight[counter] for Weight in stock_weights]
        # make a nice dataframe of the extended dictionary
        self.pf_df = pd.DataFrame(self.portfolio)
        # get better labels for desired arrangement of columns
        column_order = ['Returns', 'Volatility', 'Sharpe Ratio'] + [stock + ' Weight' for stock in self.folio.symbol]
        # reorder dataframe columns
        self.pf_df = self.pf_df[column_order]
        return print("Markowitz Portofolio Matrix Complete; Shape = {}".format(self.pf_df.shape))

    def get_min_var_pf(self):
        # find min Volatility & max sharpe values in the dataframe (df)
        self.min_volatility = self.pf_df['Volatility'].min()
        # use the min, max values to locate and create the two special portfolios
        self.min_variance_port = self.pf_df.loc[self.pf_df['Volatility'] == self.min_volatility].T
        return self.min_variance_port

    def get_sharpe_pf(self):
        self.max_sharpe = self.pf_df['Sharpe Ratio'].max()
        self.sharpe_portfolio = self.pf_df.loc[self.pf_df['Sharpe Ratio'] == self.max_sharpe].T
        return self.sharpe_portfolio

    def plot_efficient_frontier(self):
        self.min_volatility = self.pf_df['Volatility'].min()
        self.min_variance_port = self.pf_df.loc[self.pf_df['Volatility'] == self.min_volatility]
        self.max_sharpe = self.pf_df['Sharpe Ratio'].max()
        self.sharpe_portfolio = self.pf_df.loc[self.pf_df['Sharpe Ratio'] == self.max_sharpe]
        # plot frontier, max sharpe & min Volatility values with a scatterplot
        plt.style.use('seaborn-dark')
        self.pf_df.plot.scatter(x='Volatility', y='Returns', c='Sharpe Ratio',
                        cmap='RdYlGn', edgecolors='black', figsize=(10, 8), grid=True)
        plt.scatter(x=self.sharpe_portfolio['Volatility'], y=self.sharpe_portfolio['Returns'], c='red', marker='D', s=200)
        plt.scatter(x=self.min_variance_port['Volatility'], y=self.min_variance_port['Returns'], c='blue', marker='D', s=200)
        plt.xlabel('Volatility (Std. Deviation)')
        plt.ylabel('Expected Returns')
        plt.title('Efficient Frontier')
        plt.show()
        print("Minimum Variance Portfolio:")
        print(self.min_variance_port.T)
        print("\n")
        print("Maximum Sharpe Portfolio:")
        print(self.sharpe_portfolio.T)

    def get_balanced_portfolio(self, var_or_sharpe):
        if var_or_sharpe == "var":
            self.new_weights = self.min_variance_port.T.filter(like='Weight')
        elif var_or_sharpe == "sharpe":
            self.new_weights = self.sharpe_portfolio.T.filter(like='Weight')
        else:
            print("need to indicate sharpe or var")
        self.new_weights = self.new_weights.reindex(sorted(self.new_weights.columns), axis=1)
        self.rebal = self.new_weights.values * self.CB.loc['longMarketValue'].values
        self.cps = self.current_ps.reindex(sorted(self.current_ps.columns), axis=1)
        self.balanced_portfolio = round(self.rebal / self.cps, 0)
        return self.balanced_portfolio
    def get_pf_trxns(self):
        self.new_port = self.balanced_portfolio.reset_index(drop=True).T
        self.share_trxns = self.new_port.values - self.folio.sort_values(by='symbol').set_index('symbol').values
        self.share_trxns = pd.DataFrame(self.share_trxns).set_index(self.new_port.index)
        return self.share_trxns



