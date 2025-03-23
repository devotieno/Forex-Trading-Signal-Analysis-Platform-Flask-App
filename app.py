from flask import Flask, render_template
import yfinance as yf
from forex_analyzer import EnhancedForexAnalyzer
from datetime import datetime, timedelta
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_analyze_data():
    current_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = current_date - timedelta(days=30)
    ticker = "CAD=X"
    intervals = ["5m", "15m", "30m", "60m"]
    results = {}

    for interval in intervals:
        logger.info(f"Fetching data for {interval} interval...")
        try:
            data = yf.download(ticker,
                             start=start_date.strftime('%Y-%m-%d'),
                             end=current_date.strftime('%Y-%m-%d %H:%M'),
                             interval=interval)
            if data.empty:
                logger.warning(f"Initial data fetch failed for {interval}. Attempting fallback fetch.")
                data = yf.download(ticker, period="1mo", interval=interval)
                if data.empty:
                    results[interval] = {"error": f"No data retrieved for {interval} after fallback."}
                    continue

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
            logger.error(f"Error processing {interval}: {str(e)}")
            results[interval] = {"error": str(e)}
    
    return results

@app.route('/')
def index():
    analysis_results = fetch_and_analyze_data()
    return render_template('index.html', results=analysis_results, intervals=["5m", "15m", "30m", "60m"])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)