import streamlit as st
import streamlit.components.v1 as components
import json
import sys
import os
sys.path.append(os.path.dirname(__file__))

from logic import SchedulingLogic

# --- Custom HTML Component for Drag and Drop ---
def drag_and_drop_scheduler(logic_data):
    # Determine horizon based on hard_mode or content
    horizon = 40 if logic_data.hard_mode else 24
    
    # Prepare data for JS
    tasks_json = json.dumps({t_id: {
        "id": t_id,
        "name": t.name,
        "duration": t.duration,
        "skills": t.skills_required,
        "predecessors": t.predecessors,
        "project": t.project,
        "worker": t.assigned_worker,
        "start_time": t.start_time
    } for t_id, t in logic_data.tasks.items()})
    
    workers_json = json.dumps({w_id: {
        "id": w_id,
        "name": w.name,
        "skills": w.skills
    } for w_id, w in logic_data.workers.items()})

    html_code = f"""
    <div id="scheduler-root" style="font-family: 'Inter', sans-serif; color: #e0e0e0; background: #0f1116; padding: 20px; border-radius: 15px;">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
            * {{ box-sizing: border-box; }}
            :root {{
                --hour-width: 40px;
                --total-hours: {horizon};
            }}
            .pool-container {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px dashed rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                min-height: 40px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                padding: 8px;
                margin-bottom: 10px;
            }}
            .timeline-container {{
                overflow-x: auto;
                padding-bottom: 15px;
            }}
            .ruler {{
                display: flex;
                margin-left: 150px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                padding-bottom: 5px;
                margin-bottom: 10px;
            }}
            .ruler-hour {{
                width: var(--hour-width);
                flex-shrink: 0;
                font-size: 10px;
                color: #475569;
                text-align: left;
                padding-left: 2px;
                border-left: 1px solid rgba(255,255,255,0.05);
            }}
            .worker-lanes {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            .lane-row {{
                display: flex;
                align-items: stretch;
                gap: 0;
            }}
            .worker-label {{
                width: 150px;
                min-width: 150px;
                flex-shrink: 0;
                padding-right: 15px;
                font-weight: 600;
                color: #60a5fa;
                font-size: 0.9em;
                display: flex;
                flex-direction: column;
                justify-content: center;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }}
            .lane {{
                flex-shrink: 0;
                width: calc(var(--hour-width) * var(--total-hours));
                background: linear-gradient(90deg, 
                    rgba(255,255,255,0.02) 1px, transparent 1px);
                background-size: var(--hour-width) 100%;
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 4px;
                min-height: 68px;
                position: relative;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            .task-block {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                cursor: grab;
                user-select: none;
                position: absolute;
                height: 64px;
                top: 2px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                justify-content: center;
                transition: background 0.2s, border-color 0.2s;
                overflow: hidden;
            }}
            .pool-task {{
                position: static !important;
                height: 32px !important;
                width: auto !important;
                min-width: 100px;
                padding: 4px 8px !important;
            }}
            .pool-task .task-info:not(:first-of-type) {{
                display: none;
            }}
            .task-block:hover {{
                border-color: #00ffcc;
                z-index: 10;
            }}
            .task-name {{ font-weight: bold; font-size: 0.8em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .task-info {{ font-size: 0.6em; color: #94a3b8; }}
            
            .warning-overlap {{ border-color: #ef4444 !important; background: rgba(239, 68, 68, 0.2) !important; }}
            .warning-precedence {{ border-color: #f59e0b !important; border-style: dashed !important; }}
            .warning-skill {{ background: rgba(236, 72, 153, 0.2) !important; }}
            
            .tooltip {{
                position: absolute;
                bottom: 105%;
                left: 50%;
                transform: translateX(-50%);
                background: #000;
                color: #fff;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 10px;
                line-height: 1.4;
                white-space: pre-line;
                visibility: hidden;
                pointer-events: none;
                opacity: 0.9;
                z-index: 100;
            }}
            .task-block:hover .tooltip {{ visibility: visible; }}
        </style>

        <h4 style="margin-top:0; color:#94a3b8;">📋 Task Pool</h4>
        <div id="pool" class="pool-container"></div>

        <h4 style="color:#94a3b8; display: flex; justify-content: space-between; align-items: center;">
            <span>📅 Timeline (Drag tasks to specific hours)</span>
            <span id="makespan-display" style="color: #00ffcc; font-size: 1.2em;">Makespan: 0h</span>
        </h4>
        <div class="timeline-container">
            <div id="ruler" class="ruler"></div>
            <div id="lanes" class="worker-lanes"></div>
        </div>

        <div style="margin-top: 20px; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px; font-size: 0.75em; display: flex; gap: 20px;">
            <span><strong style="color: #ef4444;">Red Background:</strong> Overlap Warning</span>
            <span><strong style="color: #f59e0b;">Dashed Border:</strong> Precedence Error</span>
            <span><strong style="color: #ec4899;">Pink Background:</strong> Skill Mismatch</span>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/interactjs/dist/interact.min.js"></script>
        <script>
            const tasks = {tasks_json};
            const workers = {workers_json};
            const HOUR_WIDTH = 40;
            
            const projectColors = {{
                'Project Alpha': 'rgba(59, 130, 246, 0.2)',
                'Project Beta': 'rgba(16, 185, 129, 0.2)',
                'Project Gamma': 'rgba(251, 191, 36, 0.2)',
                'Project Delta': 'rgba(236, 72, 153, 0.2)',
                'Project Epsilon': 'rgba(139, 92, 246, 0.2)',
                'Project Zeta': 'rgba(20, 184, 166, 0.2)',
                'Shared': 'rgba(139, 92, 246, 0.2)',
                'Default': 'rgba(107, 114, 128, 0.2)'
            }};
            const projectBorderColors = {{
                'Project Alpha': '#3b82f6',
                'Project Beta': '#10b981',
                'Project Gamma': '#fbbf24',
                'Project Delta': '#ec4899',
                'Project Epsilon': '#8b5cf6',
                'Project Zeta': '#14b8a6',
                'Shared': '#8b5cf6',
                'Default': '#6b7280'
            }};

            const poolEl = document.getElementById('pool');
            const lanesEl = document.getElementById('lanes');
            const rulerEl = document.getElementById('ruler');

            function createTaskEl(task) {{
                const div = document.createElement('div');
                div.className = 'task-block';
                div.id = task.id;
                div.dataset.duration = task.duration;
                div.dataset.projectId = task.project;
                div.style.width = (task.duration * HOUR_WIDTH) + 'px';
                
                const bgColor = projectColors[task.project] || projectColors['Default'];
                const borderColor = projectBorderColors[task.project] || projectBorderColors['Default'];
                div.style.backgroundColor = bgColor;
                div.style.borderColor = borderColor;
                
                const skillNames = task.skills.join(', ');
                const skillHtml = `<div class="task-info" style="color: #60a5fa;">Skills: ${{skillNames}}</div>`;
                
                const predNames = task.predecessors.map(pId => tasks[pId] ? tasks[pId].name : pId).join(', ');
                const predHtml = predNames ? `<div class="task-info" style="color: #cbd5e1; font-style: italic;">Need: ${{predNames}}</div>` : '';

                const infoText = `Length: ${{task.duration}}h\nSkills: ${{skillNames}}`;

                div.innerHTML = `
                    <div class="task-name">${{task.name}}</div>
                    <div class="task-info">${{task.duration}}h | ${{task.project}}</div>
                    ${{skillHtml}}
                    ${{predHtml}}
                    <div class="tooltip" id="tooltip-${{task.id}}">${{infoText}}</div>
                `;
                return div;
            }}

            // 1. Create Ruler
            const HORIZON = {horizon};
            for(let i=0; i<=HORIZON; i++) {{
                const hour = document.createElement('div');
                hour.className = 'ruler-hour';
                hour.innerText = i + 'h';
                rulerEl.appendChild(hour);
            }}

            // 2. Create Tasks and Workers
            const projects = [...new Set(Object.values(tasks).map(t => t.project))].sort();
            
            projects.forEach(projectName => {{
                const projectTasks = Object.values(tasks).filter(t => t.project === projectName && !t.worker);
                const row = document.createElement('div');
                row.style.display = 'flex';
                row.style.alignItems = 'center';
                row.style.marginBottom = '4px';
                row.style.width = '100%';
                row.style.gap = '10px';
                
                const label = document.createElement('div');
                label.style.fontSize = '0.65em';
                label.style.color = projectBorderColors[projectName] || '#94a3b8';
                label.style.fontWeight = 'bold';
                label.style.width = '100px';
                label.style.flexShrink = '0';
                label.innerText = projectName.toUpperCase();
                
                const container = document.createElement('div');
                container.className = 'pool-container project-pool';
                container.dataset.projectId = projectName;
                container.style.marginBottom = '0';
                container.style.minHeight = '30px';
                container.style.flexGrow = '1';
                container.style.border = '1px solid rgba(255,255,255,0.05)';
                container.style.padding = '4px';
                
                projectTasks.forEach(t => {{
                    const el = createTaskEl(t);
                    el.classList.add('pool-task');
                    container.appendChild(el);
                }});
                
                row.appendChild(label);
                row.appendChild(container);
                poolEl.appendChild(row);
                poolEl.style.flexDirection = 'column';
            }});

            Object.values(workers).forEach(w => {{
                const row = document.createElement('div');
                row.className = 'lane-row';
                row.innerHTML = `<div class="worker-label">${{w.name}}<br><small style="color:#475569; font-weight:normal;">${{w.skills.slice(0,2).join(', ')}}</small></div>`;
                
                const lane = document.createElement('div');
                lane.className = 'lane';
                lane.id = `lane-${{w.id}}`;
                lane.dataset.workerId = w.id;
                
                row.appendChild(lane);
                lanesEl.appendChild(row);

                // Add existing tasks if any
                Object.values(tasks).filter(t => t.worker === w.id).forEach(t => {{
                    const el = createTaskEl(t);
                    el.style.left = (t.start_time || 0) * HOUR_WIDTH + 'px';
                    lane.appendChild(el);
                }});
            }});

            // 3. Initialize Drag and Drop with InteractJS
            interact('.task-block').draggable({{
                listeners: {{
                    move(event) {{
                        const target = event.target;
                        const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
                        const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;

                        target.style.transform = `translate(${{x}}px, ${{y}}px)`;
                        target.setAttribute('data-x', x);
                        target.setAttribute('data-y', y);
                    }},
                    end(event) {{
                        const target = event.target;
                        target.style.transform = 'none';
                        target.removeAttribute('data-x');
                        target.removeAttribute('data-y');
                    }}
                }}
            }});

            interact('.lane').dropzone({{
                accept: '.task-block',
                overlap: 0.1,
                ondrop(event) {{
                    const taskEl = event.relatedTarget;
                    const laneEl = event.target;
                    
                    const laneRect = laneEl.getBoundingClientRect();
                    const taskRect = taskEl.getBoundingClientRect();
                    
                    // Use the task's left edge relative to the lane's left edge
                    const dropX = taskRect.left - laneRect.left;
                    let startHour = Math.round(dropX / HOUR_WIDTH);
                    
                    // Strictly enforce 0 as the minimum start time
                    startHour = Math.max(0, Math.min(startHour, HORIZON - parseInt(taskEl.dataset.duration)));
                    
                    taskEl.classList.remove('pool-task');
                    taskEl.style.left = (startHour * HOUR_WIDTH) + 'px';
                    laneEl.appendChild(taskEl);
                    
                    tasks[taskEl.id].worker = laneEl.dataset.workerId;
                    tasks[taskEl.id].start_time = startHour;
                    tasks[taskEl.id].end_time = startHour + tasks[taskEl.id].duration;
                    
                    checkLogic();
                }}
            }});

            interact('.project-pool').dropzone({{
                accept: '.task-block',
                ondrop(event) {{
                    const taskEl = event.relatedTarget;
                    const poolEl = event.target;
                    
                    // Optional: Ensure task goes to its own project pool
                    // const projectPool = document.querySelector(`.project-pool[data-project-id="${{tasks[taskEl.id].project}}"]`);
                    // (projectPool || poolEl).appendChild(taskEl);
                    
                    taskEl.classList.add('pool-task');
                    taskEl.style.left = 'auto';
                    poolEl.appendChild(taskEl);
                    
                    tasks[taskEl.id].worker = null;
                    tasks[taskEl.id].start_time = null;
                    tasks[taskEl.id].end_time = null;
                    checkLogic();
                }}
            }});

            function checkLogic() {{
                const laneEls = document.querySelectorAll('.lane');
                
                Object.values(tasks).forEach(t => {{
                    const el = document.getElementById(t.id);
                    if(el) el.classList.remove('warning-overlap', 'warning-precedence', 'warning-skill');
                    const tooltip = document.getElementById('tooltip-' + t.id);
                    if(tooltip) {{
                        const skillNames = t.skills.join(', ');
                        tooltip.innerText = `OK\nLength: ${{t.duration}}h\nSkills: ${{skillNames}}`;
                    }}
                }});

                laneEls.forEach(lane => {{
                    const worker = workers[lane.dataset.workerId];
                    const laneTasks = Array.from(lane.children).map(el => tasks[el.id]);
                    
                    laneTasks.sort((a,b) => a.start_time - b.start_time);

                    for (let i = 0; i < laneTasks.length; i++) {{
                        const t = laneTasks[i];
                        const el = document.getElementById(t.id);
                        const tooltip = document.getElementById('tooltip-' + t.id);

                        if (!t.skills.some(s => worker.skills.includes(s))) {{
                            el.classList.add('warning-skill');
                            tooltip.innerText = `Skill Mismatch\nLength: ${{t.duration}}h\nSkills: ${{t.skills.join(', ')}}`;
                        }}

                        if (i > 0) {{
                            const prev = laneTasks[i-1];
                            if (t.start_time < prev.end_time) {{
                                el.classList.add('warning-overlap');
                                document.getElementById(prev.id).classList.add('warning-overlap');
                                tooltip.innerText = `Time Overlap!\nLength: ${{t.duration}}h\nSkills: ${{t.skills.join(', ')}}`;
                            }}
                        }}

                        t.predecessors.forEach(pId => {{
                            const pred = tasks[pId];
                            if (!pred.worker) {{
                                el.classList.add('warning-precedence');
                                tooltip.innerText = `Pred. not assigned\nLength: ${{t.duration}}h\nSkills: ${{t.skills.join(', ')}}`;
                            }} else if (pred.end_time > t.start_time) {{
                                el.classList.add('warning-precedence');
                                tooltip.innerText = `Starts before Pred.\nLength: ${{t.duration}}h\nSkills: ${{t.skills.join(', ')}}`;
                            }}
                        }});
                    }}
                }});
                
                updateMakespan();
            }}
            
            function updateMakespan() {{
                let maxEndTime = 0;
                Object.values(tasks).forEach(t => {{
                    if (t.end_time && t.end_time > maxEndTime) {{
                        maxEndTime = t.end_time;
                    }}
                }});
                document.getElementById('makespan-display').innerText = `Makespan: ${{maxEndTime}}h`;
            }}
            
            // Re-run logic immediately to clear any stale state
            checkLogic();
        </script>
    </div>
    """
    components.html(html_code, height=800, scrolling=True)
