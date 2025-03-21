from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from dotenv import load_dotenv, set_key, find_dotenv
from seleniumbase import Driver
from threading import Lock
import time
from flask_cors import CORS
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from models import db, TaskSchedule, ActivityLog
from scheduler import TaskScheduler
import atexit
from collections import deque
from flask_socketio import SocketIO, emit
from sqlalchemy import inspect
from sqlalchemy import text
import hashlib

# Load environment variables
dotenv_file = find_dotenv()
load_dotenv(dotenv_file)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD', 'password')  # This will now store the SHA-256 hash

# Site configuration
app.config['SITE_TITLE'] = os.getenv('SITE_TITLE', 'Zurg Control Panel')
app.config['SITE_LOGO_PATH'] = os.getenv('SITE_LOGO_PATH', 'https://share.woahlab.com/-nRaS9SX5KU')
app.config['SITE_FAVICON_PATH'] = os.getenv('SITE_FAVICON_PATH', '/static/img/favicon.ico')

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def load_env_schedules():
    """Load schedule configurations from .env file into the database"""
    print("Loading schedules from .env file...")
    
    # Find all schedule-related environment variables
    env_schedule_pattern = r'SCHEDULE_([A-Z_]+)_([A-Z_]+)'
    schedule_vars = {}
    
    # Group environment variables by schedule name
    for key, value in os.environ.items():
        match = re.match(env_schedule_pattern, key)
        if match:
            schedule_name = match.group(1).lower()
            attribute = match.group(2).lower()
            
            if schedule_name not in schedule_vars:
                schedule_vars[schedule_name] = {}
            
            schedule_vars[schedule_name][attribute] = value
    
    # Process each schedule configuration
    imported_count = 0
    with app.app_context():
        for name, attrs in schedule_vars.items():
            if 'cron' not in attrs or 'action' not in attrs:
                print(f"Skipping incomplete schedule {name}: missing required attributes")
                continue
            
            # Display name for the UI (convert snake_case to Title Case)
            display_name = f"{name.replace('_', ' ').title()} Schedule"
            
            # Determine if we should enable the schedule
            enabled = attrs.get('enabled', 'true').lower() == 'true'
            
            # Check if this schedule already exists in the database
            existing = TaskSchedule.query.filter_by(name=display_name).first()
            
            if existing:
                # Update existing schedule if env settings are different
                if (existing.cron != attrs['cron'] or 
                    existing.action != attrs['action'] or 
                    existing.enabled != enabled):
                    
                    existing.cron = attrs['cron']
                    existing.action = attrs['action']
                    existing.enabled = enabled
                    db.session.commit()
                    print(f"Updated existing schedule from .env: {name}")
                    imported_count += 1
            else:
                # Create new schedule
                schedule = TaskSchedule(
                    name=display_name,
                    cron=attrs['cron'],
                    action=attrs['action'],
                    enabled=enabled
                )
                db.session.add(schedule)
                db.session.commit()
                print(f"Created new schedule from .env: {name}")
                imported_count += 1
    
    return imported_count

def save_schedule_to_env(schedule):
    """Save a schedule to the .env file"""
    # Convert schedule name to uppercase snake case for .env format
    env_name = re.sub(r'[^a-zA-Z0-9]', '_', schedule.name.replace(' Schedule', '')).upper()
    
    # Set environment variables
    set_key(dotenv_file, f"SCHEDULE_{env_name}_ACTION", schedule.action)
    set_key(dotenv_file, f"SCHEDULE_{env_name}_CRON", schedule.cron)
    set_key(dotenv_file, f"SCHEDULE_{env_name}_ENABLED", str(schedule.enabled).lower())
    
    print(f"Saved schedule to .env file: {env_name}")
    return True

def delete_schedule_from_env(schedule):
    """Remove a schedule from the .env file"""
    # Get the current .env file content
    with open(dotenv_file, 'r') as file:
        lines = file.readlines()
    
    # Convert schedule name to uppercase snake case for .env format
    env_name = re.sub(r'[^a-zA-Z0-9]', '_', schedule.name.replace(' Schedule', '')).upper()
    prefix = f"SCHEDULE_{env_name}_"
    
    # Filter out the schedule's entries
    lines = [line for line in lines if not line.startswith(prefix)]
    
    # Write the updated content back
    with open(dotenv_file, 'w') as file:
        file.writelines(lines)
    
    print(f"Removed schedule from .env file: {env_name}")
    return True

