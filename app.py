from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Config
PROJECTS_FILE = 'projects.json'

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_projects(projects):
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects, f, indent=2)

@app.route('/')
def index():
    projects = load_projects()
    return render_template('index.html', projects=projects)

@app.route('/add_project', methods=['POST'])
def add_project():
    project_id = request.form.get('project_id')
    project_name = request.form.get('project_name')
    
    projects = load_projects()
    projects[project_id] = {
        'name': project_name,
        'count': 0,
        'last_updated': datetime.now().isoformat()
    }
    save_projects(projects)
    
    return redirect(url_for('index'))

@app.route('/update_counts', methods=['POST'])
def update_counts():
    data = request.json
    projects = load_projects()
    
    for project in data:
        if project['projectId'] in projects:
            projects[project['projectId']]['count'] = project['count']
            projects[project['projectId']]['last_updated'] = datetime.now().isoformat()
    
    save_projects(projects)
    return jsonify({'status': 'success'})

@app.route('/delete_project/<project_id>', methods=['POST'])
def delete_project(project_id):
    projects = load_projects()
    if project_id in projects:
        del projects[project_id]
        save_projects(projects)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Project not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))