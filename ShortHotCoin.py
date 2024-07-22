import requests
import pandas_ta as ta
import pandas as pd
from scipy.stats import pearsonr
from itertools import combinations
import time

def get_symbols():
    url = 'https://www.okx.com/api/v5/public/instruments?instType=SWAP'
    response = requests.get(url)
    data = response.json()
    symbols = [symbol['instId'] for symbol in data['data'] if 'USDT' in symbol['instId']]
    excluded_symbols = ['USDC-USDT-SWAP','TUSD-USDT-SWAP','FDUSD-USDT-SWAP']
    symbols = [symbol for symbol in symbols if symbol not in excluded_symbols]
    return symbols

def get_historical_klines(symbol, bar='1H', limit=200):
    url = f'https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}'
    while True:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()['data']
            #print(f'Data for {symbol}: {data}')
            df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume','quote_volume','volCcyQuote','confirm'])
            df['close'] = df['close'].astype(float)
            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['timestamp'] = pd.to_datetime(df['timestamp'],unit='ms')
            df = df.iloc[:: -1]
            df['ema25'] = ta.ema(df['close'], 25)
            df = slope(df)
            #print(df)
            return df
        except (requests.exceptions.RequestException, ValueError, IndexError, KeyError) as e:
            print(f'Error: {e}')
            time.sleep(5)

def slope(df):  
    df['emaSlope'] = df['ema25'].rolling(window=21).apply(lambda x: ((x[-1] - x[0]) / 20) / df['close'].iloc[-1] * 100, raw=True)
    return df             

def calculate_7d_price_increase_and_drawdown(symbols):
    result_data = {}
    current_time = pd.Timestamp.now()
    for symbol in symbols:
        df = get_historical_klines(symbol)
        if df is not None:
            start_time = current_time - pd.Timedelta(days=7)
            df_7d = df[df['timestamp'] >= start_time]
            if not df_7d.empty:
                lowest_price = df_7d['close'].min()
                highest_price = df_7d['close'].max()
                current_price = df_7d['close'].iloc[-1]
                current_slope = df_7d['emaSlope'].iloc[-1]
                price_increase = (current_price - lowest_price) / lowest_price * 100
                drawdown = (highest_price - current_price) / highest_price * 100
                print(f"币种: {symbol} 当前价格{current_price} 涨幅为 {price_increase} 回撤为 {drawdown} 当前斜率 {current_slope}")
                result_data[symbol] = {'increase': price_increase, 'drawdown': drawdown, 'scope':current_slope}
    return result_data

def get_top_20_price_increase_symbols(result_data):
    sorted_increases = sorted(result_data.items(), key=lambda x: x[1]['increase'], reverse=True)
    top_20_symbols = sorted_increases[:20]
    return top_20_symbols

def main():
    symbols = get_symbols()
    result_data = calculate_7d_price_increase_and_drawdown(symbols)
    top_20_symbols = get_top_20_price_increase_symbols(result_data)
    for symbol, data in top_20_symbols:
        print(f"涨幅排名的币种: {symbol} 涨幅为 {data['increase']}，回撤为 {data['drawdown']},当前斜率 {data['scope']}")

if __name__ == "__main__":
    main()
