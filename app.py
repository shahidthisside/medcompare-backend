from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from scraper import scrape_medicines

app = Flask(__name__)
# Allow all origins with a wildcard
CORS(app, resources={r"/api/*": {"origins": "*"}})
# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return jsonify({"status": "API is running", "endpoints": ["/api/scrape"]})

@app.route('/api/scrape', methods=['POST'])
def scrape():
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        if not query:
            return jsonify({"error": "No search term provided"}), 400
        
        # Perform scraping (no caching)
        logging.debug(f"Scraping for query: {query}")
        results = scrape_medicines(query)
        
        logging.debug(f"Returning results: {results}")
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error in scrape: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)