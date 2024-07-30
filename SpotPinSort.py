import pandas as pd
import requests


# 用于存储插针次数的字典
pin_count_dict = {} 

def get_symbols():
    url = 'https://www.okx.com/api/v5/public/instruments?instType=SPOT'
    response = requests.get(url)
    data = response.json()
    symbols = [symbol['instId'] for symbol in data['data'] if 'USDT' in symbol['instId']]
    excluded_symbols = ['USDT-BRL','USDT-EUR','USDT-USDC']
    symbols = [symbol for symbol in symbols if symbol not in excluded_symbols]
    return symbols

def get_historical_klines(symbol, bar='1H', limit=200):
    url = f'https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}'
    while True:
        try:
            response = requests.get(url)
            data = response.json()
            df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'volCcyQuote', 'confirm'])
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['timestamp'] = pd.to_datetime(df['timestamp'],unit='ms')
            df = df.iloc[::-1].reset_index(drop=True)  # 颠倒顺序并重置索引
            return df
        except (requests.exceptions.RequestException, ValueError, IndexError, KeyError) as e:
            print(f'Error: {e}')
            time.sleep(5)

symbols = get_symbols()  # 获取交易对列表

for symbol in symbols:
    try:
        # 获取交易对的历史小时 K 线数据
        df = get_historical_klines(symbol)
        print(df)
        pin_count = 0
        for i in range(1, len(df)):  # 从第二行开始，与前一小时的收盘价比较
            prev_close = df['close'][i - 1]
            current_high = df['high'][i]
            current_low = df['low'][i]
            # 判断向上插针（当前小时最高价与前一小时收盘价的差异超过 6%）
            if (current_high - prev_close) / prev_close > 0.06: 
                pin_count += 1 

            # 判断向下插针（前一小时收盘价与当前小时最低价的差异超过 6%）
            if (prev_close - current_low) / prev_close > 0.06: 
                pin_count += 1 
        pin_count_dict[symbol] = pin_count
    except Exception as e:
        print(f"获取 {symbol} 的数据时出错: {e}")

# 对插针次数进行排序并获取前 20 的代币及插针次数
sorted_pin_count = sorted(pin_count_dict.items(), key=lambda x: x[1], reverse=True)[:20] 

for symbol, count in sorted_pin_count:
    print(f"{symbol}: {count} 次插针")
