import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import base64

try: 
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except Exception:
    STREAMLIT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, n=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()

def simulate_exit(df, start_idx, entry, sl, tp):
    is_long = tp > entry
    for j in range(start_idx + 1, len(df)):
        high = df['High'].iat[j]
        low = df['Low'].iat[j]
        t = df.index[j]
        if is_long:
            if low <= sl:
                return float(sl), t, float(sl - entry)
            if high >= tp:
                return float(tp), t, float(tp - entry)
        else:
            if high >= sl:
                return float(sl), t, float(entry - sl)
            if low <= tp:
                return float(tp), t, float(entry - tp)
    last = float(df['Close'].iat[-1])
    t = df.index[-1]
    return last, t, float((last - entry) if is_long else (entry - last))

def run_backtest(df, params):
    df = df.copy()
    for col in ['Open','High','Low','Close']:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")
    df['EMA'] = ema(df['Close'], params.get('ema_period',200))
    df['ATR'] = atr(df, n=params.get('atr_period',14))
    trades = []
    lookback = int(params.get('swing_lookback',100))
    if len(df) <= lookback + 1:
        return pd.DataFrame()
    for i in range(lookback, len(df)-1):
        price = float(df['Close'].iat[i])
        ema_val = float(df['EMA'].iat[i]) if not pd.isna(df['EMA'].iat[i]) else np.nan
        current_atr = float(df['ATR'].iat[i]) if not pd.isna(df['ATR'].iat[i]) else np.nan
        if pd.isna(ema_val) or pd.isna(current_atr):
            continue
        trend = 'long' if price > ema_val else 'short'
        slice_df = df.iloc[i-lookback:i+1]
        swing_high = float(slice_df['High'].max())
        swing_low = float(slice_df['Low'].min())
        move_size = swing_high - swing_low
        if move_size <= 0 or np.isnan(move_size):
            continue
        if trend == 'long':
            rp30 = swing_high - params['retrace_pct']/100.0 * move_size
            rp50 = swing_high - 0.5 * move_size
            target = rp30 if params['retrace_pct'] <= 30 else rp50
            low_i = float(df['Low'].iat[i])
            high_i = float(df['High'].iat[i])
            if low_i <= target <= high_i:
                entry = float(df['Open'].iat[i+1])
                if params['sl_type'] == 'ATR':
                    sl = entry - params['sl_mult'] * current_atr
                else:
                    sl = entry - params['sl_points']
                if sl >= entry:
                    continue
                tp = entry + params['rr'] * (entry - sl)
                exit_price, exit_time, pnl = simulate_exit(df, i+1, entry, sl, tp)
                trades.append({'entry_time': df.index[i+1], 'entry_price': entry, 'side':'long', 'sl':sl, 'tp':tp, 'exit_time': exit_time, 'exit_price': exit_price, 'pnl': pnl})
        else:
            rp30 = swing_low + params['retrace_pct']/100.0 * move_size
            rp50 = swing_low + 0.5 * move_size
            target = rp30 if params['retrace_pct'] <= 30 else rp50
            low_i = float(df['Low'].iat[i])
            high_i = float(df['High'].iat[i])
            if low_i <= target <= high_i:
                entry = float(df['Open'].iat[i+1])
                if params['sl_type'] == 'ATR':
                    sl = entry + params['sl_mult'] * current_atr
                else:
                    sl = entry + params['sl_points']
                if sl <= entry:
                    continue
                tp = entry - params['rr'] * (sl - entry)
                exit_price, exit_time, pnl = simulate_exit(df, i+1, entry, sl, tp)
                trades.append({'entry_time': df.index[i+1], 'entry_price': entry, 'side':'short', 'sl':sl, 'tp':tp, 'exit_time': exit_time, 'exit_price': exit_price, 'pnl': pnl})
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df = trades_df[['entry_time','entry_price','side','sl','tp','exit_time','exit_price','pnl']]
        trades_df = trades_df.reset_index(drop=True)
    return trades_df

def monte_carlo_from_trades(trades_df, account, sims=1000, random_seed=None):
    if trades_df is None or trades_df.empty:
        return None
    if random_seed is not None:
        np.random.seed(random_seed)
    pnl = trades_df['pnl'].astype(float).values
    n = len(pnl)
    sims_equity = np.zeros((sims, n))
    for s in range(sims):
        sample = np.random.choice(pnl, size=n, replace=True)
        sims_equity[s,:] = np.cumsum(sample) + account
    return sims_equity

def generate_sample_data(periods=2000, freq='H', base=1.10, noise=0.001):
    rng = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq=freq)
    price = base + 0.005 * np.sin(np.linspace(0, 20, periods)) + np.random.normal(0, noise, periods)
    df = pd.DataFrame(index=rng)
    df['Open'] = price
    df['High'] = price + np.abs(np.random.normal(0, 0.002, periods))
    df['Low'] = price - np.abs(np.random.normal(0, 0.002, periods))
    df['Close'] = price + np.random.normal(0, noise / 2, periods)
    df['Volume'] = np.random.randint(100, 1000, size=periods)
    df.index.name = 'datetime'
    return df

