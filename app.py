from flask import Flask, render_template, jsonify, request, session, send_from_directory
import logging
import os
import psutil  
import time
from flask_session import Session
from cachelib.file import FileSystemCache
from datetime import datetime
import requests
import re


app = Flask(__name__)
server_start_time = time.time()

# Flask Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "M@s1471236m@S")  # Change this in production
app.config["SESSION_TYPE"] = "cachelib"
app.config["SESSION_CACHELIB"] = FileSystemCache("./flask_session")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_KEY_PREFIX"] = "session:"

# Initialize session
Session(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log")]
)
logger = logging.getLogger(__name__)

# Global user activity log to store request information
user_activity_log = []

def sanitize_input(user_input):
    """Sanitize input to prevent HTML injection."""
    return re.sub(r'<.*?>', '', user_input)

# Serve static files efficiently with caching
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename, cache_timeout=31536000)

@app.route("/")
def home():
    return render_template("index.html")

# Middleware to track user activity before handling requests
@app.before_request
def track_user_activity():
    # Ignore tracking for static files (CSS, JS, images, etc.)
    if request.endpoint not in ["static"]:
        request.start_time = time.time()  # Store request start time
        if "start_time" not in session:
            session["start_time"] = request.start_time  # Store session start time

# Middleware to log response time and status codes
@app.after_request
def log_response_info(response):
    if not any(excluded in request.url for excluded in ["/clear-session", "/clear-log", "/static/"]):
        if hasattr(request, "start_time"):  # Ensure request.start_time exists
            response_time = (time.time() - request.start_time) * 1000  # Convert to milliseconds
            user_activity_log.append({
                "page": request.path,
                "timestamp": time.time(),
                "response_code": response.status_code,
                "response_time": f"{response_time:.2f} ms"
            })
    return response

# Application performance monitoring
@app.route("/app-performance")
def app_performance():
    process = psutil.Process(os.getpid())
    app_memory = process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
    uptime = time.time() - server_start_time

    total_response_time = sum(
        float(entry["response_time"].replace(" ms", "")) for entry in user_activity_log
    ) if user_activity_log else 0

    avg_response_time = total_response_time / len(user_activity_log) if user_activity_log else 0
    cache_hits = sum(1 for entry in user_activity_log if entry.get("response_code") == 304)

    metrics = {
        "App Memory Usage": f"{app_memory:.2f} MB",
        "Running Time": f"{uptime:.2f} seconds",
        "Active Sessions": len(session.items()),  # Count active user sessions
        "Avg Response Time": f"{avg_response_time:.2f} ms",  # Show average response time
        "Cache Hits": cache_hits
    }
    return render_template("app_performance.html", metrics=metrics)

# Clear activity log endpoint
@app.route("/clear-log", methods=["POST"])
def clear_user_activity():
    global user_activity_log
    user_activity_log = []
    return jsonify({"success": True})

# Display user activity log
@app.route("/user-activity")
def user_activity():
    formatted_log = [
        {
            "page": entry["page"].replace("/", "").replace("-", " ").title() or "Home Page",
            "timestamp": datetime.fromtimestamp(entry["timestamp"]).strftime('%d-%m %H:%M'),
            "response_code": entry["response_code"],
            "response_time": entry["response_time"]
        }
        for entry in user_activity_log
    ]
    return render_template("user_activity.html", log=formatted_log)

# HTTP request analysis endpoint
@app.route("/request-analysis", methods=["GET", "POST"])
def request_analysis():
    if request.method == "POST":
        try:
            user_input = sanitize_input(request.form.get("request_input", "").strip())
            method = request.form.get("method", "GET").upper()
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0]

            if not user_input:
                return jsonify({"error": "No request input provided"}), 400

            if user_input.startswith("http://") or user_input.startswith("https://"):
                headers = {"User-Agent": "Flask-App/1.0"}
                timeout = 5

                if method == "GET":
                    response = requests.get(user_input, headers=headers, timeout=timeout)
                elif method == "POST":
                    response = requests.post(user_input, headers=headers, timeout=timeout, data={"test": "data"})
                else:
                    return jsonify({"error": f"Unsupported method: {method}"}), 400

                response_data = {
                    "method": method,
                    "ip": client_ip,
                    "request_data": user_input,
                    "status_code": response.status_code,
                    "response": response.text[:500],
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                return jsonify(response_data), response.status_code

            else:
                return jsonify({
                    "error": "Please provide a valid URL starting with http:// or https://",
                    "method": method,
                    "ip": client_ip,
                    "request_data": user_input,
                    "status_code": 400,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }), 400

        except requests.exceptions.RequestException as e:
            return jsonify({
                "error": f"Request failed: {str(e)}",
                "method": method,
                "ip": client_ip,
                "request_data": user_input,
                "status_code": 502 if "timeout" in str(e).lower() else 400,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 502 if "timeout" in str(e).lower() else 400

        except Exception as e:
            return jsonify({
                "error": f"Unexpected error: {str(e)}",
                "method": method,
                "ip": client_ip,
                "request_data": user_input,
                "status_code": 500,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 500

    return render_template("request_analysis.html")

# Handle 404 errors
@app.errorhandler(404)
def page_not_found(error):
    logger.warning(f"Page not found: {request.url}")
    return render_template("404.html"), 404

# Handle unexpected errors
@app.errorhandler(Exception)
def handle_exception(error):
    logger.error(f"Unhandled error: {error}")
    return render_template("error.html", error="Internal server error"), 500

# Clear session endpoint
@app.route('/clear-session', methods=["POST"])
def clear_session():
    session.clear() 
    return jsonify({"success": True}), 200

# Run Flask app
if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=5050, debug=debug_mode, threaded=True)
