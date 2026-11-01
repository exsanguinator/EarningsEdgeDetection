"""
Core options analysis functionality.
Handles volatility calculations and options chain analysis.
"""

import logging
import math
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.interpolate import interp1d

from .market_calendar import EASTERN, eastern_today


def years_to_expiry(expiry: str) -> float:
    """Years from now to the 4 pm ET close on the expiration date, at least one hour."""
    close = EASTERN.localize(datetime.strptime(expiry, "%Y-%m-%d").replace(hour=16))
    seconds = (close - datetime.now(EASTERN)).total_seconds()
    return max(seconds, 3600) / (365 * 24 * 3600)


def bs_delta(price: float, strike: float, years: float, iv: float, is_call: bool) -> Optional[float]:
    """Black-Scholes delta with zero rate and dividends, or None for an unusable IV.

    yfinance chains carry impliedVolatility but no greeks. An IV below 1% is
    treated as missing: yfinance reports near-zero IVs for stale quotes.
    """
    if not (iv >= 0.01 and years > 0 and price > 0 and strike > 0):
        return None
    d1 = (np.log(price / strike) + 0.5 * iv * iv * years) / (iv * np.sqrt(years))
    n_d1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
    return n_d1 if is_call else n_d1 - 1


def chain_deltas(options: pd.DataFrame, price: float, expiry: str, is_call: bool) -> pd.Series:
    """The chain's own delta column if it has one, else deltas computed from impliedVolatility."""
    if 'delta' in options.columns:
        return options['delta']
    years = years_to_expiry(expiry)
    return pd.Series(
        [bs_delta(price, k, years, iv, is_call) for k, iv in zip(options['strike'], options['impliedVolatility'])],
        index=options.index, dtype=float,
    )

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class OptionsAnalyzer:
    def __init__(self):
        self.warnings_shown = False
    
    def filter_dates(self, dates: List[str]) -> List[str]:
        """Filter option expiration dates to those 45+ days out."""
        today = eastern_today()
        cutoff_date = today + timedelta(days=45)
        sorted_dates = sorted(datetime.strptime(date, "%Y-%m-%d").date() 
                            for date in dates)
        
        arr = []
        for i, date in enumerate(sorted_dates):
            if date >= cutoff_date:
                arr = [d.strftime("%Y-%m-%d") for d in sorted_dates[:i+1]]
                break
        
        if arr:
            if arr[0] == today.strftime("%Y-%m-%d") and len(arr) > 1:
                return arr[1:]
            return arr
        return [x.strftime("%Y-%m-%d") for x in sorted_dates]

    def yang_zhang_volatility(self, price_data: pd.DataFrame, 
                            window: int = 30,
                            trading_periods: int = 252,
                            return_last_only: bool = True) -> float:
        """Calculate Yang-Zhang volatility."""
        try:
            log_ho = np.log(price_data['High'] / price_data['Open'])
            log_lo = np.log(price_data['Low'] / price_data['Open'])
            log_co = np.log(price_data['Close'] / price_data['Open'])
            log_oc = np.log(price_data['Open'] / price_data['Close'].shift(1))
            log_oc_sq = log_oc**2
            log_cc = np.log(price_data['Close'] / price_data['Close'].shift(1))
            log_cc_sq = log_cc**2
            
            rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
            close_vol = log_cc_sq.rolling(window=window).sum() / (window - 1.0)
            open_vol = log_oc_sq.rolling(window=window).sum() / (window - 1.0)
            window_rs = rs.rolling(window=window).sum() / (window - 1.0)
            
            k = 0.34 / (1.34 + (window + 1) / (window - 1))
            result = np.sqrt(open_vol + k * close_vol + (1 - k) * window_rs) * np.sqrt(trading_periods)
            
            if return_last_only:
                return result.iloc[-1]
            return result.dropna()
            
        except Exception as e:
            if not self.warnings_shown:
                warnings.warn(f"Error in volatility calculation: {str(e)}. Using simple volatility.")
                self.warnings_shown = True
            return self.calculate_simple_volatility(price_data, window, trading_periods, return_last_only)

    def calculate_simple_volatility(self, price_data: pd.DataFrame,
                                  window: int = 30,
                                  trading_periods: int = 252,
                                  return_last_only: bool = True) -> float:
        """Calculate simple volatility as fallback method."""
        try:
            returns = price_data['Close'].pct_change().dropna()
            vol = returns.rolling(window=window).std() * np.sqrt(trading_periods)
            if return_last_only:
                return vol.iloc[-1]
            return vol
        except Exception as e:
            warnings.warn(f"Error in simple volatility calculation: {str(e)}")
            return np.nan

    def build_term_structure(self, days: List[int], ivs: List[float]) -> callable:
        """Build IV term structure using linear interpolation."""
        try:
            days_arr = np.array(days)
            ivs_arr = np.array(ivs)
            sort_idx = days_arr.argsort()
            days_arr = days_arr[sort_idx]
            ivs_arr = ivs_arr[sort_idx]
            
            spline = interp1d(days_arr, ivs_arr, kind='linear', fill_value="extrapolate")
            
            def term_spline(dte: float) -> float:
                if dte < days_arr[0]:
                    return float(ivs_arr[0])
                elif dte > days_arr[-1]:
                    return float(ivs_arr[-1])
                else:
                    return float(spline(dte))
            
            return term_spline
        except Exception as e:
            warnings.warn(f"Error in term structure calculation: {str(e)}")
            return lambda x: np.nan

    def compute_recommendation(self, ticker: str) -> Dict:
        """Analyze options and compute trading recommendation."""
        try:
            ticker = ticker.strip().upper()
            if not ticker:
                return {"error": "No symbol provided."}

            stock = yf.Ticker(ticker)
            if not stock.options:
                return {"error": f"No options for {ticker}."}

            exp_dates = self.filter_dates(list(stock.options))
            options_chains = {date: stock.option_chain(date) for date in exp_dates}

            # Get current price
            hist = stock.history(period='1d')
            if hist.empty:
                return {"error": "No price data available"}
            current_price = hist['Close'].iloc[-1]

            # Calculate ATM IV for each expiration
            atm_ivs = {}
            straddle = None
            first_chain = True

            for exp_date, chain in options_chains.items():
                calls, puts = chain.calls, chain.puts
                if calls.empty or puts.empty:
                    continue

                call_idx = (calls['strike'] - current_price).abs().idxmin()
                put_idx = (puts['strike'] - current_price).abs().idxmin()
                
                call_iv = calls.loc[call_idx, 'impliedVolatility']
                put_iv = puts.loc[put_idx, 'impliedVolatility']
                atm_iv = (call_iv + put_iv) / 2.0
                atm_ivs[exp_date] = atm_iv

                if first_chain:
                    # Calculate straddle price for first expiration
                    call_mid = (calls.loc[call_idx, 'bid'] + calls.loc[call_idx, 'ask']) / 2
                    put_mid = (puts.loc[put_idx, 'bid'] + puts.loc[put_idx, 'ask']) / 2
                    straddle = call_mid + put_mid
                    
                    # ATM deltas: the chain's own, or computed from its IV
                    atm_call_delta = chain_deltas(calls.loc[[call_idx]], current_price, exp_date, True).iloc[0]
                    atm_put_delta = chain_deltas(puts.loc[[put_idx]], current_price, exp_date, False).iloc[0]
                    if pd.isna(atm_call_delta) or pd.isna(atm_put_delta):
                        atm_call_delta = atm_put_delta = None
                    
                    first_chain = False

            if not atm_ivs:
                return {"error": "Could not calculate ATM IVs"}

            # Build term structure
            today = eastern_today()
            dtes = [(datetime.strptime(exp, "%Y-%m-%d").date() - today).days 
                   for exp in atm_ivs.keys()]
            ivs = list(atm_ivs.values())
            
            term_spline = self.build_term_structure(dtes, ivs)
            iv30 = term_spline(30)
            slope = (term_spline(45) - term_spline(min(dtes))) / (45 - min(dtes))

            # Calculate historical volatility
            hist_data = stock.history(period='3mo')
            hist_vol = self.yang_zhang_volatility(hist_data)
            
            # Get volume data
            avg_volume = hist_data['Volume'].rolling(30).mean().dropna().iloc[-1]

            # Check if we have deltas to return
            result_dict = {
                'avg_volume': avg_volume >= 1_500_000,
                'iv30_rv30': iv30 / hist_vol if hist_vol > 0 else 9999,
                'term_slope': slope,
                'term_structure_valid': slope <= -0.004,
                'term_structure_tier2': slope <= -0.006,
                'expected_move': f"{(straddle/current_price*100):.2f}%" if straddle else "N/A",
                'current_price': current_price,
                'ticker': ticker,
                'recommendation': 'BUY' if iv30 < hist_vol and avg_volume >= 1_500_000 else 'SELL' if iv30 > hist_vol * 1.2 else 'HOLD'
            }
            
            # Add ATM deltas if available
            if 'atm_call_delta' in locals() and 'atm_put_delta' in locals() and atm_call_delta is not None and atm_put_delta is not None:
                result_dict['atm_call_delta'] = atm_call_delta
                result_dict['atm_put_delta'] = atm_put_delta
            
            return result_dict
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {str(e)}")
            return {
                "error": f"Failed to compute recommendation: {str(e)}",
                "ticker": ticker if 'ticker' in locals() else "UNKNOWN",
                "status": "ERROR"
            }