def save_plot(fig, filename):
    outdir = 'output'
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, filename)
    fig.savefig(path, bbox_inches='tight')
    return path

def print_backtest_summary(trades_df, account):
    if trades_df is None or trades_df.empty:
        logging.info('No trades generated.')
        return
    total_pnl = trades_df['pnl'].sum()
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]
    win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0
    avg_win = wins['pnl'].mean() if not wins.empty else 0
    avg_loss = losses['pnl'].mean() if not losses.empty else 0
    profit_factor = (wins['pnl'].sum() / -losses['pnl'].sum()) if not losses.empty and losses['pnl'].sum() != 0 else np.nan
    logging.info(f"Trades: {len(trades_df)}, Win rate: {win_rate:.2%}")
    logging.info(f"Total PnL (price-units): {total_pnl:.6f}, Avg win: {avg_win:.6f}, Avg loss: {avg_loss:.6f}, Profit factor: {profit_factor:.3f}")

if STREAMLIT_AVAILABLE:
    def run_streamlit_app():
        st.set_page_config(layout="wide", page_title="Strategy Backtester + Monte Carlo")
        st.title('Strategy Backtester + Monte Carlo Simulator (ATR + Retracement + EMA200)')
        with st.sidebar:
            uploaded = st.file_uploader('Upload OHLC CSV (datetime, Open, High, Low, Close, Volume)', type=['csv'])
            sample_data = st.checkbox('Use sample data (EURUSD sample)', value=False)
            timeframe = st.selectbox('Timeframe (informational)', ['M15','H1','H4','Daily'])
            ema_period = st.number_input('EMA period (for trend filter)', min_value=50, max_value=400, value=200)
            atr_period = st.number_input('ATR period', min_value=2, max_value=50, value=14)
            retrace_pct = st.slider('Retracement % (use 30 or 50)', 10, 90, 30)
            sl_type = st.selectbox('Stop loss type', ['ATR','points'])
            sl_mult = st.number_input('SL multiplier (if ATR)', value=1.0, step=0.1)
            sl_points = st.number_input('SL points (if points)', value=10.0)
            rr = st.number_input('Risk:Reward ratio', min_value=0.5, max_value=10.0, value=2.0, step=0.1)
            swing_lookback = st.number_input('Swing lookback candles', min_value=20, max_value=500, value=100)
            account = st.number_input('Account balance ($)', value=36.0)
            risk_pct = st.number_input('Risk per trade (%)', min_value=0.1, max_value=20.0, value=5.0)
            leverage = st.selectbox('Leverage', ['1:50','1:100','1:200'])
            sims = st.number_input('Monte Carlo sims', min_value=100, max_value=5000, value=500)
            run_btn = st.button('Run Backtest')
        if sample_data and not uploaded:
            df = generate_sample_data()
        else:
            if uploaded is not None:
                try:
                    df = pd.read_csv(uploaded)
                    if 'datetime' in df.columns:
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        df.set_index('datetime', inplace=True)
                    else:
                        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
                        df = df.set_index(df.columns[0])
                except Exception as e:
                    st.error('Could not parse uploaded CSV. Use sample data or provide proper OHLC CSV.')
                    df = pd.DataFrame()
            else:
                df = pd.DataFrame()
        if run_btn and not df.empty:
            params = {'ema_period':int(ema_period),'atr_period':int(atr_period),'retrace_pct':int(retrace_pct),'sl_type':sl_type,'sl_mult':float(sl_mult),'sl_points':float(sl_points),'rr':float(rr),'swing_lookback':int(swing_lookback)}
            trades_df = run_backtest(df, params)
            st.subheader('Backtest Results')
            if trades_df is None or trades_df.empty:
                st.write('No trades found with current parameters. Try changing retracement % or lookback.')
            else:
                st.write(f"Total trades: {len(trades_df)}")
                st.dataframe(trades_df.head(50))
                total_pnl = trades_df['pnl'].sum()
                wins = trades_df[trades_df['pnl']>0]
                losses = trades_df[trades_df['pnl']<=0]
                win_rate = len(wins)/len(trades_df)
                avg_win = wins['pnl'].mean() if not wins.empty else 0
                avg_loss = losses['pnl'].mean() if not losses.empty else 0
                pf = (wins['pnl'].sum() / -losses['pnl'].sum()) if not losses.empty and losses['pnl'].sum() !=0 else np.nan
                st.markdown(f"**Total PnL (price units)**: {total_pnl:.4f}")
                st.markdown(f"**Trades**: {len(trades_df)} | **Win rate**: {win_rate:.2%} | **Avg win**: {avg_win:.4f} | **Avg loss**: {avg_loss:.4f} | **Profit factor**: {pf:.2f}")
                equity = np.cumsum(trades_df['pnl'].values) + account
                fig, ax = plt.subplots()
                ax.plot(equity)
                ax.set_title('Equity curve (no compounding)')
                st.pyplot(fig)
                sims_equity = monte_carlo_from_trades(trades_df, account, sims=int(sims))
                if sims_equity is not None:
                    final_vals = sims_equity[:,-1]
                    p05 = np.percentile(final_vals,5)
                    p50 = np.percentile(final_vals,50)
                    p95 = np.percentile(final_vals,95)
                    st.markdown(f"Monte Carlo final equity: 5th% = {p05:.2f}, median = {p50:.2f}, 95th% = {p95:.2f}")
                    fig2, ax2 = plt.subplots(figsize=(8,4))
                    for i in range(min(50, sims_equity.shape[0])):
                        ax2.plot(sims_equity[i], alpha=0.15)
                    ax2.set_title('Monte Carlo sample equity curves (first 50 sims)')
                    st.pyplot(fig2)
                    fig3, ax3 = plt.subplots()
                    ax3.hist(final_vals, bins=40)
                    ax3.set_title('Distribution of final equity after Monte Carlo sims')
                    st.pyplot(fig3)
                csv = trades_df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="trades.csv">Download trades CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
    run_streamlit_app()