def check_and_update_schema():
    """Check if the database schema is up to date and update it if necessary"""
    with app.app_context():
        # Check if last_run column exists in TaskSchedule
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('task_schedule')]
        
        if 'last_run' not in columns:
            print("Adding last_run column to TaskSchedule table")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE task_schedule ADD COLUMN last_run DATETIME'))
                conn.commit()
            print("Database schema updated")

# Create tables
with app.app_context():
    db.create_all()
    
    # Check and update schema if necessary
    check_and_update_schema()
    
    # Load schedules from .env file
    imported_count = load_env_schedules()
    if imported_count > 0:
        print(f"Imported {imported_count} schedules from .env file")

# Initialize scheduler
scheduler = TaskScheduler(app)

# Global browser instance and lock
browser = None
browser_lock = Lock()

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Activity log storage
activity_logs = deque(maxlen=100)  # Store last 100 activities

def initialize_browser():
    global browser
    try:
        print("Initializing browser...")
        browser = Driver(
            browser="chrome",
            headless=True,
            uc=True,  # Undetected Chrome mode
            agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            cap_string='{"goog:chromeOptions": {"args": ["--no-sandbox", "--headless", "--disable-dev-shm-usage", "--disable-gpu"]}}'
        )
        browser.get("http://192.168.0.247:9999/")
        
        # Wait for the page to load and specifically for the worker information
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Get page source and check for worker info
                page_text = browser.get_page_source()
                # Look for pattern: number running / number free / number total
                pattern = r'\d+\s*running\s*/\s*\d+\s*free\s*/\s*\d+\s*total'
                if re.search(pattern, page_text):
                    print("Worker information found in page")
                    break
                print(f"Waiting for worker information (attempt {retry_count + 1}/{max_retries})")
                time.sleep(2)
                retry_count += 1
            except Exception as e:
                print(f"Error checking for worker info: {str(e)}")
                time.sleep(2)
                retry_count += 1
        
        print("Browser initialized and waiting at http://192.168.0.247:9999/")
    except Exception as e:
        print(f"Error initializing browser: {str(e)}")
        if browser:
            try:
                browser.quit()
            except:
                pass

def run_selenium_command(action):
    global browser
    with browser_lock:
        try:
            print(f"Executing action: {action}")
            # Refresh the page to ensure we're in a good state
            browser.get("http://192.168.0.247:9999/")
            time.sleep(2)  # Wait for page to load
            
            if action == "remount_downloads":
                browser.click('input[value="Remount downloads"]')
            elif action == "reboot_repair":
                browser.click('input[value="Reboot repair worker"]')
            elif action == "reboot_refresh":
                browser.click('input[value="Reboot refresh worker"]')
            elif action == "reboot_worker":
                browser.click('input[value="Reboot worker pool"]')
            time.sleep(2)  # Wait for action to complete
            browser.get("http://192.168.0.247:9999/")  # Return to main page
            return True
        except Exception as e:
            print(f"Error during action: {str(e)}")
            # Try to reinitialize browser if something went wrong
            try:
                browser.quit()
            except:
                pass
            initialize_browser()
            return False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    if username == ADMIN_USERNAME:
        return User(username)
    return None

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

def hash_password(password):
    """Convert a plain text password to SHA-256 hash"""
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hash the input password and compare with stored hash
        if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD_HASH:
            user = User(username)
            login_user(user)
            log_activity(f'User {username} logged in successfully', 'info')
            return redirect(url_for('dashboard'))
        else:
            log_activity(f'Failed login attempt for user {username}', 'warning')
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.id
    logout_user()
    log_activity(f'User {username} logged out', 'info')
    return redirect(url_for('login'))

