import pandas as pd
import matplotlib.pyplot as plt
import pandas_datareader as pdr
from datetime import datetime


def load_data(stock, starttime, endtime):
  data = pdr.get_data_yahoo(symbols=stock, start=starttime, end=endtime)
  data = data["Adj Close"].to_frame()
  data = data.rename(columns={"Adj Close": stock})
  return data

def get_data(symbols, starttime, endtime):
    # Create an empty dataframe
    SPY = load_data('SPY', starttime, endtime)
    df1 = pd.DataFrame(index = SPY.index)
    df1 = df1.join(SPY, how = "inner")

    for symbol in symbols:
        stock = pdr.get_data_yahoo(symbols=symbol, start=starttime, end=endtime)
        stock = stock["Adj Close"].to_frame()
        stock = stock.rename(columns={"Adj Close": symbol})
        df1 = df1.join(stock, how="inner")
    return df1

def get_data_no_spy(symbols, starttime, endtime):
        SPY = load_data('SPY', starttime, endtime)
        df1 = pd.DataFrame(index = SPY.index)
        for symbol in symbols:
            stock = pdr.get_data_yahoo(symbols=symbol, start=starttime, end=endtime)
            stock = stock["Adj Close"].to_frame()
            stock = stock.rename(columns={"Adj Close": symbol})
            df1 = df1.join(stock, how="inner")
        return df1
        

def normalize_data(df):
    return df / df.iloc[0, :]


def plot_data(df, title="Stock Prices"):
    ax = df.plot(title=title, fontsize=10)
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend(loc = 'upper left')
    # plt.axhline(y=0, color='r', linestyle='-')
    plt.show()

def compute_daily_returns(df):
    daily_returns = (df/df.shift(1))-1
    return daily_returns

def compute_cum_returns(df, stock):
    daily_returns = (df[stock].iloc[-1]/df[stock].iloc[0])-1
    return daily_returns

def get_bollinger_bands(rm, rstd):
    """Returns the upper and lower Bollinger Bands"""
    upper_band = rm + rstd * 2
    lower_band = rm - rstd * 2
    return upper_band, lower_band


def rolling(df, ticker, day):
    ax = df[ticker].plot(title="FSLY rolling mean", label="Actual Price")

    #  Computer rolling mean using 20-day window
    NVDA_rm = df[ticker].rolling(day).mean()
    NVDA_rm.plot(label= str(day) + " day rolling mean", ax=ax)

    NVDA_std = df[ticker].rolling(day).std()

    upper_band, lower_band = get_bollinger_bands(NVDA_rm, NVDA_std)

    upper_band.plot(label="upper band", ax=ax)

    lower_band.plot(label="lower band", ax=ax)

    ax.legend(loc="upper left")
    plt.show()

def test_run():
    df = get_data(["FSLY", "TTD", "NET", "QQQ", "SQ", "DOCU", "TWLO", "SE", "WIX"], datetime(2020, 1, 1), datetime(2020, 6, 18))

    # Plot data is the main function and plots the normalized returns of all the tickers
    # plot_data(normalize_data(df))

    # Rolling plots the x day moving average of a particular ticker
    # rolling(df, "FSLY", 10)

    # Below gets the correlation matrix of all of your positions
    # daily_returns = compute_daily_returns(df)
    # print(daily_returns.corr(method = "pearson"))




if __name__ == "__main__":
    test_run()
