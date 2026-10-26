/**
 * AI-Powered Intern Review Automation - Frontend Application
 */

const STATE = {
  token: null,
  user: null,
  internProfile: null,
  activeTab: 'admin-dashboard',
  cachedInterns: [],
  cachedTasks: [],
  cachedMentors: []
};

// Persona login credentials for seamless testing & pairing
const PERSONAS = {
  admin: { email: 'admin@company.com', password: 'Admin@2026' },
  mentor: { email: 'mentor.sarah@company.com', password: 'Mentor@2026' },
  intern_aarav: { email: 'aarav.patel@company.com', password: 'Intern@2026' },
  intern_sneha: { email: 'sneha.sharma@company.com', password: 'Intern@2026' }
};

// Toast notification helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  const bg = type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6';
  toast.style.cssText = `background: ${bg}; color: white; padding: 12px 18px; border-radius: 8px; font-size: 0.875rem; font-weight: 500; box-shadow: 0 4px 12px rgba(0,0,0,0.15); transition: opacity 0.3s;`;
  toast.innerHTML = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// API request wrapper
async function apiRequest(endpoint, options = {}) {
  const headers = options.headers || {};
  if (STATE.token) {
    headers['Authorization'] = `Bearer ${STATE.token}`;
  }
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(endpoint, { ...options, headers });
  if (res.status === 401) {
    showToast('Session expired. Re-authenticating...', 'error');
    loginPersona('admin');
    throw new Error('Unauthorized');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.detail || 'An unexpected error occurred.';
    showToast(errorMsg, 'error');
    throw new Error(errorMsg);
  }
  return data;
}

// Authenticate persona
async function loginPersona(personaKey) {
  const creds = PERSONAS[personaKey] || PERSONAS.admin;
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(creds)
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || 'Login failed', 'error');
      return;
    }

    STATE.token = data.access_token;
    STATE.user = data.user;
    
    // Update navbar
    document.getElementById('navUserName').textContent = data.user.full_name;
    document.getElementById('navUserRole').textContent = data.user.role;
    document.getElementById('navUserAvatar').textContent = data.user.full_name.charAt(0);

    // Adjust tabs based on role
    adjustTabsForRole(data.user.role);

    showToast(`Logged in as ${data.user.full_name} (${data.user.role})`, 'success');

    // Refresh current view
    refreshCurrentView();
  } catch (e) {
    console.error('Persona login error:', e);
  }
}

function handleQuickRoleChange(personaKey) {
  loginPersona(personaKey);
}

function adjustTabsForRole(role) {
  const nav = document.getElementById('mainTabNav');
  const buttons = nav.querySelectorAll('.tab-btn');

  if (role === 'INTERN') {
    buttons.forEach(btn => {
      const tab = btn.getAttribute('data-tab');
      btn.style.display = (tab === 'intern-portal') ? 'flex' : 'none';
    });
    switchTab('intern-portal');
  } else if (role === 'MENTOR') {
    buttons.forEach(btn => {
      const tab = btn.getAttribute('data-tab');
      btn.style.display = (tab === 'admin-dashboard' || tab === 'mentor-workspace' || tab === 'admin-interns' || tab === 'admin-reviews' || tab === 'intern-portal') ? 'flex' : 'none';
    });
    switchTab('mentor-workspace');
  } else {
    // Admin has access to all tabs
    buttons.forEach(btn => btn.style.display = 'flex');
    switchTab('admin-dashboard');
  }
}

// Tab navigation
function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(section => {
    section.style.display = (section.id === `tab-${tabId}`) ? 'block' : 'none';
  });
  refreshCurrentView();
}

function refreshCurrentView() {
  switch (STATE.activeTab) {
    case 'admin-dashboard':
      loadDashboardStats();
      break;
    case 'admin-interns':
      loadInternsTable();
      break;
    case 'admin-tasks':
      loadTasksList();
      break;
    case 'mentor-workspace':
      loadMentorWorkspace();
      break;
    case 'admin-reviews':
      loadReviewsList();
      break;
    case 'admin-emails':
      loadEmailLogs();
      break;
    case 'admin-audit':
      loadAuditLogs();
      break;
    case 'intern-portal':
      loadInternDashboard();
      break;
  }
}

// Status badge helper
function getStatusBadge(status) {
  const map = {
    'Registered': 'badge-registered',
    'Task Assigned': 'badge-task-assigned',
    'In Progress': 'badge-in-progress',
    'Submitted': 'badge-submitted',
    'AI Evaluation Pending': 'badge-eval-pending',
    'Mentor Approval Pending': 'badge-approval-pending',
    'Review Scheduled': 'badge-review-scheduled',
    'Feedback Published': 'badge-feedback-published',
    'Corrections Required': 'badge-corrections-required',
    'Resubmitted': 'badge-resubmitted',
    'Approved': 'badge-approved',
    'Overdue': 'badge-overdue',
    'Closed': 'badge-closed'
  };
  const cls = map[status] || 'badge-registered';
  return `<span class="badge ${cls}"><span class="badge-dot"></span>${status}</span>`;
}

