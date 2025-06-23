from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import pickle
import threading
import time
from datetime import datetime
from automation_script import run_automation, start_manual_login, save_cookies_and_run, running_tasks
import json

app = Flask(__name__)
CORS(app)

# Ensure directories exist
os.makedirs('cookies', exist_ok=True)
os.makedirs('logs', exist_ok=True)

@app.route('/api/run', methods=['POST'])
def run_automation_endpoint():
    try:
        data = request.json
        start_row = int(data['start_row'])
        end_row = int(data['end_row'])
        cookie_name = data['cookie_name']
        
        cookie_path = f"cookies/{cookie_name}.pkl"
        
        # Check if cookie exists
        if os.path.exists(cookie_path):
            # Run automation in background thread
            task_id = f"{cookie_name}_{start_row}_{end_row}_{int(time.time())}"
            
            def run_task():
                try:
                    running_tasks[task_id] = {
                        'status': 'initializing',
                        'start_time': datetime.now().isoformat(),
                        'progress': 0,
                        'current_member': None,
                        'current_family': None,
                        'console_logs': ['🚀 System initialized', '🔐 Loading session cookies...']
                    }
                    
                    # Update status to running
                    running_tasks[task_id]['status'] = 'running'
                    running_tasks[task_id]['progress'] = 5
                    running_tasks[task_id]['console_logs'].append('⚡ Automation sequence started')
                    
                    result = run_automation(cookie_name, start_row, end_row, task_id)
                    
                    running_tasks[task_id]['status'] = 'completed'
                    running_tasks[task_id]['end_time'] = datetime.now().isoformat()
                    running_tasks[task_id]['result'] = result
                    running_tasks[task_id]['progress'] = 100
                    running_tasks[task_id]['console_logs'].append('🎉 Automation completed successfully!')
                    running_tasks[task_id]['console_logs'].append(f'📊 Total processed: {result["total_processed"]}')
                    running_tasks[task_id]['console_logs'].append(f'✅ Successful: {result["success_count"]}')
                    running_tasks[task_id]['console_logs'].append(f'⚠️ Failed: {result["fail_count"]}')
                    
                except Exception as e:
                    running_tasks[task_id]['status'] = 'failed'
                    running_tasks[task_id]['end_time'] = datetime.now().isoformat()
                    running_tasks[task_id]['error'] = str(e)
                    running_tasks[task_id]['progress'] = 0
                    running_tasks[task_id]['console_logs'].append(f'❌ Error: {str(e)}')
            
            thread = threading.Thread(target=run_task)
            thread.start()
            
            return jsonify({
                'status': 'started',
                'task_id': task_id,
                'message': 'Automation started successfully'
            })
        else:
            return jsonify({
                'status': 'login_required',
                'message': 'Session not found. Manual authentication required.',
                'login_url': f'/api/login?cookie_name={cookie_name}&start_row={start_row}&end_row={end_row}'
            })
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/login')
def login_page():
    cookie_name = request.args.get('cookie_name')
    start_row = request.args.get('start_row')
    end_row = request.args.get('end_row')
    
    try:
        start_manual_login(cookie_name)
        return jsonify({
            'status': 'browser_opened',
            'message': 'Browser opened for manual authentication. Please login and then continue.',
            'continue_url': f'/api/save_cookies?cookie_name={cookie_name}&start_row={start_row}&end_row={end_row}'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/save_cookies', methods=['POST'])
def save_cookies():
    try:
        data = request.json
        cookie_name = data['cookie_name']
        start_row = int(data['start_row'])
        end_row = int(data['end_row'])
        
        task_id = f"{cookie_name}_{start_row}_{end_row}_{int(time.time())}"
        
        def run_task():
            try:
                running_tasks[task_id] = {
                    'status': 'saving_cookies',
                    'start_time': datetime.now().isoformat(),
                    'progress': 5,
                    'console_logs': ['💾 Saving authentication session...']
                }
                
                result = save_cookies_and_run(cookie_name, start_row, end_row, task_id)
                
                running_tasks[task_id]['status'] = 'completed'
                running_tasks[task_id]['end_time'] = datetime.now().isoformat()
                running_tasks[task_id]['result'] = result
                running_tasks[task_id]['progress'] = 100
                running_tasks[task_id]['console_logs'].append('✅ Session saved successfully')
                running_tasks[task_id]['console_logs'].append('🎉 Automation completed')
                running_tasks[task_id]['console_logs'].append(f'📊 Total processed: {result["total_processed"]}')
                running_tasks[task_id]['console_logs'].append(f'✅ Successful: {result["success_count"]}')
                running_tasks[task_id]['console_logs'].append(f'⚠️ Failed: {result["fail_count"]}')
                
            except Exception as e:
                running_tasks[task_id]['status'] = 'failed'
                running_tasks[task_id]['end_time'] = datetime.now().isoformat()
                running_tasks[task_id]['error'] = str(e)
                running_tasks[task_id]['progress'] = 0
                running_tasks[task_id]['console_logs'].append(f'❌ Error: {str(e)}')
        
        thread = threading.Thread(target=run_task)
        thread.start()
        
        return jsonify({
            'status': 'started',
            'task_id': task_id,
            'message': 'Session saved and automation started'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/task_status/<task_id>')
def get_task_status(task_id):
    if task_id in running_tasks:
        return jsonify(running_tasks[task_id])
    else:
        return jsonify({'status': 'not_found'}), 404

@app.route('/api/logs')
def list_logs():
    try:
        log_files = []
        for filename in os.listdir('logs'):
            if filename.endswith('.csv'):
                filepath = os.path.join('logs', filename)
                stat = os.stat(filepath)
                log_files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify(log_files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<filename>')
def download_log(filename):
    try:
        filepath = os.path.join('logs', filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cookies')
def list_cookies():
    try:
        cookie_files = []
        for filename in os.listdir('cookies'):
            if filename.endswith('.pkl'):
                cookie_name = filename.replace('.pkl', '')
                filepath = os.path.join('cookies', filename)
                stat = os.stat(filepath)
                cookie_files.append({
                    'name': cookie_name,
                    'filename': filename,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        cookie_files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify(cookie_files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)