def log_activity(message, activity_type='info'):
    """Log an activity and broadcast it to connected clients"""
    try:
        # Create new activity log entry
        activity = ActivityLog(
            message=message,
            type=activity_type,
            timestamp=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()

        # Broadcast to connected clients
        socketio.emit('activity', activity.to_dict())
    except Exception as e:
        print(f"Error logging activity: {str(e)}")

@app.route('/trigger/<action>', methods=['POST'])
@login_required
def trigger_action(action):
    if action in ['remount_downloads', 'reboot_repair', 'reboot_refresh', 'reboot_worker']:
        print(f"Triggering action: {action}")
        success = run_selenium_command(action)
        print(f"Action completed with success: {success}")
        
        # Log the activity with a more descriptive message
        if success:
            action_messages = {
                'remount_downloads': 'Remounted downloads directory',
                'reboot_repair': 'Rebooted repair worker',
                'reboot_refresh': 'Rebooted refresh worker',
                'reboot_worker': 'Rebooted worker pool'
            }
            log_activity(action_messages[action], 'success')
        else:
            log_activity(f"Failed to {action.replace('_', ' ')}", 'error')
            
        return {'success': success}
    return {'success': False, 'error': 'Invalid action'}, 400

@app.route('/status')
@login_required
def get_status():
    global browser
    with browser_lock:
        try:
            # Navigate to main page
            browser.get(os.getenv('ZURG_HOST', 'http://192.168.0.247:9999/'))
            time.sleep(2)  # Wait for page load
            
            # Get the page content
            page_text = browser.get_page_source()
            print("\n=== Parsing Zurg Homepage Data ===")
            
            # Use BeautifulSoup to parse the HTML
            soup = BeautifulSoup(page_text, 'html.parser')
            table = soup.find('table')
            data = {}
            
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        key = cols[0].get_text(strip=True)
                        value = cols[1].get_text(strip=True)
                        data[key] = value
            
            # Extract information using the parsed data
            version = data.get('Version', 'Unknown')
            print(f"Version: {version}")
            
            memory_allocation = re.search(r'(\d+)\s*MB', data.get('Memory Allocation', '0 MB'))
            print(f"Memory Allocation: {memory_allocation.group(1) if memory_allocation else 'Not found'} MB")
            
            system_memory = re.search(r'(\d+)\s*MB', data.get('System Memory', '0 MB'))
            print(f"System Memory: {system_memory.group(1) if system_memory else 'Not found'} MB")
            
            built_at = data.get('Built At', 'Unknown')
            print(f"Built At: {built_at}")
            
            git_commit = data.get('Git Commit', 'Unknown')
            print(f"Git Commit: {git_commit}")
            
            # Extract worker stats from the table
            workers_text = data.get('Workers', '')
            workers_match = re.search(r'(\d+)\s*running\s*/\s*(\d+)\s*free\s*/\s*(\d+)\s*total', workers_text)
            if workers_match:
                print(f"Workers: {workers_match.group(1)} running / {workers_match.group(2)} free / {workers_match.group(3)} total")
            else:
                print("Workers: Not found")
            
            # Extract premium status
            premium_status = data.get('Type', 'Unknown')
            print(f"Premium Status: {premium_status}")
            
            # Extract points
            points = data.get('Points', '0')
            print(f"Points: {points}")
            
            # Calculate memory usage percentage
            memory_usage = None
            if memory_allocation and system_memory:
                try:
                    memory_alloc = int(memory_allocation.group(1))
                    system_mem = int(system_memory.group(1))
                    memory_usage = (memory_alloc / system_mem) * 100
                    print(f"Memory usage: {memory_usage:.1f}%")
                except Exception as e:
                    print(f"Error calculating memory usage: {str(e)}")
            
            # Extract premium days and expiry
            premium_days = data.get('Premium', '0')
            if ' days' in premium_days:
                premium_days = premium_days.replace(' days', '')
            
            # Extract RD info
            rd_expiry = data.get('RD Expiry', 'Unknown')
            rd_time_remaining = data.get('RD Time Remaining', 'Unknown')
            
            # Format the response to match exactly what the frontend JavaScript expects
            return {
                'workers': {
                    'running': int(workers_match.group(1)) if workers_match else 0,
                    'free': int(workers_match.group(2)) if workers_match else 0,
                    'total': int(workers_match.group(3)) if workers_match else 0
                },
                'system': {
                    'memory_usage': f"{memory_usage:.1f}" if memory_usage is not None else '0',
                    'memory_allocation': f"{memory_allocation.group(1)}" if memory_allocation else '0',
                    'system_memory': f"{system_memory.group(1)}" if system_memory else '0'
                },
                'premium': {
                    'days_remaining': premium_days if premium_days != '0' else '-',
                    'expiry_date': data.get('Expiration', '-'),
                    'rd_expires': rd_expiry if rd_expiry != 'Unknown' else '-',
                    'rd_time_remaining': rd_time_remaining if rd_time_remaining != 'Unknown' else '-'
                },
                'points': points if points != '0' else '-',
                'version': {
                    'number': version if version != 'Unknown' else '-',
                    'built_at': built_at if built_at != 'Unknown' else '-',
                    'git_commit': git_commit[:7] if git_commit != 'Unknown' else '-'
                }
            }
            
        except Exception as e:
            print(f"Error getting status: {str(e)}")
            try:
                browser.quit()
            except:
                pass
            initialize_browser()
            return {
                'error': str(e),
                'workers': {
                    'running': 0,
                    'free': 0,
                    'total': 0
                }
            }

@app.route('/worker_stats')
@login_required
def get_worker_stats():
    global browser
    with browser_lock:
        try:
            # Refresh the page to get latest stats
            browser.get("http://192.168.0.247:9999/")
            time.sleep(2)  # Wait for page load
            
            # Get the page content
            page_text = browser.get_page_source()
            
            # Look for the pattern: number running / number free / number total
            pattern = r'(\d+)\s*running\s*/\s*(\d+)\s*free\s*/\s*(\d+)\s*total'
            match = re.search(pattern, page_text)
            
            if match:
                running = int(match.group(1))
                free = int(match.group(2))
                total = int(match.group(3))
                
                print(f"Found worker stats: {running} running, {free} free, {total} total")
                return {
                    'success': True,
                    'workers': {
                        'running': running,
                        'free': free,
                        'total': total
                    }
                }
            else:
                print("Workers information not found in page source")
                print("Page content:", page_text[:500])  # Print first 500 chars for debugging
                # Try to reinitialize browser
                try:
                    browser.quit()
                except:
                    pass
                initialize_browser()
                return {
                    'success': False,
                    'error': 'Workers information not found'
                }
                
        except Exception as e:
            print(f"Error getting worker stats: {str(e)}")
            # Try to reinitialize browser
            try:
                browser.quit()
            except:
                pass
            initialize_browser()
            return {
                'success': False,
                'error': str(e)
            }

@app.route('/trigger/jellyfin_scan', methods=['POST'])
@login_required
def trigger_jellyfin_scan():
    """
    Web route handler for triggering Jellyfin scan - requires request context
    """
    result, status_code = jellyfin_scan_library()
    
    if result['success']:
        return result, 200
    else:
        return result, status_code

def jellyfin_scan_library():
    """
    Context-free version of Jellyfin scan that can be used by scheduler
    Returns (result_dict, status_code)
    """
    try:
        # Add debug logging
        print("Starting Jellyfin library scan...")
        api_key = os.getenv('JELLYFIN_TOKEN')
        if not api_key:
            print("No Jellyfin token found")
            log_activity_direct('Failed to start Jellyfin library scan: No token configured', 'error')
            return {'success': False, 'error': 'No Jellyfin token configured'}, 400

        print(f"Using Jellyfin token: {api_key[:5]}...")
        
        # Get Jellyfin host from environment
        jellyfin_host = os.getenv('JELLYFIN_HOST', 'http://192.168.0.247:8096/')
        
        # Make the API request
        response = requests.post(
            f"{jellyfin_host.rstrip('/')}/Library/Refresh",
            headers={'X-Emby-Token': api_key},
            timeout=10
        )
        
        print(f"Jellyfin API response status: {response.status_code}")
        if response.status_code == 204:
            log_activity_direct('Started Jellyfin library scan', 'success')
            return {'success': True}, 200
        else:
            error_msg = f'Jellyfin API returned status code: {response.status_code}'
            try:
                error_msg += f' - {response.json().get("error", "")}'
            except:
                pass
            print(f"Error: {error_msg}")
            log_activity_direct(f'Failed to start Jellyfin library scan: {error_msg}', 'error')
            return {'success': False, 'error': error_msg}, 400
            
    except requests.exceptions.Timeout:
        error_msg = "Jellyfin API request timed out"
        print(f"Error: {error_msg}")
        log_activity_direct(f'Failed to start Jellyfin library scan: {error_msg}', 'error')
        return {'success': False, 'error': error_msg}, 500
    except requests.exceptions.ConnectionError:
        error_msg = "Could not connect to Jellyfin server"
        print(f"Error: {error_msg}")
        log_activity_direct(f'Failed to start Jellyfin library scan: {error_msg}', 'error')
        return {'success': False, 'error': error_msg}, 500
    except Exception as e:
        error_msg = str(e)
        print(f"Unexpected error: {error_msg}")
        log_activity_direct(f'Failed to start Jellyfin library scan: {error_msg}', 'error')
        return {'success': False, 'error': error_msg}, 500

def log_activity_direct(message, activity_type='info'):
    """
    Direct database version of log_activity that doesn't use socketio
    This version can be used outside of request context (e.g., in scheduled tasks)
    """
    try:
        # Create new activity log entry
        activity = ActivityLog(
            message=message,
            type=activity_type,
            timestamp=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
        print(f"Activity logged: {message} ({activity_type})")
    except Exception as e:
        print(f"Error logging activity: {str(e)}")

def parse_logs(response_text):
    """Helper function to parse logs from response text"""
    logs = []
    log_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\t(\w+)\t(\w+)\t(.+)'
    
    # Split into lines and parse each log entry
    for line in response_text.strip().split('\n'):
        match = re.match(log_pattern, line)
        if match:
            timestamp, level, component, message = match.groups()
            # Convert timestamp to datetime for sorting and formatting
            dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
            formatted_timestamp = dt.strftime('%d/%m/%Y %H:%M:%S')
            logs.append({
                'timestamp': formatted_timestamp,
                'raw_timestamp': timestamp,
                'datetime': dt,
                'level': level,
                'component': component,
                'message': message
            })
    return logs

@app.route('/logs')
@login_required
def view_logs():
    try:
        # Get pagination and filter parameters from request
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)  # Default to 50 items per page
        level_filter = request.args.get('level', 'all')
        component_filter = request.args.get('component', 'all')
        time_range = request.args.get('time_range', 'all')
        
        # Fetch logs from the logs URL
        response = requests.get('http://192.168.0.247:9999/logs/')
        if not response.ok:
            return render_template('logs.html', logs=[], error="Failed to fetch logs")
        
        # Parse and sort logs
        logs = parse_logs(response.text)
        
        # Apply filters if they're set
        if level_filter != 'all':
            logs = [log for log in logs if log['level'] == level_filter]
        if component_filter != 'all':
            logs = [log for log in logs if log['component'].lower() == component_filter.lower()]
            
        # Apply time range filter
        if time_range != 'all':
            now = datetime.utcnow()
            if time_range == 'custom':
                try:
                    time_from = request.args.get('time_from')
                    time_to = request.args.get('time_to')
                    if time_from:
                        time_from = datetime.fromisoformat(time_from.replace('Z', '+00:00'))
                        logs = [log for log in logs if log['datetime'] >= time_from]
                    if time_to:
                        time_to = datetime.fromisoformat(time_to.replace('Z', '+00:00'))
                        logs = [log for log in logs if log['datetime'] <= time_to]
                except ValueError:
                    pass  # Invalid date format, ignore the filter
            else:
                # Calculate time delta based on range
                delta = {
                    '1h': timedelta(hours=1),
                    '6h': timedelta(hours=6),
                    '24h': timedelta(hours=24),
                    '7d': timedelta(days=7),
                    '30d': timedelta(days=30)
                }.get(time_range)
                
                if delta:
                    cutoff_time = now - delta
                    logs = [log for log in logs if log['datetime'] >= cutoff_time]
        
        # Sort logs in reverse chronological order
        logs.sort(key=lambda x: x['datetime'], reverse=True)
        
        # Calculate pagination values
        total_logs = len(logs)
        total_pages = max(1, (total_logs + per_page - 1) // per_page)  # Ceiling division, minimum 1 page
        page = min(max(1, page), total_pages)  # Ensure page is within valid range
        
        # Get the logs for the current page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_logs = logs[start_idx:end_idx]
        
        return render_template('logs.html', 
                             logs=paginated_logs,
                             current_page=page,
                             total_pages=total_pages,
                             per_page=per_page,
                             total_logs=total_logs,
                             min=min,
                             max=max)
    except Exception as e:
        return render_template('logs.html', logs=[], error=str(e), min=min, max=max)

@app.route('/recent_logs')
@login_required
def get_recent_logs():
    try:
        # Fetch logs from Zurg's logs URL
        response = requests.get('http://192.168.0.247:9999/logs/')
        if not response.ok:
            return {'success': False, 'error': "Failed to fetch logs"}, 500
        
        # Parse and sort logs using the shared function
        logs = parse_logs(response.text)
        logs.sort(key=lambda x: x['raw_timestamp'], reverse=True)
        recent_logs = logs[:5]  # Get 5 most recent logs
        
        return {'success': True, 'logs': recent_logs}
    except Exception as e:
        print(f"Error getting recent logs: {str(e)}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/activity_logs')
@login_required
def get_activity_logs():
    try:
        # Get the 50 most recent activity logs from our control panel
        logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
        return {
            'success': True,
            'logs': [log.to_dict() for log in logs]
        }
    except Exception as e:
        print(f"Error getting activity logs: {str(e)}")
        return {'success': False, 'error': str(e)}, 500

@app.route('/schedules')
@login_required
def view_schedules():
    return render_template('schedules.html')

@app.route('/api/schedules')
@login_required
def get_schedules():
    schedules = TaskSchedule.query.all()
    return jsonify([schedule.to_dict() for schedule in schedules])

@app.route('/api/schedules/save', methods=['POST'])
@login_required
def save_schedule():
    try:
        data = request.json
        print(f"Received schedule data: {data}")
        schedule_id = data.get('id')
        
        # Convert frontend data to model fields
        schedule_data = {
            'name': f"{data['task_name'].replace('_', ' ').title()} Schedule",  # Create a readable name
            'action': data['task_name'],  # The actual task to perform
            'enabled': data['enabled']
        }
        
        # Handle cron expression based on schedule type
        if data['type'] == 'cron':
            schedule_data['cron'] = data['cron']
            print(f"Using direct cron expression: {data['cron']}")
        else:  # simple schedule
            # Convert simple schedule to cron expression
            if data['frequency'] == 'hourly':
                time = data.get('time', '00:00')
                minutes = time.split(':')[1] if time else '0'
                schedule_data['cron'] = f"{minutes} * * * *"
            elif data['frequency'] == 'daily':
                if 'time' not in data or not data['time']:
                    raise ValueError("Time is required for daily schedule")
                time_parts = data['time'].split(':')
                schedule_data['cron'] = f"{time_parts[1]} {time_parts[0]} * * *"
            elif data['frequency'] == 'weekly':
                if 'time' not in data or not data['time']:
                    raise ValueError("Time is required for weekly schedule")
                if 'days' not in data or not data['days']:
                    raise ValueError("At least one day must be selected for weekly schedule")
                time_parts = data['time'].split(':')
                days = ','.join(str(d) for d in data['days'])
                schedule_data['cron'] = f"{time_parts[1]} {time_parts[0]} * * {days}"
            elif data['frequency'] == 'custom':
                if 'hours' not in data:
                    raise ValueError("Hours interval is required for custom schedule")
                schedule_data['cron'] = f"0 */{data['hours']} * * *"
            else:
                raise ValueError(f"Unknown frequency: {data['frequency']}")
            print(f"Generated cron expression: {schedule_data['cron']}")

        if schedule_id:  # Update existing schedule
            schedule = TaskSchedule.query.get(schedule_id)
            if not schedule:
                return {'success': False, 'error': 'Schedule not found'}, 404
                
            old_name = schedule.name
            for key, value in schedule_data.items():
                setattr(schedule, key, value)
            
            db.session.commit()
            print(f"Updated schedule in database: {schedule.id}")
            
            # Update schedule in the .env file
            save_schedule_to_env(schedule)
            
            scheduler.update_job(schedule)
            print(f"Updated schedule in scheduler: {schedule.id}")
            
            log_activity(f'Updated schedule: {old_name}', 'info')
            return {'success': True, 'message': 'Schedule updated successfully'}
            
        else:  # Create new schedule
            schedule = TaskSchedule(**schedule_data)
            
            db.session.add(schedule)
            db.session.commit()
            print(f"Created new schedule in database: {schedule.id}")
            
            # Save new schedule to the .env file
            save_schedule_to_env(schedule)
            
            if schedule.enabled:
                scheduler.add_job(schedule)
                print(f"Added new schedule to scheduler: {schedule.id}")
                
            log_activity(f'Created new schedule: {schedule.name}', 'info')
            return {'success': True, 'message': 'Schedule created successfully'}
            
    except Exception as e:
        error_message = str(e)
        print(f"Error saving schedule: {error_message}")
        log_activity(f'Failed to save schedule: {error_message}', 'error')
        return {'success': False, 'error': error_message}, 500

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required
def delete_schedule(schedule_id):
    try:
        schedule = TaskSchedule.query.get_or_404(schedule_id)
        name = schedule.name
        
        # Remove from the scheduler
        scheduler.remove_schedule(schedule)
        
        # Remove from the .env file
        delete_schedule_from_env(schedule)
        
        # Remove from the database
        db.session.delete(schedule)
        db.session.commit()
        
        log_activity(f'Deleted schedule: {name}', 'info')
        return jsonify({'success': True})
    except Exception as e:
        log_activity(f'Failed to delete schedule: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/activities')
@login_required
def get_activities():
    """Get recent activities"""
    return jsonify({
        'activities': list(activity_logs)
    })

@app.route('/api/schedules/import_from_env', methods=['POST'])
@login_required
def import_schedules_from_env():
    """Manually trigger import of schedules from .env file"""
    try:
        # Reload environment variables from .env file
        dotenv_file = find_dotenv()
        load_dotenv(dotenv_file, override=True)
        
        count = load_env_schedules()
        
        # Reload all enabled schedules in the scheduler
        scheduler.reload_schedules()
        
        message = f"Successfully imported {count} schedules from .env file"
        log_activity(message, 'success')
        return jsonify({'success': True, 'message': message, 'count': count})
    except Exception as e:
        error_message = f"Failed to import schedules: {str(e)}"
        log_activity(error_message, 'error')
        return jsonify({'success': False, 'error': error_message}), 500

@app.route('/api/schedules/export_to_env', methods=['POST'])
@login_required
def export_schedules_to_env():
    """Export all schedules in the database to .env file"""
    try:
        schedules = TaskSchedule.query.all()
        count = 0
        
        for schedule in schedules:
            save_schedule_to_env(schedule)
            count += 1
        
        message = f"Successfully exported {count} schedules to .env file"
        log_activity(message, 'success')
        return jsonify({'success': True, 'message': message, 'count': count})
    except Exception as e:
        error_message = f"Failed to export schedules: {str(e)}"
        log_activity(error_message, 'error')
        return jsonify({'success': False, 'error': error_message}), 500

# Initialize browser when the application starts
initialize_browser()

# Cleanup when the application exits
@atexit.register
def cleanup():
    global browser
    if browser:
        try:
            browser.quit()
        except:
            pass
    scheduler.shutdown()

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

# Add static file handling
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    initialize_browser()
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, debug=True, host='0.0.0.0', port=port) 