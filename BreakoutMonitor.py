import pandas as pd
import numpy as np
import pandas_ta as ta
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 邮件配置
SMTP_SERVER = 'mtp.163.com'
SMTP_PORT = 465
EMAIL_ADDRESS = 'xxx@163.com'
EMAIL_PASSWORD = 'xxx'
recipients = ['xxxx@163.com']


class BreakoutStrategy:
    def __init__(self):
        self.breakout_symbols = []  # 用于存储突破的交易对

    def fetch_all_symbols(self):
        url = 'https://www.okx.com/api/v5/public/instruments?instType=SPOT'
        response = requests.get(url)
        data = response.json()
        symbols = [symbol['instId'] for symbol in data['data'] if 'USDT' in symbol['instId']]
        excluded_symbols = ['USDT-BRL','USDT-EUR','USDT-USDC']
        symbols = [symbol for symbol in symbols if symbol not in excluded_symbols]
        return symbols

    def check_for_breakout(self, symbol):
        data = self.fetch_data(symbol)
        current_candle_close = data['close'].iloc[-1]
        prev_candle_close = data['close'].iloc[-2]
        prev_candle_open = data['open'].iloc[-2]
        fourth_candle_close = data['close'].iloc[-5]
        second_candle_close = data['close'].iloc[-3]

        volume_sum_of_prev_three_candles = data['volume'].iloc[-5:-2].sum()
        current_candle_volume = data['volume'].iloc[-2]

        sma50_data = ta.sma(data['close'], length=50)
        is_above_sma50 = current_candle_close > sma50_data.iloc[-1]

        prev_candle_price_change_percentage = ((prev_candle_close - prev_candle_open) / prev_candle_open) * 100
        prev_two_candle_change_percentage = ((second_candle_close - fourth_candle_close) / fourth_candle_close) * 100
        adjusted_open_price = prev_candle_close * (1 - 0.02)

        if prev_candle_price_change_percentage > 5 and prev_two_candle_change_percentage < 2 and current_candle_volume > volume_sum_of_prev_three_candles and current_candle_close < adjusted_open_price and is_above_sma50:
            print(f"满足突破条件的交易对: {symbol}")
            self.breakout_symbols.append(symbol)
            # 输出检测到突破的日志
            print(f"检测到交易对 {symbol} 满足突破条件")
            return True
        else:
            # 输出未检测到突破的日志
            print(f"{symbol} 未满足突破条件,上一根K棒涨幅{prev_candle_price_change_percentage:.2f}%,上一根K棒前叠加涨幅{prev_two_candle_change_percentage:.2f}%,当前价格突破SMA50 {is_above_sma50}")
        return False

    def fetch_data(self, symbol):
        url = f'https://www.okx.com/api/v5/market/candles?instId={symbol}&bar=15m&limit=200'
        while True:
            try:
                response = requests.get(url)
                data = response.json()
                df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'volCcyQuote', 'confirm'])
                df['open'] = df['open'].astype(float)
                df['volume'] = df['volume'].astype(float)
                df['close'] = df['close'].astype(float)
                df['timestamp'] = pd.to_numeric(df['timestamp'])
                df['timestamp'] = pd.to_datetime(df['timestamp'],unit='ms')
                df = df.iloc[::-1].reset_index(drop=True)  # 颠倒顺序并重置索引
                return df
            except (requests.exceptions.RequestException, ValueError, IndexError, KeyError) as e:
                print(f'Error: {e}')
                time.sleep(5)

    def send_breakout_email(self):
        if self.breakout_symbols:
            subject = "交易对突破通知"
            body = f"以下交易对满足突破条件：\n" + "\n".join(self.breakout_symbols)
            for recipient in recipients:
                self.send_email(recipient, subject, body)
            self.breakout_symbols = []  # 清空列表，准备下一次检测

    def send_email(self, recipient, subject, body):
        msg = MIMEMultipart()
        msg['From'] = Header(EMAIL_ADDRESS, 'utf-8')
        msg['To'] = Header(recipient, 'utf-8') 
        msg['Subject'] = Header(subject, 'utf-8')
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
                print(f"邮件发送成功: {subject}")
        except Exception as e:
            print(f"邮件发送失败: {e}")

def run_strategy():
    strategy = NewStrategy()
    all_symbols = strategy.fetch_all_symbols()
    while True:
        for symbol in all_symbols:
            strategy.check_for_breakout(symbol)
            time.sleep(1) 

        strategy.send_breakout_email()  # 遍历完所有交易对后发送邮件（如果有突破的交易对）
        time.sleep(60)  # 每分钟运行一次，60 秒 = 1 分钟

def main():
    run_strategy()

if __name__ == "__main__":
    main()
