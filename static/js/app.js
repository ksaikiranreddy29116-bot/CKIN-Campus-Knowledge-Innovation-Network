document.addEventListener('DOMContentLoaded', () => {

    // --- Faculty Approve / Reject Handlers ---
    document.querySelectorAll('.btn-approve-project').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const projectId = e.target.getAttribute('data-project-id');
            if (!confirm("Are you sure you want to APPROVE this project?")) return;

            try {
                const response = await fetch(`/api/projects/${projectId}/approve`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const result = await response.json();
                if (result.success) {
                    alert("Project approved!");
                    location.reload();
                } else {
                    alert("Error: " + result.error);
                }
            } catch (err) {
                alert("Request failed: " + err);
            }
        });
    });

    document.querySelectorAll('.btn-reject-project').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const projectId = e.target.getAttribute('data-project-id');
            if (!confirm("Are you sure you want to REJECT this project?")) return;

            try {
                const response = await fetch(`/api/projects/${projectId}/reject`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const result = await response.json();
                if (result.success) {
                    alert("Project rejected.");
                    location.reload();
                } else {
                    alert("Error: " + result.error);
                }
            } catch (err) {
                alert("Request failed: " + err);
            }
        });
    });

    // --- What-If Skill Simulator Handler ---
    const simForm = document.getElementById('what-if-sim-form');
    if (simForm) {
        simForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const projectId = document.getElementById('sim-project-id').value;
            const skill = document.getElementById('sim-skill-input').value;
            const resContainer = document.getElementById('sim-result-container');

            try {
                const res = await fetch('/api/recommendations/simulate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ project_id: projectId, skill: skill })
                });
                const data = await res.json();

                if (data.success) {
                    const info = data.data;
                    resContainer.innerHTML = `
                        <div class="alert alert-info mt-3">
                            <h6 class="fw-bold mb-2">Simulated Outcome for learning "${info.hypothetical_skill}":</h6>
                            <p class="mb-1"><strong>Skill Coverage:</strong> ${info.original_coverage_percentage}% &rarr; <span class="text-success fw-bold">${info.simulated_coverage_percentage}%</span></p>
                            <p class="mb-1"><strong>Compatibility Score:</strong> ${info.original_compatibility_pct}% &rarr; <span class="text-success fw-bold">${info.simulated_compatibility_pct}%</span></p>
                            <p class="mb-0"><strong>Score Change:</strong> <span class="badge ${info.score_difference_pct >= 0 ? 'bg-success' : 'bg-secondary'}">+${info.score_difference_pct}%</span></p>
                        </div>
                    `;
                } else {
                    resContainer.innerHTML = `<div class="alert alert-danger mt-3">${data.error}</div>`;
                }
            } catch (err) {
                resContainer.innerHTML = `<div class="alert alert-danger mt-3">Simulation failed: ${err}</div>`;
            }
        });
    }

    // --- Team Invite Handler ---
    document.querySelectorAll('.btn-invite-student').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const projectId = e.target.getAttribute('data-project-id');
            const studentId = e.target.getAttribute('data-student-id');

            try {
                const res = await fetch('/api/collaboration/invite', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ project_id: projectId, invitee_id: studentId })
                });
                const data = await res.json();
                if (data.success) {
                    alert("Invitation sent!");
                    e.target.disabled = true;
                    e.target.innerText = "Invited";
                } else {
                    alert("Invitation failed: " + data.error);
                }
            } catch (err) {
                alert("Error: " + err);
            }
        });
    });

    // --- Join Request Handler ---
    const joinReqBtn = document.getElementById('btn-submit-join-request');
    if (joinReqBtn) {
        joinReqBtn.addEventListener('click', async () => {
            const projectId = joinReqBtn.getAttribute('data-project-id');
            const msg = document.getElementById('join-request-msg')?.value || '';

            try {
                const res = await fetch('/api/collaboration/join-request', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ project_id: projectId, message: msg })
                });
                const data = await res.json();
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert("Request failed: " + data.error);
                }
            } catch (err) {
                alert("Error: " + err);
            }
        });
    }

    // --- Respond to Join Request / Invitation Handlers ---
    document.querySelectorAll('.btn-respond-invite').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const invId = e.target.getAttribute('data-invitation-id');
            const action = e.target.getAttribute('data-action');

            try {
                const res = await fetch(`/api/collaboration/invitations/${invId}/respond`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ action: action })
                });
                const data = await res.json();
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            } catch (err) {
                alert("Request error: " + err);
            }
        });
    });

    document.querySelectorAll('.btn-respond-join-request').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const reqId = e.target.getAttribute('data-request-id');
            const action = e.target.getAttribute('data-action');

            try {
                const res = await fetch(`/api/collaboration/join-requests/${reqId}/respond`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ action: action })
                });
                const data = await res.json();
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            } catch (err) {
                alert("Request error: " + err);
            }
        });
    });

    // --- Task Creation Handler ---
    const addTaskForm = document.getElementById('add-task-form');
    if (addTaskForm) {
        addTaskForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const projectId = document.getElementById('task-project-id').value;
            const title = document.getElementById('task-title').value.trim();
            const description = document.getElementById('task-description').value.trim();
            const assignedTo = document.getElementById('task-assigned-to').value;
            const dueDate = document.getElementById('task-due-date').value;
            const status = document.getElementById('task-status').value;
            const progress = document.getElementById('task-progress').value;
            const priorityElem = document.getElementById('task-priority');
            const priority = priorityElem ? priorityElem.value : 'Medium';

            if (!title) {
                alert("Please enter a task title.");
                return;
            }

            const submitBtn = document.getElementById('btn-submit-task');
            if (submitBtn) submitBtn.disabled = true;

            try {
                const res = await fetch(`/api/tasks/${projectId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        title: title,
                        description: description,
                        assigned_to: assignedTo,
                        due_date: dueDate,
                        status: status,
                        progress: progress,
                        priority: priority
                    })
                });

                const contentType = res.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const text = await res.text();
                    throw new Error(`Server returned non-JSON response (${res.status}): ${text.substring(0, 100)}`);
                }

                const data = await res.json();
                if (res.ok && data.success) {
                    location.reload();
                } else {
                    alert("Task creation failed: " + (data.error || "Unexpected response from server."));
                    if (submitBtn) submitBtn.disabled = false;
                }
            } catch (err) {
                alert("Error creating task: " + (err.message || err));
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

    // --- Task Progress & Status Update Handler ---
    document.querySelectorAll('.btn-update-task-progress').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const taskId = e.target.getAttribute('data-task-id');
            const parent = e.target.closest('.list-group-item');
            const progressInput = parent ? parent.querySelector('.task-progress-input') : null;
            const statusSelect = parent ? parent.querySelector('.task-status-select') : null;

            const progress = progressInput ? progressInput.value : 0;
            const status = statusSelect ? statusSelect.value : 'pending';

            if (progress < 0 || progress > 100) {
                alert("Progress percentage must be between 0 and 100.");
                return;
            }

            e.target.disabled = true;

            try {
                const res = await fetch(`/api/tasks/${taskId}/progress`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ status: status, progress: progress })
                });

                const data = await res.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert("Failed to update task: " + data.error);
                    e.target.disabled = false;
                }
            } catch (err) {
                alert("Error updating task: " + err);
                e.target.disabled = false;
            }
        });
    });

    // --- Mark Notification as Read ---
    document.querySelectorAll('.btn-mark-read').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const notifId = e.target.getAttribute('data-notif-id');
            try {
                const res = await fetch(`/api/notifications/${notifId}/read`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    location.reload();
                }
            } catch (err) {
                console.error(err);
            }
        });
    });

    const markAllReadBtn = document.getElementById('btn-mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/notifications/read-all', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    location.reload();
                }
            } catch (err) {
                console.error(err);
            }
        });
    }
});
