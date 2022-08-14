# Import Libraries
import os
import json
import pandas as pd
import pandas_datareader as pdr
import numpy as np
import yfinance as yf
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px


from datetime import datetime, timedelta
from requests import Session

yf.pdr_override()
sns.set_theme()


# CMC DATA
def cmc_sessions(url):
    cmc_api_key = os.environ['CMC_PRO_API_KEY']

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': cmc_api_key,
    }

    session = Session()
    session.headers.update(headers)
    response = session.get(url)
    return response


def cmc_coins_info(num_pairs):
    # Obtain information about crypto. Limit the number of options according to the cmc ranking
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    cmc_map = json.loads(cmc_sessions(url).text)

    # Create the dictionary
    crypto_dict = {}

    for i in range(len(cmc_map['data'])):
        if cmc_map['data'][i]['cmc_rank'] <= num_pairs:
            crypto_dict[cmc_map['data'][i]['symbol']] = \
                {'name': cmc_map['data'][i]['name'],
                 'price': cmc_map['data'][i]['quote']['USD']['price'],
                 '% 1h_change': cmc_map['data'][i]['quote']['USD']['percent_change_1h'],
                 '% 24h_change': cmc_map['data'][i]['quote']['USD']['percent_change_24h'],
                 '% 7d_change': cmc_map['data'][i]['quote']['USD']['percent_change_7d'],
                 '% 30d_change': cmc_map['data'][i]['quote']['USD']['percent_change_30d'],
                 '% 60d_change': cmc_map['data'][i]['quote']['USD']['percent_change_60d'],
                 '% 90d_change': cmc_map['data'][i]['quote']['USD']['percent_change_90d'],
                 'Marketcap': cmc_map['data'][i]['quote']['USD']['market_cap'],
                 'rank': cmc_map['data'][i]['cmc_rank'],
                 'id': cmc_map['data'][i]['id']}

    crypto_dict = dict(sorted(crypto_dict.items(), key=lambda x: x[1]['rank'], reverse=False))

    # Create the DataFrame
    df = pd.DataFrame.from_dict(crypto_dict, orient='index').reset_index()
    df.rename(columns={'index': 'symbol'}, inplace=True)
    df = df.iloc[:, :-3]
    return df

def cmc_pairs(output, num_pairs):

    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    cmc_map = json.loads(cmc_sessions(url).text)
    pairs_dict = {}

    for i in range(len(cmc_map['data'])):
        pairs_dict[cmc_map['data'][i]['symbol']] = \
            {'name': cmc_map['data'][i]['name'],
             'rank': cmc_map['data'][i]['cmc_rank']}

    pairs_dict = dict(sorted(pairs_dict.items(), key=lambda x: x[1]['rank'], reverse=False))

    if output == 'full':
        return pairs_dict

    else:
        return [i+'-USD' for i in pairs_dict.keys() if i not in ['USDT', 'USDC', 'BUSD', 'DAI', 'WBTC']][:num_pairs]

# YFINANCE DATA

def set_dates(days_back):
    # Return two dates: Today & Today - days_back. It's used for defining dates in yahoo_prices
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    return [start, end]


def yahoo_prices(pairs=None, interval='1d', period=None):
    # Return a dataframe with the prices of a concrete Tickers
    dates = {
        'Last Week': set_dates(7),
        'Last Month': set_dates(30),
        'Last six months': set_dates(180),
        'Last year': set_dates(365),
        'Last two years': set_dates(730)
    }
    return pdr.get_data_yahoo(pairs, interval=interval, start=dates[period][0], end=dates[period][1])['Close']

dates = ['Last Week', 'Last Month', 'Last six months', 'Last year', 'Last two years']


# Init Streamlit
## Crypto General Info Explorer
st.markdown("# 🤓 Crypto Observateur.")
slider_number_crypto = st.slider('Choose the number of Crypto: (Sorted by Marketcap):', 1, 100)
df = cmc_coins_info(slider_number_crypto)


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["General", "% Variation", "Price Evolution (% var)", "CORR.: Crypto vs BTC", "CORR.: All crypto", "CORR.: BTC vs Stocks"])

with tab1:
    # General
    st.dataframe(df)

with tab2:
    # % Variation
    option = st.selectbox('Choose a period:', list(df.columns)[3:])
    fig = px.bar(df, x=option, y='symbol',
                 orientation='h',
                 color=option,
                 height=700)
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    # Price Evolution
    pairs = cmc_pairs('pairs', slider_number_crypto)
    option2 = st.selectbox('Choose a period:', dates)
    data = (yahoo_prices(pairs=pairs, interval='d', period=option2).pct_change() + 1).cumprod() - 1
    fig = px.line(data)
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    # CORR. Vs. BTC
    option3 = st.selectbox('Choose a period: ', dates)
    btc_correlation = yahoo_prices(pairs=pairs, interval='d', period=option3).corr()[
        'BTC-USD'].iloc[1:].sort_values(ascending=True).round(2)
    fig = px.bar(btc_correlation,
                 orientation='h',
                 height=700,
                 color='value',
                 text_auto=True)

    st.plotly_chart(fig, use_container_width=True)

with tab5:
    # CORR. ALL CRYPTO
    option4 = st.selectbox('Choose a period:     ', dates)
    crypto_correlation = yahoo_prices(pairs=pairs, interval='d', period=option4).corr().round(2)
    fig = px.imshow(crypto_correlation, text_auto=True, height=700)
    st.plotly_chart(fig, use_container_width=True)


with tab6:
    # CORR. STOCKS
    option5 = st.selectbox('Choose a period:       ', dates)
    stocks_indexes = {'BTC-USD': 'Bitcoin', '^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ', '^RUT': 'Russell 2000', 'GC=F': 'Gold', 'CL=F': 'Crude Oil'}
    stocks_correlations = yahoo_prices(pairs=list(stocks_indexes.keys()), interval='d', period=option5).corr().round(2).reset_index()
    stocks_correlations['Ticker'] = list(stocks_indexes.values())

    fig = px.bar(stocks_correlations,
                 x='BTC-USD',
                 y='Ticker',
                 orientation='h',
                 color='BTC-USD',
                 height=700,
                 text_auto=True)

    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)




