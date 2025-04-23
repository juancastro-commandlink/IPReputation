from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_cors import CORS
from multiprocessing import Process, Manager, freeze_support
from models import db, User, IPRequest, DriverResponse, DriverConfig, IPAccessLog
from drivers import load_drivers, run_driver
from utils.auth import md5_hash, check_login
from utils.driver_config import load_config, get_driver_config, update_driver_config
from utils.log_helper import get_logger


import time
import os

manager = None
driver_status = None
drivers = {}
logger = get_logger()

def create_api_app():
    global manager, driver_status, drivers
    logger.info("✅ Logging is active and writing to api.log")

    app = Flask("api_app")
    CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5001, http://localhost:5001"])
    app.secret_key = 'super-secret-key'
    app.config['SESSION_COOKIE_NAME'] = 'api-session'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    db.init_app(app)

    manager = Manager()
    driver_status = manager.dict()
    drivers = load_drivers()

    with app.app_context():
        db.create_all()
        if driver_status is not None:
            configs = load_config()
            for name in drivers:
                driver_status[name] = configs.get(name, {}).get('enabled', True)


    @app.after_request
    def apply_cors(response):
        origin = request.headers.get("Origin")
        if origin := request.headers.get("Origin"):
            if origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        return response


    @app.route('/api/admin/driver-configs', methods=['GET'])
    @app.route('/api/admin/driver-configs/<name>', methods=['GET', 'POST'])
    def driver_config(name=None):
        if request.method == 'GET':
            if name:
                return jsonify(get_driver_config(name))
            return jsonify(load_config())

        # POST update to specific provider
        if not name:
            return jsonify({"error": "Provider name required"}), 400
        data = request.get_json()
        update_driver_config(name, data)
        return jsonify({"status": "updated"})

    @app.route('/api/ip/<ip>')
    def ip_lookup(ip):
        logger.warning(f"[CALL] Greynoise.fetch_ip was called for {ip}")
        record = IPRequest.query.filter_by(ip=ip).first()

        responses = {}
        print("Loaded drivers:", drivers.keys())
        for name, driver in drivers.items():
            if driver_status.get(name):
                try:
                    data = run_driver(driver, ip)
                    if data.get("status") == "private":
                        return jsonify(data)
                    else:
                        responses[name] = data
                except Exception as e:
                    responses[name] = {"error": str(e)}

        return jsonify(responses)

    @app.route('/api/ip/<ip>', methods=['DELETE'])
    def delete_ip_cache(ip):
        deleted = DriverResponse.query.filter_by(ip=ip).delete()
        IPRequest.query.filter_by(ip=ip).delete()
        db.session.commit()
        return jsonify({"deleted_records": deleted, "ip": ip})

    @app.route('/api/admin/metrics')
    def metrics():
        driver_counts = {name: DriverResponse.query.filter_by(driver=name).count() for name in drivers}
        driver_counts["_total_ips_queried"] = IPRequest.query.count()
        return jsonify(driver_counts)

    @app.route('/api/admin/drivers')
    def list_drivers():
        return jsonify({name: driver_status.get(name, False) for name in drivers})

    @app.route('/api/admin/cache-stats')
    def cache_stats():
        cached_hits = IPAccessLog.query.filter_by(source='cache').count()
        missed = IPAccessLog.query.filter_by(source='driver').count()

        return jsonify({
            "cached": cached_hits,
            "missed": missed
        })

    @app.route('/api/admin/cached-ips')
    def cached_ips():
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("limit", 10))
        search = request.args.get("search", "")

        query = IPRequest.query
        if search:
            query = query.filter(IPRequest.ip.contains(search))

        total = query.count()
        results = query.order_by(IPRequest.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()

        data = [{
            "ip": r.ip,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r.timestamp)),
            "drivers": DriverResponse.query.filter_by(ip=r.ip).count()
        } for r in results]

        return jsonify({ "results": data, "total": total })

    @app.route('/api/admin/drivers/<name>/toggle', methods=['POST'])
    def toggle_driver(name):
        driver_status[name] = not driver_status.get(name, True)
        return jsonify({name: driver_status[name]})
    return app



def create_ui_app():
    app = Flask("ui_app")
    app.secret_key = 'super-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    db.init_app(app)

    with app.app_context():
        db.create_all()
        if not User.query.first():
            default_user = User(username='admin', password=md5_hash('admin'))
            db.session.add(default_user)
            db.session.commit()

    @app.route('/', endpoint='index')
    def index():
        if 'user' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'], endpoint='login')
    def login():
        if request.method == 'POST':
            user = User.query.filter_by(username=request.form['username']).first()
            if user and user.password == md5_hash(request.form['password']):
                session['user'] = user.username
                session['is_admin'] = user.is_admin
                return redirect(url_for('dashboard'))
        return render_template('login.html')


    @app.route('/admin', endpoint='admin')
    def admin():
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('admin.html')



    @app.route('/dashboard', endpoint='dashboard')
    def dashboard():
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('dashboard.html')

    @app.route('/logout', endpoint='logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    return app

def run_api():
    app = create_api_app()
    app.run(port=5000, debug=True, use_reloader=False)

def run_ui():
    app = create_ui_app()
    app.run(port=5001, debug=True, use_reloader=False)

if __name__ == '__main__':
    freeze_support()
    api_process = Process(target=run_api)
    ui_process = Process(target=run_ui)
    api_process.start()
    ui_process.start()
    api_process.join()
    ui_process.join()

# Note:
# - Driver modules are in the `drivers/` directory
# - Templates `login.html`, `dashboard.html` must exist
# - Models and utility functions are separated for modularity
# - LDAP integration can be added in `check_login()` in utils.py