// ==================== DASHBOARD ====================
async function loadDashboardStats() {
  try {
    const stats = await apiRequest('/api/admin/stats');
    document.getElementById('statTotalInterns').textContent = stats.total_interns;
    document.getElementById('statNotStarted').textContent = stats.not_started;
    document.getElementById('statInProgress').textContent = stats.in_progress;
    document.getElementById('statSubmitted').textContent = stats.submitted_for_review;
    document.getElementById('statReviewsScheduled').textContent = stats.reviews_scheduled;
    document.getElementById('statReviewsCompleted').textContent = stats.reviews_completed;
    document.getElementById('statOverdue').textContent = stats.overdue_interns;
    document.getElementById('statNeedsReview').textContent = stats.needs_another_review;

    document.getElementById('internsCountBadge').textContent = stats.total_interns;

    // Upcoming reviews table
    const tbody = document.getElementById('upcomingReviewsTableBody');
    if (!stats.upcoming_reviews || stats.upcoming_reviews.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No upcoming reviews scheduled. Click 'Schedule New Review' to create one.</td></tr>`;
      return;
    }

    tbody.innerHTML = stats.upcoming_reviews.map(r => `
      <tr>
        <td><strong>${r.intern_name}</strong></td>
        <td><code>${r.intern_id}</code></td>
        <td>${r.mentor_name}</td>
        <td>${r.review_date} (${r.time})</td>
        <td><a href="${r.google_meet_link}" target="_blank" style="font-weight:600;"><i class="fa-solid fa-video"></i> Join Meet</a></td>
        <td>${getStatusBadge(r.status)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="triggerReviewReminder(${r.id}, '24h')">
            <i class="fa-regular fa-bell"></i> Send 24h Reminder
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Stats loading error:', e);
  }
}

// ==================== INTERNS MANAGEMENT ====================
let internSearchTimeout = null;
function debounceLoadInterns() {
  clearTimeout(internSearchTimeout);
  internSearchTimeout = setTimeout(loadInternsTable, 300);
}

function resetInternFilters() {
  document.getElementById('internSearchInput').value = '';
  document.getElementById('internDeptFilter').value = '';
  document.getElementById('internStatusFilter').value = '';
  loadInternsTable();
}

async function loadInternsTable() {
  const search = document.getElementById('internSearchInput').value;
  const dept = document.getElementById('internDeptFilter').value;
  const status = document.getElementById('internStatusFilter').value;

  let url = `/api/admin/interns?limit=200`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (dept) url += `&department=${encodeURIComponent(dept)}`;
  if (status) url += `&status=${encodeURIComponent(status)}`;

  try {
    const data = await apiRequest(url);
    STATE.cachedInterns = data.interns;
    document.getElementById('internsCountBadge').textContent = data.total;

    const tbody = document.getElementById('internsTableBody');
    if (!data.interns || data.interns.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No intern records found matching criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.interns.map(i => `
      <tr>
        <td><code>${i.intern_id}</code></td>
        <td>
          <strong>${i.full_name}</strong><br>
          <span style="font-size: 0.75rem; color: var(--text-muted);">${i.email}</span>
        </td>
        <td><span class="badge" style="background:var(--bg-subtle);">${i.department}</span></td>
        <td>${i.mentor_name}</td>
        <td>${i.task_title || '<span style="color:var(--text-light);">None</span>'}</td>
        <td>${i.task_deadline ? new Date(i.task_deadline).toLocaleDateString() : '-'}</td>
        <td>${getStatusBadge(i.status)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="viewInternDetail(${i.id})">
            <i class="fa-regular fa-eye"></i> Profile
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Error loading interns:', e);
  }
}

// Modal open/close helpers
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function openImportModal() { openModal('importModal'); }
function openAddInternModal() { openModal('addInternModal'); }
function openCreateTaskModal() { openModal('createTaskModal'); }

// Handle file selection in Bulk Import modal
let selectedImportFile = null;
function handleImportFileSelect(input) {
  if (input.files && input.files[0]) {
    selectedImportFile = input.files[0];
    document.getElementById('importFileName').textContent = `Selected: ${selectedImportFile.name} (${Math.round(selectedImportFile.size / 1024)} KB)`;
  }
}

// One-click shortcut: load sample 105 interns CSV
async function loadBundledSampleCSV() {
  try {
    const res = await fetch('/static/../data/sample_100_interns.csv');
    if (!res.ok) {
      // Direct API upload simulation
      showToast('Fetching sample 105 interns dataset...', 'info');
    }
    const blob = await res.blob();
    selectedImportFile = new File([blob], 'sample_100_interns.csv', { type: 'text/csv' });
    document.getElementById('importFileName').textContent = 'Loaded: sample_100_interns.csv (105 records ready)';
    showToast('Loaded bundled 105 interns CSV into upload queue! Click "Import Interns".', 'success');
  } catch (e) {
    showToast('Failed to load sample dataset: ' + e.message, 'error');
  }
}

async function handleBulkImport(e) {
  e.preventDefault();
  if (!selectedImportFile) {
    showToast('Please select a CSV or Excel file to import.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedImportFile);

  const btn = document.getElementById('btnSubmitImport');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing 100+ Interns...`;

  try {
    const res = await apiRequest('/api/admin/interns/import', {
      method: 'POST',
      body: formData
    });

    closeModal('importModal');
    showToast(`Bulk Import Complete: ${res.successful_imports} imported, ${res.duplicate_emails_skipped} duplicate emails skipped.`, 'success');
    loadInternsTable();
    loadDashboardStats();
  } catch (err) {
    // Handled by apiRequest
  } finally {
    btn.disabled = false;
    btn.textContent = 'Import Interns';
  }
}

// Single intern creation
async function handleAddIntern(e) {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById('addInternName').value,
    email: document.getElementById('addInternEmail').value,
    intern_id: document.getElementById('addInternId').value,
    department: document.getElementById('addInternDept').value
  };

  try {
    await apiRequest('/api/admin/interns', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    closeModal('addInternModal');
    showToast(`Intern ${payload.full_name} (${payload.intern_id}) registered successfully!`, 'success');
    document.getElementById('addInternForm').reset();
    loadInternsTable();
    loadDashboardStats();
  } catch (err) {}
}

// View intern details drawer
async function viewInternDetail(internId) {
  try {
    const intern = await apiRequest(`/api/admin/interns/${internId}`);
    const modalContent = document.getElementById('internDetailModalContent');

    modalContent.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; background: var(--bg-subtle); padding: 1rem; border-radius: var(--radius-md);">
        <div><strong>Name:</strong> ${intern.full_name}</div>
        <div><strong>Intern ID:</strong> <code>${intern.intern_id}</code></div>
        <div><strong>Email:</strong> ${intern.email}</div>
        <div><strong>Department:</strong> ${intern.department}</div>
        <div><strong>Assigned Mentor:</strong> ${intern.mentor_name}</div>
        <div><strong>Status:</strong> ${getStatusBadge(intern.status)}</div>
        <div><strong>Assigned Task:</strong> ${intern.assigned_task ? intern.assigned_task.title : 'None'}</div>
        <div><strong>Deadline:</strong> ${intern.task_deadline ? new Date(intern.task_deadline).toLocaleString() : 'None'}</div>
      </div>

      <h3 style="margin-bottom: 0.75rem;"><i class="fa-solid fa-file-lines" style="color: var(--primary);"></i> Submissions & Versions</h3>
      ${intern.submissions && intern.submissions.length > 0 ? `
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${intern.submissions.map(s => `
            <div style="border: 1px solid var(--border); padding: 1rem; border-radius: var(--radius-md);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong>Version ${s.version} — ${s.file_name} (${Math.round(s.file_size / 1024)} KB)</strong>
                <span style="font-size: 0.75rem; color: var(--text-muted);">${new Date(s.submitted_at).toLocaleString()}</span>
              </div>
              <p style="font-size: 0.8125rem; color: var(--text-muted); margin-bottom: 0.5rem;">${s.description || 'No description provided.'}</p>
              ${s.evaluation ? `
                <div style="background: white; border-left: 3px solid var(--primary); padding: 0.75rem; border-radius: 4px; font-size: 0.8125rem;">
                  <div><strong>AI Completion:</strong> ${s.evaluation.completion_percentage}% | <strong>Score:</strong> ${s.evaluation.overall_score}/${s.evaluation.max_score} (${s.evaluation.is_provisional ? 'Provisional' : 'Mentor Approved'})</div>
                  <div><strong>Mentor Notes:</strong> ${s.evaluation.mentor_notes || 'None'}</div>
                </div>
              ` : '<div style="font-size: 0.75rem; color: var(--text-muted);">AI Evaluation Pending</div>'}
            </div>
          `).join('')}
        </div>
      ` : '<p style="color: var(--text-muted); font-size: 0.875rem;">No submissions uploaded yet.</p>'}
    `;

    openModal('internDetailModal');
  } catch (err) {}
}

// ==================== TASK MANAGEMENT ====================
function addRubricRow() {
  const container = document.getElementById('rubricRowsContainer');
  const div = document.createElement('div');
  div.className = 'rubric-row';
  div.style.cssText = 'display: grid; grid-template-columns: 2fr 3fr 1fr auto; gap: 0.5rem; align-items: center;';
  div.innerHTML = `
    <input type="text" class="rubric-req" placeholder="Criterion name" required>
    <input type="text" class="rubric-desc" placeholder="Criteria description" required>
    <input type="number" class="rubric-marks" placeholder="Marks" value="25" required>
    <button type="button" class="close-btn" onclick="this.parentElement.remove()">&times;</button>
  `;
  container.appendChild(div);
}

async function handleCreateTask(e) {
  e.preventDefault();
  const rows = document.querySelectorAll('#rubricRowsContainer .rubric-row');
  const rubricList = [];
  rows.forEach(r => {
    const req = r.querySelector('.rubric-req').value;
    const desc = r.querySelector('.rubric-desc').value;
    const marks = parseFloat(r.querySelector('.rubric-marks').value) || 20;
    if (req) rubricList.push({ requirement: req, description: desc, max_marks: marks });
  });

  const payload = {
    title: document.getElementById('taskTitleInput').value,
    description: document.getElementById('taskDescInput').value,
    deliverables: document.getElementById('taskDeliverablesInput').value,
    submission_format: document.getElementById('taskFormatInput').value,
    rubric_criteria: rubricList,
    max_marks: parseInt(document.getElementById('taskMaxMarksInput').value) || 100
  };

  try {
    await apiRequest('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    closeModal('createTaskModal');
    showToast(`Task '${payload.title}' created with ${rubricList.length} rubric criteria!`, 'success');
    loadTasksList();
  } catch (err) {}
}

async function loadTasksList() {
  try {
    const tasks = await apiRequest('/api/tasks');
    STATE.cachedTasks = tasks;
    const container = document.getElementById('tasksListContainer');

    if (!tasks || tasks.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted);">No tasks created yet. Click 'Create New Task' to get started.</p>`;
      return;
    }

    container.innerHTML = tasks.map(t => {
      let rubric = [];
      try { rubric = JSON.parse(t.rubric_criteria); } catch (e) {}

      return `
        <div class="card" style="margin-bottom: 0;">
          <div class="card-header">
            <h3>${t.title}</h3>
            <span class="badge badge-primary">Max: ${t.max_marks} pts</span>
          </div>
          <p style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.75rem;">${t.description}</p>
          <div style="font-size: 0.8125rem; background: var(--bg-subtle); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.75rem;">
            <strong>Expected Deliverables:</strong>
            <pre style="white-space: pre-wrap; font-family: inherit; margin-top: 0.25rem;">${t.deliverables}</pre>
          </div>
          <div style="margin-bottom: 0.75rem;">
            <strong style="font-size: 0.8125rem;">Rubric Criteria (${rubric.length}):</strong>
            <ul style="padding-left: 1.25rem; font-size: 0.8125rem; color: var(--text-muted); margin-top: 0.25rem;">
              ${rubric.map(r => `<li><strong>${r.requirement}</strong> (${r.max_marks} marks): ${r.description}</li>`).join('')}
            </ul>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="openAssignTaskModal(${t.id})">
            <i class="fa-solid fa-user-check"></i> Assign to Interns
          </button>
        </div>
      `;
    }).join('');
  } catch (err) {}
}

// Bulk Task Assignment
async function openAssignTaskModal(preselectedTaskId = null) {
  // Populate task dropdown
  const taskSelect = document.getElementById('assignTaskSelect');
  if (STATE.cachedTasks.length === 0) {
    STATE.cachedTasks = await apiRequest('/api/tasks');
  }
  taskSelect.innerHTML = STATE.cachedTasks.map(t => `
    <option value="${t.id}" ${t.id === preselectedTaskId ? 'selected' : ''}>${t.title} (${t.max_marks} marks)</option>
  `).join('');

  // Default deadline 7 days out
  const defaultDeadline = new Date();
  defaultDeadline.setDate(defaultDeadline.getDate() + 7);
  document.getElementById('assignTaskDeadline').value = defaultDeadline.toISOString().slice(0, 16);

  // Populate interns checkbox list
  if (STATE.cachedInterns.length === 0) {
    const res = await apiRequest('/api/admin/interns?limit=300');
    STATE.cachedInterns = res.interns;
  }

  filterAssignInternsList('');
  openModal('assignTaskModal');
}

function filterAssignInternsList(dept) {
  const container = document.getElementById('assignInternsCheckboxList');
  const filtered = dept ? STATE.cachedInterns.filter(i => i.department === dept) : STATE.cachedInterns;

  container.innerHTML = filtered.map(i => `
    <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0; font-size: 0.8125rem;">
      <input type="checkbox" class="assign-intern-cb" value="${i.id}" id="cb-intern-${i.id}" checked>
      <label for="cb-intern-${i.id}"><strong>${i.intern_id}</strong> — ${i.full_name} (${i.department})</label>
    </div>
  `).join('');
}

function toggleSelectAllInterns() {
  const cbs = document.querySelectorAll('.assign-intern-cb');
  const allChecked = Array.from(cbs).every(cb => cb.checked);
  cbs.forEach(cb => cb.checked = !allChecked);
}

async function handleAssignTask(e) {
  e.preventDefault();
  const taskId = parseInt(document.getElementById('assignTaskSelect').value);
  const deadline = document.getElementById('assignTaskDeadline').value;
  const sendEmail = document.getElementById('assignSendEmailCheck').checked;

  const selectedIds = Array.from(document.querySelectorAll('.assign-intern-cb:checked')).map(cb => parseInt(cb.value));
  if (selectedIds.length === 0) {
    showToast('Please select at least one intern to assign.', 'error');
    return;
  }

  const btn = document.getElementById('btnConfirmAssign');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Assigning & Notifying...`;

  try {
    const res = await apiRequest('/api/tasks/assign', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
        intern_ids: selectedIds,
        deadline: new Date(deadline).toISOString(),
        send_email: sendEmail
      })
    });

    closeModal('assignTaskModal');
    showToast(res.message, 'success');
    loadInternsTable();
    loadDashboardStats();
  } catch (err) {} finally {
    btn.disabled = false;
    btn.textContent = 'Assign Task';
  }
}

// ==================== MENTOR WORKSPACE ====================
async function loadMentorWorkspace() {
  try {
    const data = await apiRequest('/api/mentor/workspace');
    document.getElementById('pendingEvalBadge').textContent = data.pending_submissions.length;

    const container = document.getElementById('mentorPendingList');
    if (!data.pending_submissions || data.pending_submissions.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.875rem;">No submissions currently awaiting mentor review. All evaluations are up to date!</p>`;
      return;
    }

    container.innerHTML = data.pending_submissions.map(sub => `
      <div class="card" style="border-left: 4px solid var(--primary); margin-bottom: 1rem;">
        <div class="card-header">
          <div>
            <h3>${sub.intern_name} (<code>${sub.intern_id}</code>) — Version ${sub.version}</h3>
            <span style="font-size: 0.8125rem; color: var(--text-muted);">Task: ${sub.task_title} | File: ${sub.file_name}</span>
          </div>
          <div style="text-align: right;">
            <span class="badge ${sub.completion_percentage >= 75 ? 'badge-approved' : 'badge-in-progress'}">
              AI Completion: ${sub.completion_percentage}%
            </span>
            <div style="font-size: 0.75rem; color: var(--text-light); margin-top: 0.25rem;">Submitted: ${new Date(sub.submitted_at).toLocaleDateString()}</div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
          <div style="background: var(--bg-subtle); padding: 0.75rem; border-radius: var(--radius-sm); font-size: 0.8125rem;">
            <strong style="color: var(--success);"><i class="fa-solid fa-check"></i> Completed Items:</strong>
            <ul style="padding-left: 1.25rem; margin-top: 0.25rem;">
              ${(sub.strengths || []).map(s => `<li>${s}</li>`).join('')}
            </ul>
          </div>
          <div style="background: var(--danger-bg); padding: 0.75rem; border-radius: var(--radius-sm); font-size: 0.8125rem;">
            <strong style="color: var(--danger);"><i class="fa-solid fa-xmark"></i> Missing / Incomplete Items:</strong>
            <ul style="padding-left: 1.25rem; margin-top: 0.25rem;">
              ${(sub.missing_items || []).map(m => `<li>${m}</li>`).join('') || '<li>None identified.</li>'}
            </ul>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 0.5rem;">
          <button class="btn btn-secondary btn-sm" onclick="openRequestCorrectionsModal(${sub.intern_profile_id}, '${sub.intern_name}')">
            <i class="fa-solid fa-rotate-left"></i> Request Corrections
          </button>
          <button class="btn btn-primary btn-sm" onclick="openMentorReviewModal(${sub.evaluation_id}, ${JSON.stringify(sub).replace(/"/g, '&quot;')})">
            <i class="fa-solid fa-user-pen"></i> Review & Approve Evaluation
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {}
}

function openMentorReviewModal(evalId, subData) {
  const modalContent = document.getElementById('mentorReviewModalContent');
  modalContent.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <h3>Evaluating: ${subData.intern_name} (ID: ${subData.intern_id})</h3>
      <p style="font-size: 0.875rem; color: var(--text-muted);">Task: ${subData.task_title} | Version: ${subData.version} | Deliverable: ${subData.file_name}</p>
    </div>

    <div style="border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1rem; background: var(--bg-subtle);">
      <h4 style="margin-bottom: 0.5rem;">AI Provisional Rubric Breakdown:</h4>
      ${(subData.requirement_evaluations || []).map(r => `
        <div style="background: white; padding: 0.65rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem; border: 1px solid var(--border); font-size: 0.8125rem;">
          <div style="display: flex; justify-content: space-between; font-weight: 600;">
            <span>${r.requirement} (${r.awarded_marks}/${r.max_marks} marks)</span>
            <span class="badge ${r.status === 'Completed' ? 'badge-approved' : r.status === 'Partially Completed' ? 'badge-in-progress' : 'badge-corrections-required'}">${r.status}</span>
          </div>
          <p style="color: var(--text-muted); margin-top: 0.25rem;">${r.explanation}</p>
        </div>
      `).join('')}
    </div>

    <form onsubmit="handleMentorApprovalSubmit(event, ${evalId})">
      <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; margin-bottom: 1rem;">
        <div>
          <label style="font-size: 0.8125rem; font-weight: 600;">Final Score (Max: ${subData.max_score}):</label>
          <input type="number" step="0.5" id="mentorFinalScoreInput" value="${subData.provisional_score}" required>
        </div>
        <div>
          <label style="font-size: 0.8125rem; font-weight: 600;">Workflow Action:</label>
          <select id="mentorActionSelect">
            <option value="publish">Publish Feedback (Feedback Published)</option>
            <option value="approve_final">Approve Task & Close Review Cycle (Approved)</option>
          </select>
        </div>
      </div>

      <div>
        <label style="font-size: 0.8125rem; font-weight: 600;">Mentor Feedback & Comments for Intern:</label>
        <textarea id="mentorNotesInput" rows="3" required placeholder="Constructive guidance, strengths noted, and next steps...">${subData.mentor_notes || 'Excellent implementation. All core deliverables and rubric criteria have been satisfied.'}</textarea>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="closeModal('mentorReviewModal')">Cancel</button>
        <button type="submit" class="btn btn-success">
          <i class="fa-solid fa-check-double"></i> Confirm & Publish Mentor Evaluation
        </button>
      </div>
    </form>
  `;
  openModal('mentorReviewModal');
}

async function handleMentorApprovalSubmit(e, evalId) {
  e.preventDefault();
  const score = parseFloat(document.getElementById('mentorFinalScoreInput').value);
  const notes = document.getElementById('mentorNotesInput').value;
  const action = document.getElementById('mentorActionSelect').value;

  try {
    await apiRequest(`/api/mentor/evaluations/${evalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        overall_score: score,
        mentor_notes: notes,
        approve_evaluation: true,
        update_status_to_approved: (action === 'approve_final')
      })
    });

    closeModal('mentorReviewModal');
    showToast('Mentor evaluation confirmed and feedback email dispatched to intern!', 'success');
    loadMentorWorkspace();
    loadDashboardStats();
  } catch (err) {}
}

function openRequestCorrectionsModal(internId, internName) {
  const checklist = prompt(`Request corrections for ${internName}.\nEnter revision checklist / instructions:`, '1. Implement robust try/except error boundary.\n2. Add automated unit test asserting output format.');
  if (!checklist) return;

  const defaultDeadline = new Date();
  defaultDeadline.setDate(defaultDeadline.getDate() + 3);

  apiRequest(`/api/mentor/interns/${internId}/request-corrections`, {
    method: 'POST',
    body: JSON.stringify({
      checklist: checklist,
      resubmission_deadline: defaultDeadline.toISOString()
    })
  }).then(res => {
    showToast(`Corrections requested for ${internName}. Intern notified via email!`, 'success');
    loadMentorWorkspace();
    loadDashboardStats();
  });
}

// ==================== REVIEW SCHEDULING ====================
async function openScheduleReviewModal() {
  if (STATE.cachedInterns.length === 0) {
    const res = await apiRequest('/api/admin/interns?limit=300');
    STATE.cachedInterns = res.interns;
  }

  // Populate intern select
  const internSelect = document.getElementById('scheduleInternSelect');
  internSelect.innerHTML = STATE.cachedInterns.map(i => `
    <option value="${i.id}">${i.intern_id} — ${i.full_name} (${i.department})</option>
  `).join('');

  // Default mentor
  const mentorSelect = document.getElementById('scheduleMentorSelect');
  mentorSelect.innerHTML = `
    <option value="2">Sarah Jenkins (Senior AI Lead)</option>
    <option value="3">Alex Rivera (Engineering Manager)</option>
  `;

  // Default tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('scheduleReviewDate').value = tomorrow.toISOString().slice(0, 10);
  document.getElementById('scheduleMeetLink').value = 'https://meet.google.com/xyz-qwer-vbn';

  openModal('scheduleReviewModal');
}

async function handleScheduleReview(e) {
  e.preventDefault();
  const internId = parseInt(document.getElementById('scheduleInternSelect').value);
  const mentorId = parseInt(document.getElementById('scheduleMentorSelect').value);
  const dateStr = document.getElementById('scheduleReviewDate').value;
  const startTime = document.getElementById('scheduleStartTime').value;
  const endTime = document.getElementById('scheduleEndTime').value;
  const meetLink = document.getElementById('scheduleMeetLink').value;
  const notes = document.getElementById('scheduleNotes').value;
  const sendEmail = document.getElementById('scheduleSendEmailCheck').checked;

  try {
    await apiRequest('/api/reviews', {
      method: 'POST',
      body: JSON.stringify({
        intern_id: internId,
        mentor_id: mentorId,
        review_date: new Date(dateStr).toISOString(),
        start_time: startTime,
        end_time: endTime,
        google_meet_link: meetLink,
        notes: notes,
        send_invitation_email: sendEmail
      })
    });

    closeModal('scheduleReviewModal');
    showToast('Performance review scheduled and Google Meet invitation dispatched!', 'success');
    loadReviewsList();
    loadDashboardStats();
  } catch (err) {}
}

async function loadReviewsList() {
  try {
    const reviews = await apiRequest('/api/reviews');
    const tbody = document.getElementById('reviewsAllTableBody');

    if (!reviews || reviews.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No review sessions recorded.</td></tr>`;
      return;
    }

    tbody.innerHTML = reviews.map(r => `
      <tr>
        <td>#${r.id}</td>
        <td>Intern Profile #${r.intern_id}</td>
        <td>Mentor #${r.mentor_id}</td>
        <td>${new Date(r.review_date).toLocaleDateString()}</td>
        <td>${r.start_time} - ${r.end_time} (${r.timezone})</td>
        <td><a href="${r.google_meet_link}" target="_blank" style="font-weight:600;"><i class="fa-solid fa-video"></i> Join Meet</a></td>
        <td>${getStatusBadge(r.status)}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="triggerReviewReminder(${r.id}, '24h')">
            24h Reminder
          </button>
          <button class="btn btn-secondary btn-sm" onclick="triggerReviewReminder(${r.id}, '1h')">
            1h Reminder
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {}
}

async function triggerReviewReminder(reviewId, type) {
  try {
    const res = await apiRequest(`/api/reviews/${reviewId}/send-reminder?reminder_type=${type}`, { method: 'POST' });
    showToast(res.message, 'info');
  } catch (err) {}
}

// ==================== EMAIL LOGS & AUDIT TRAIL ====================
async function loadEmailLogs() {
  try {
    const logs = await apiRequest('/api/emails/logs?limit=50');
    const tbody = document.getElementById('emailLogsTableBody');

    if (!logs || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No email logs found.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td>${new Date(l.sent_at).toLocaleTimeString()}</td>
        <td><code>${l.recipient}</code></td>
        <td><span class="badge" style="background:var(--bg-subtle);">${l.email_type}</span></td>
        <td><strong>${l.subject}</strong></td>
        <td><span class="badge ${l.status === 'SENT' ? 'badge-approved' : 'badge-overdue'}">${l.status}</span></td>
        <td style="font-size: 0.75rem; color: var(--text-muted); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${l.error_message ? `<span style="color:var(--danger);">${l.error_message}</span>` : (l.content_preview || '-')}
        </td>
        <td>
          ${l.status === 'FAILED' ? `
            <button class="btn btn-danger btn-sm" onclick="retryEmail(${l.id})">Retry</button>
          ` : '<span style="color:var(--success); font-size:0.75rem;"><i class="fa-solid fa-check"></i> Delivered</span>'}
        </td>
      </tr>
    `).join('');
  } catch (err) {}
}

async function retryEmail(logId) {
  try {
    const res = await apiRequest(`/api/emails/retry/${logId}`, { method: 'POST' });
    showToast(res.message, 'success');
    loadEmailLogs();
  } catch (err) {}
}

async function loadAuditLogs() {
  try {
    const logs = await apiRequest('/api/admin/audit-logs?limit=50');
    const tbody = document.getElementById('auditLogsTableBody');

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td>${new Date(l.timestamp).toLocaleString()}</td>
        <td><strong>${l.action}</strong></td>
        <td>${l.actor_name}</td>
        <td>${l.intern_id ? `#${l.intern_id}` : '-'}</td>
        <td style="font-size: 0.8125rem; color: var(--text-muted);">${l.details || '-'}</td>
      </tr>
    `).join('');
  } catch (err) {}
}

// ==================== INTERN PORTAL VIEW ====================
async function loadInternDashboard() {
  try {
    const data = await apiRequest('/api/intern/dashboard');
    const info = data.intern_info;
    const task = data.assigned_task;

    // Profile card
    document.getElementById('portalInternName').textContent = info.name;
    document.getElementById('portalInternId').textContent = info.intern_id;
    document.getElementById('portalInternDept').textContent = info.department;
    document.getElementById('portalMentorName').textContent = info.mentor_name;
    document.getElementById('portalInternStatusBadge').innerHTML = getStatusBadge(info.status);

    // Corrections card
    const corrCard = document.getElementById('internCorrectionsCard');
    if (info.status === 'Corrections Required') {
      corrCard.style.display = 'block';
      document.getElementById('portalCorrectionChecklist').textContent = info.correction_checklist || 'Review areas for improvement.';
      document.getElementById('portalResubmissionDeadline').textContent = info.resubmission_deadline ? `Resubmit by: ${new Date(info.resubmission_deadline).toLocaleString()}` : 'Resubmit promptly';
      document.getElementById('portalCurrentVersionBadge').textContent = 'Version 2 Resubmission';
    } else {
      corrCard.style.display = 'none';
      document.getElementById('portalCurrentVersionBadge').textContent = `Version ${(data.submissions ? data.submissions.length + 1 : 1)} Upload`;
    }

    // Task card
    if (task) {
      document.getElementById('portalTaskTitle').textContent = task.title;
      document.getElementById('portalTaskDescription').textContent = task.description;
      document.getElementById('portalTaskDeliverables').textContent = task.deliverables;
      document.getElementById('portalTaskDeadlineBadge').textContent = task.deadline ? `Deadline: ${new Date(task.deadline).toLocaleDateString()}` : 'No deadline';

      // Rubric
      const rubricPreview = document.getElementById('portalRubricPreview');
      if (task.rubric && task.rubric.length > 0) {
        rubricPreview.innerHTML = `
          <strong style="font-size: 0.8125rem;">Evaluation Rubric Criteria:</strong>
          <div style="display: grid; gap: 0.5rem; margin-top: 0.5rem;">
            ${task.rubric.map(r => `
              <div style="background: white; border: 1px solid var(--border); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); font-size: 0.8125rem;">
                <strong>${r.requirement}</strong> (${r.max_marks} marks) — <span style="color: var(--text-muted);">${r.description}</span>
              </div>
            `).join('')}
          </div>
        `;
      }
    } else {
      document.getElementById('portalTaskTitle').textContent = 'No Task Assigned';
      document.getElementById('portalTaskDescription').textContent = 'Your mentor has not assigned a task to your account yet.';
    }

    // Submissions history
    const historyList = document.getElementById('internSubmissionsHistoryList');
    if (data.submissions && data.submissions.length > 0) {
      historyList.innerHTML = data.submissions.map(s => `
        <div style="border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <strong>Version ${s.version} — ${s.file_name} (${Math.round(s.file_size / 1024)} KB)</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${new Date(s.submitted_at).toLocaleString()}</span>
          </div>
          ${s.evaluation ? `
            <div style="background: var(--bg-subtle); padding: 0.75rem; border-radius: var(--radius-sm); font-size: 0.8125rem;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
                <span><strong>AI Completion:</strong> ${s.evaluation.completion_percentage}% | <strong>Score:</strong> ${s.evaluation.overall_score}/${s.evaluation.max_score}</span>
                <span class="badge ${s.evaluation.mentor_approved ? 'badge-approved' : 'badge-eval-pending'}">
                  ${s.evaluation.mentor_approved ? 'Mentor Approved' : 'Provisional AI Evaluation'}
                </span>
              </div>
              <p><strong>Mentor Feedback:</strong> ${s.evaluation.mentor_notes || 'Pending mentor review.'}</p>
            </div>
          ` : '<p style="font-size: 0.75rem; color: var(--text-muted);">AI Evaluation Pending...</p>'}
        </div>
      `).join('');
    } else {
      historyList.innerHTML = `<p style="font-size: 0.875rem; color: var(--text-muted);">No submissions recorded yet.</p>`;
    }

    // Review meeting card
    const reviewBox = document.getElementById('portalReviewDetailsContent');
    if (data.reviews && data.reviews.length > 0) {
      const rev = data.reviews[0];
      reviewBox.innerHTML = `
        <div style="background: var(--bg-subtle); padding: 1rem; border-radius: var(--radius-md); font-size: 0.875rem;">
          <div><strong>Date:</strong> ${rev.review_date}</div>
          <div><strong>Time:</strong> ${rev.start_time} - ${rev.end_time} (${rev.timezone})</div>
          <div style="margin-top: 0.75rem; text-align: center;">
            <a href="${rev.google_meet_link}" target="_blank" class="btn btn-success" style="width: 100%;">
              <i class="fa-solid fa-video"></i> Join Google Meet Review
            </a>
          </div>
        </div>
      `;
    } else {
      reviewBox.innerHTML = `<p style="font-size: 0.875rem; color: var(--text-muted);">No upcoming review scheduled yet.</p>`;
    }
  } catch (err) {}
}

let selectedSubmissionFile = null;
function handleFileSelect(input) {
  if (input.files && input.files[0]) {
    selectedSubmissionFile = input.files[0];
    document.getElementById('selectedFileName').textContent = `Selected: ${selectedSubmissionFile.name} (${Math.round(selectedSubmissionFile.size / 1024)} KB)`;
  }
}

async function handleSubmissionUpload(e) {
  e.preventDefault();
  if (!selectedSubmissionFile) {
    showToast('Please select a file to submit.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedSubmissionFile);
  const notes = document.getElementById('submissionNotesInput').value;
  if (notes) formData.append('description', notes);

  const btn = document.getElementById('btnSubmitDeliverable');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Parsing Document & Running AI Evaluation...`;

  try {
    const res = await apiRequest('/api/intern/submit', {
      method: 'POST',
      body: formData
    });

    showToast(`Submission (Version ${res.version}) processed! AI Score: ${res.ai_provisional_report.overall_score} marks (${res.ai_provisional_report.completion_percentage}%).`, 'success');
    document.getElementById('submissionUploadForm').reset();
    document.getElementById('selectedFileName').textContent = 'Drag and drop deliverable file, or click to browse';
    selectedSubmissionFile = null;
    loadInternDashboard();
  } catch (err) {} finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Submit Deliverables for AI Verification`;
  }
}

// ==================== AI CHATBOT ====================
function toggleChatbot() {
  document.getElementById('chatbotPanel').classList.toggle('open');
}

function askQuickChip(question) {
  document.getElementById('chatInput').value = question;
  handleSendChatMessage();
}

async function handleSendChatMessage(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('chatInput');
  const question = input.value.trim();
  if (!question) return;

  // Append user bubble
  appendChatBubble(question, 'user');
  input.value = '';

  // Append typing bubble
  const typingId = appendChatBubble('<i class="fa-solid fa-ellipsis fa-fade"></i> Checking your internship records...', 'assistant');

  try {
    const res = await apiRequest('/api/chat/ask', {
      method: 'POST',
      body: JSON.stringify({ question })
    });

    // Replace typing bubble
    const typingBubble = document.getElementById(typingId);
    if (typingBubble) {
      typingBubble.innerHTML = res.answer.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
  } catch (err) {
    const typingBubble = document.getElementById(typingId);
    if (typingBubble) {
      typingBubble.textContent = 'Sorry, I encountered an issue retrieving your records.';
    }
  }
}

function appendChatBubble(content, sender) {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  const id = `bubble-${Date.now()}`;
  div.id = id;
  div.className = `chat-bubble ${sender}`;
  div.innerHTML = content;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
  loginPersona('admin');
});