else:
    def run_cli_mode(args):
        logging.info('Running in CLI fallback mode.')
        if args.file:
            if not os.path.exists(args.file):
                logging.error(f"CSV file not found: {args.file}")
                sys.exit(1)
            df = pd.read_csv(args.file)
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
            else:
                try:
                    df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
                    df = df.set_index(df.columns[0])
                except Exception:
                    logging.error('Could not parse datetime from CSV.')
                    sys.exit(1)
        else:
            df = generate_sample_data()
        params = {'ema_period': args.ema_period, 'atr_period': args.atr_period, 'retrace_pct': args.retrace_pct, 'sl_type': args.sl_type, 'sl_mult': args.sl_mult, 'sl_points': args.sl_points, 'rr': args.rr, 'swing_lookback': args.swing_lookback}
        trades_df = run_backtest(df, params)
        print_backtest_summary(trades_df, args.account)
        if trades_df is not None and not trades_df.empty:
            equity = np.cumsum(trades_df['pnl'].values) + args.account
            fig, ax = plt.subplots()
            ax.plot(equity)
            ax.set_title('Equity curve (no compounding)')
            save_plot(fig, 'equity_curve.png')
            sims_equity = monte_carlo_from_trades(trades_df, args.account, sims=args.sims)
            if sims_equity is not None:
                final_vals = sims_equity[:,-1]
                fig2, ax2 = plt.subplots(figsize=(8,4))
                for i in range(min(50, sims_equity.shape[0])):
                    ax2.plot(sims_equity[i], alpha=0.15)
                ax2.set_title('Monte Carlo sample equity curves (first 50 sims)')
                save_plot(fig2, 'monte_carlo_curves.png')
                fig3, ax3 = plt.subplots()
                ax3.hist(final_vals, bins=40)
                ax3.set_title('Distribution of final equity after Monte Carlo sims')
                save_plot(fig3, 'mc_histogram.png')
                logging.info(f"Monte Carlo percentiles: 5%={np.percentile(final_vals,5):.2f}, median={np.percentile(final_vals,50):.2f},95%={np.percentile(final_vals,95):.2f}")
            trades_csv = trades_df.to_csv(index=False)
            outpath = os.path.join('output','trades.csv')
            with open(outpath,'w') as f:
                f.write(trades_csv)
            logging.info(f"Saved trades CSV to {outpath}")
        logging.info('CLI run complete. Check output/ for results.')
    def run_basic_tests():
        logging.info('Running basic tests...')
        df = generate_sample_data(periods=300, freq='H')
        params = {'ema_period':200,'atr_period':14,'retrace_pct':30,'sl_type':'ATR','sl_mult':1.0,'sl_points':10,'rr':2.0,'swing_lookback':50}
        trades_df = run_backtest(df, params)
        assert trades_df is not None
        assert isinstance(trades_df, pd.DataFrame)
        logging.info('Basic tests passed.')
    def parse_args():
        parser = argparse.ArgumentParser(description='Backtester CLI')
        parser.add_argument('--sample', action='store_true')
        parser.add_argument('--file', type=str)
        parser.add_argument('--account', type=float, default=36.0)
        parser.add_argument('--ema_period', type=int, default=200)
        parser.add_argument('--atr_period', type=int, default=14)
        parser.add_argument('--retrace_pct', type=int, default=30)
        parser.add_argument('--sl_type', type=str, default='ATR')
        parser.add_argument('--sl_mult', type=float, default=1.0)
        parser.add_argument('--sl_points', type=float, default=10.0)
        parser.add_argument('--rr', type=float, default=2.0)
        parser.add_argument('--swing_lookback', type=int, default=100)
        parser.add_argument('--sims', type=int, default=500)
        return parser.parse_args()
    if __name__ == '__main__':
        args = parse_args()
        if not args.file and not args.sample:
            logging.info('Defaulting to sample data.')
        try:
            run_basic_tests()
        except AssertionError as e:
            logging.warning(f"Tests warning: {e}")
        run_cli_mode(args)
