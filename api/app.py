from flask import Flask, render_template, request
import yfinance as yf
from forex_analyzer import EnhancedForexAnalyzer
from datetime import datetime, timedelta
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available currency pairs and their display names
AVAILABLE_PAIRS = ["CAD=X", "EURJPY=X", "GBPUSD=X", "AUDUSD=X", "EURUSD=X"]
PAIR_DISPLAY_NAMES = {
    "CAD=X": "USD/CAD",
    "EURJPY=X": "EUR/JPY",
    "GBPUSD=X": "GBP/USD",
    "AUDUSD=X": "AUD/USD",
    "EURUSD=X": "EUR/USD"
}

def fetch_and_analyze_data(selected_pair):
    current_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = current_date - timedelta(days=30)
    intervals = ["5m", "15m", "30m", "60m"]
    results = {}

    for interval in intervals:
        logger.info(f"Fetching data for {selected_pair} - {interval} interval...")
        try:
            # Fetch data with auto_adjust=False and group_by='ticker' to avoid MultiIndex
            data = yf.download(selected_pair,
                              start=start_date.strftime('%Y-%m-%d'),
                              end=current_date.strftime('%Y-%m-%d'),
                              interval=interval,
                              auto_adjust=False,  # Explicitly disable auto_adjust
                              group_by='ticker')  # Ensure single-level columns
            if data.empty:
                logger.warning(f"Initial data fetch failed for {interval}. Attempting fallback fetch.")
                # Fallback fetch using period instead of date range
                data = yf.download(selected_pair,
                                  period="1mo",
                                  interval=interval,
                                  auto_adjust=False,
                                  group_by='ticker')
                if data.empty:
                    logger.error(f"Fallback fetch failed for {selected_pair} on {interval} interval.")
                    results[interval] = {"error": f"No data retrieved for {selected_pair} on {interval} interval after fallback."}
                    continue

            # Debug: Log DataFrame structure
            logger.info(f"Data fetched for {selected_pair} on {interval} interval. Shape: {data.shape}, Columns: {list(data.columns)}")

            analyzer = EnhancedForexAnalyzer(adapt_weights=True, optimize_params=False)
            analyzer.load_data(data)
            analyzer.calculate_indicators()
            analyzer.generate_signals()
            analyzer.calculate_take_profit_stop_loss()
            backtest = analyzer.backtest(initial_capital=10000)

            results[interval] = {
                'backtest': backtest['stats'],
                'latest_signal': analyzer.data['Combined_Signal'].iloc[-1],
                'latest_time': analyzer.data.index[-1].strftime('%Y-%m-%d %H:%M'),
                'current_price': analyzer.data['Close'].iloc[-1],
                'stop_loss_long': analyzer.data['Stop_Loss_Long'].iloc[-1],
                'take_profit_long': analyzer.data['Take_Profit_Long'].iloc[-1],
                'stop_loss_short': analyzer.data['Stop_Loss_Short'].iloc[-1],
                'take_profit_short': analyzer.data['Take_Profit_Short'].iloc[-1],
                'signal_interpretation': analyzer.interpret_signal(analyzer.data['Combined_Signal'].iloc[-1]),
                'market_regime': analyzer.market_regime
            }
        except Exception as e:
            logger.error(f"Error processing {selected_pair} on {interval} interval: {str(e)}")
            results[interval] = {"error": f"Failed to process data for {selected_pair}: {str(e)}"}
    
    return results

@app.route('/')
def index():
    selected_pair = request.args.get('pair', 'CAD=X')
    if selected_pair not in AVAILABLE_PAIRS:
        logger.warning(f"Invalid pair selected: {selected_pair}. Falling back to default 'CAD=X'.")
        selected_pair = "CAD=X"  # Fallback to default if invalid pair
    
    # Get the display name for the selected pair
    display_pair = PAIR_DISPLAY_NAMES.get(selected_pair, selected_pair)
    
    analysis_results = fetch_and_analyze_data(selected_pair)
    return render_template('index.html', 
                         results=analysis_results, 
                         intervals=["5m", "15m", "30m", "60m"],
                         available_pairs=AVAILABLE_PAIRS,
                         selected_pair=selected_pair,
                         display_pair=display_pair,
                         PAIR_DISPLAY_NAMES=PAIR_DISPLAY_NAMES)  # Pass PAIR_DISPLAY_NAMES to the template

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)