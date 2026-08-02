# pyrefly: ignore [missing-import]
from ..services.language_registry import LANGUAGE_REGISTRY


def get_instructor_dashboard_html(id_token: str, exams: list):
    options_html = ""
    for exam in exams:
        options_html += f'<option value="{exam.exam_id}">{exam.title} (Duration: {exam.duration}m)</option>'

    language_options_html = ""
    language_labels = {
        "python": "Python",
        "javascript": "JavaScript",
        "c": "C",
        "cpp": "C++",
    }
    for language_key in LANGUAGE_REGISTRY.keys():
        label = language_labels.get(language_key, language_key.capitalize())
        language_options_html += f'<option value="{language_key}">{label}</option>'

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ProctorIDE Lecturer Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
        window.addEventListener("load", () => {{
            try {{
                const parentDoc = window.parent.document;

                const dialog = parentDoc.querySelector(".modal-dialog");
                if (dialog) {{
                    dialog.style.maxWidth = "95vw";
                    dialog.style.width = "95vw";
                }}

                const content = parentDoc.querySelector(".modal-content");
                if (content) {{
                    content.style.height = "90vh";
                }}

                const body = parentDoc.querySelector(".modal-body");
                if (body) {{
                    body.style.maxHeight = "85vh";
                    body.style.height = "85vh";
                }}

                if (window.frameElement) {{
                    window.frameElement.style.height = "100%";
                    window.frameElement.style.minHeight = "80vh";
                }} else {{
                    const iframe = parentDoc.querySelector("iframe");
                    if (iframe) {{
                        iframe.style.height = "100%";
                        iframe.style.minHeight = "80vh";
                    }}
                }}
            }} catch (e) {{
                console.log("Unable to resize Moodle modal:", e);
            }}
        }});

        let currentExamId = null;
        let currentQuestionId = null;
        let currentEditingQuestion = null;
        let currentRuleDefinitions = [];
        let rulesCache = {{}};
        let confirmModalCallback = null;
        let allExamsList = [];
        let activeStatusFilter = 'all';
        let searchQuery = '';

        function showToast(message, type = 'success') {{
            const toast = document.getElementById('toast-notification');
            const toastMsg = document.getElementById('toast-message');
            toastMsg.innerText = message;
            
            toast.className = `fixed bottom-5 right-5 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium z-50 transition-all duration-300 transform translate-y-0 ${{
                type === 'success' ? 'bg-emerald-600' : 'bg-red-600'
                }}`;

                setTimeout(() => {{
                    toast.className = 'fixed bottom-5 right-5 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium z-50 transition-all duration-300 transform translate-y-20 opacity-0 pointer-events-none';
                }}, 3500);
            }}

            function showLinkingOverlay(message) {{
                const overlay = document.getElementById('linking-overlay');
                document.getElementById('linking-overlay-msg').innerText = message;
                overlay.classList.remove('hidden');
            }}

            function showConfirmModal(title, message, onConfirm) {{
                document.getElementById('confirm-modal-title').innerText = title;
                document.getElementById('confirm-modal-message').innerText = message;
                confirmModalCallback = onConfirm;
                document.getElementById('confirm-modal').classList.remove('hidden');
            }}

            function closeConfirmModal() {{
                document.getElementById('confirm-modal').classList.add('hidden');
                confirmModalCallback = null;
            }}

            document.addEventListener('DOMContentLoaded', () => {{
                document.getElementById('confirm-modal-btn-confirm').addEventListener('click', () => {{
                    if (confirmModalCallback) confirmModalCallback();
                    closeConfirmModal();
                }});
            }});

            function showTab(tabId) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
                document.getElementById(tabId).classList.remove('hidden');
                
                document.querySelectorAll('.tab-btn').forEach(el => {{
                    el.classList.remove('border-blue-500', 'text-blue-600');
                    el.classList.add('border-transparent', 'text-gray-500');
                }});
                const activeBtn = document.getElementById('btn-' + tabId);
                if (activeBtn) {{
                    activeBtn.classList.remove('border-transparent', 'text-gray-500');
                    activeBtn.classList.add('border-blue-500', 'text-blue-600');
                }}

                if (tabId === 'tab-exams') {{
                    fetchExams();
                }}
            }}

            function escapeHtml(value) {{
                return String(value ?? "")
                    .replaceAll("&", "&amp;")
                    .replaceAll("<", "&lt;")
                    .replaceAll(">", "&gt;")
                    .replaceAll('"', "&quot;")
                    .replaceAll("'", "&#039;");
            }}

            // ================= 1. EXAM LISTING & SEARCH & FILTER =================

            async function fetchExams() {{
                const container = document.getElementById('exams-grid');
                container.innerHTML = '<div class="col-span-2 text-center py-8 text-gray-500">Loading examinations...</div>';

                try {{
                    const res = await fetch('/lti/exams');
                    if (!res.ok) throw new Error('Failed to load examinations');
                    allExamsList = await res.json();
                    renderExamsGrid();
                }} catch (err) {{
                    container.innerHTML = `<div class="col-span-2 text-center py-8 text-red-600">Error: ${{escapeHtml(err.message)}}</div>`;
                }}
            }}

            function setStatusFilter(status, btnEl) {{
                activeStatusFilter = status;
                document.querySelectorAll('.filter-pill').forEach(el => {{
                    el.classList.remove('bg-blue-600', 'text-white', 'font-semibold');
                    el.classList.add('bg-gray-100', 'text-gray-600', 'hover:bg-gray-200');
                }});
                btnEl.classList.remove('bg-gray-100', 'text-gray-600', 'hover:bg-gray-200');
                btnEl.classList.add('bg-blue-600', 'text-white', 'font-semibold');
                renderExamsGrid();
            }}

            function onSearchInput(val) {{
                searchQuery = (val || '').toLowerCase().trim();
                renderExamsGrid();
            }}

            function renderExamsGrid() {{
                const container = document.getElementById('exams-grid');
                
                let filtered = allExamsList.filter(exam => {{
                    const isPublished = exam.published !== false;
                    if (activeStatusFilter === 'published' && !isPublished) return false;
                    if (activeStatusFilter === 'draft' && isPublished) return false;

                    if (searchQuery) {{
                        const title = (exam.title || '').toLowerCase();
                        const desc = (exam.description || '').toLowerCase();
                        const lang = (exam.language || '').toLowerCase();
                        return title.includes(searchQuery) || desc.includes(searchQuery) || lang.includes(searchQuery);
                    }}

                    return true;
                }});

                if (!allExamsList.length) {{
                    container.innerHTML = `
                        <div class="col-span-2 text-center py-12 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                            <p class="text-base font-semibold text-gray-700 mb-1">No examinations created yet</p>
                            <p class="text-xs text-gray-500 mb-4">Create your first programming examination to get started.</p>
                            <button type="button" onclick="openNewExamWizard()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm">
                                + New Examination
                            </button>
                        </div>
                    `;
                    return;
                }}

                if (!filtered.length) {{
                    container.innerHTML = `
                        <div class="col-span-2 text-center py-10 border border-gray-200 rounded-xl bg-white">
                            <p class="text-sm font-semibold text-gray-700 mb-1">No examinations match your search</p>
                            <p class="text-xs text-gray-500">Try adjusting your search query or filter selection.</p>
                        </div>
                    `;
                    return;
                }}

                container.innerHTML = filtered.map(exam => {{
                    const isPublished = exam.published !== false;
                    const badgeClass = isPublished ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : 'bg-amber-100 text-amber-800 border-amber-200';
                    const badgeText = isPublished ? 'Published' : 'Draft';

                    const useBtnDisabled = !isPublished;
                    const useBtnClass = useBtnDisabled 
                        ? 'bg-emerald-100 text-emerald-400 cursor-not-allowed opacity-60' 
                        : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs';
                    const useBtnTitle = useBtnDisabled ? 'Publish this examination before using it for a course.' : 'Use this examination for the active Moodle course activity';

                    return `
                        <div class="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition p-5 flex flex-col justify-between" id="exam-card-${{exam.exam_id}}">
                            <div>
                                <div class="flex items-start justify-between gap-2 mb-2">
                                    <h3 class="font-bold text-lg text-gray-900 line-clamp-1">${{escapeHtml(exam.title)}}</h3>
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${{badgeClass}}">
                                        ${{badgeText}}
                                    </span>
                                </div>
                                <p class="text-xs text-gray-500 mb-4 line-clamp-2">${{escapeHtml(exam.description || 'No description provided.')}}</p>
                                
                                <div class="flex items-center gap-4 text-xs text-gray-600 bg-gray-50 p-2.5 rounded-lg border border-gray-100 mb-4">
                                    <div>⏱ <b>${{exam.duration}}</b> minutes</div>
                                    <div>📝 <b>${{exam.question_count}}</b> questions</div>
                                    <div>💻 <b>${{escapeHtml((exam.language || 'python').toUpperCase())}}</b></div>
                                </div>
                            </div>

                            <div class="flex items-center gap-2 pt-3 border-t border-gray-100 flex-wrap">
                                <button type="button" onclick="openEditExamModal(${{exam.exam_id}})" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                                    Edit Exam
                                </button>
                                <button type="button" onclick="openQuestionManager(${{exam.exam_id}}, '${{escapeHtml(exam.title)}}')" class="flex-1 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                                    Manage Questions
                                </button>
                                <button type="button" onclick="togglePublishExam(${{exam.exam_id}}, ${{!isPublished}})" class="bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                                    ${{isPublished ? 'Unpublish' : 'Publish'}}
                                </button>
                                <button type="button" ${{useBtnDisabled ? 'disabled' : ''}} title="${{useBtnTitle}}" onclick="useExamForCourse(${{exam.exam_id}})" class="btn-use-exam text-xs font-semibold py-2 px-3 rounded-md transition text-center ${{useBtnClass}}">
                                    Use for This Course
                                </button>
                                <button type="button" onclick="promptDeleteExam(${{exam.exam_id}}, '${{escapeHtml(exam.title)}}')" class="btn-delete-exam bg-red-50 hover:bg-red-100 text-red-600 text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                                    Delete
                                </button>
                            </div>
                        </div>
                    `;
                }}).join('');
            }}

            function useExamForCourse(examId) {{
                showLinkingOverlay("✓ Examination linked successfully. Returning to Moodle...");
                document.getElementById('deep-link-exam-id').value = examId;
                setTimeout(() => {{
                    document.getElementById('deep-link-auto-form').submit();
                }}, 600);
            }}

            function openNewExamWizard() {{
                document.getElementById('create-exam-form').reset();
                document.getElementById('new-exam-modal').classList.remove('hidden');
            }}

            function closeNewExamModal() {{
                document.getElementById('new-exam-modal').classList.add('hidden');
            }}

            async function createNewExam(e) {{
                e.preventDefault();
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.innerText = "Creating...";

                const payload = {{
                    title: document.getElementById('create-exam-title').value.trim(),
                    description: document.getElementById('create-exam-description').value.trim(),
                    duration: parseInt(document.getElementById('create-exam-duration').value),
                    language: document.getElementById('create-exam-language').value
                }};

                try {{
                    const res = await fetch('/api/launch/api/exam', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(payload)
                    }});
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Failed to create examination');

                    showToast('Examination created successfully!');
                    closeNewExamModal();
                    
                    // Transition straight to question manager for the new exam
                    openQuestionManager(data.exam_id, data.title);
                }} catch (err) {{
                    showToast(err.message, 'error');
                }} finally {{
                    btn.disabled = false;
                    btn.innerText = "Create Examination";
                }}
            }}

            function promptDeleteExam(examId, title) {{
                showConfirmModal(
                    "Delete Examination",
                    `Are you sure you want to permanently delete "${{title}}"?\n\nThis will permanently remove:\n✓ Examination Metadata\n✓ All Programming Questions\n✓ All Static Grading Rules\n✓ All Test Cases\n\nThis action cannot be undone.`,
                    async () => {{
                        const card = document.getElementById('exam-card-' + examId);
                        if (card) {{
                            const deleteBtn = card.querySelector('.btn-delete-exam');
                            if (deleteBtn) {{
                                deleteBtn.disabled = true;
                                deleteBtn.innerText = 'Deleting...';
                            }}
                        }}

                        try {{
                            const res = await fetch('/lti/exams/' + examId, {{ method: 'DELETE' }});
                            if (res.status === 204 || res.ok) {{
                                showToast('Exam deleted successfully.');
                                if (card) {{
                                    card.classList.add('opacity-0', 'scale-95', 'transition-all', 'duration-300');
                                    setTimeout(() => {{
                                        allExamsList = allExamsList.filter(e => e.exam_id !== examId);
                                        renderExamsGrid();
                                    }}, 300);
                                }}
                            }} else {{
                                const data = await res.json().catch(() => ({{}}));
                                throw new Error(data.detail || 'Failed to delete examination.');
                            }}
                        }} catch (err) {{
                            showToast(err.message, 'error');
                            if (card) {{
                                const deleteBtn = card.querySelector('.btn-delete-exam');
                                if (deleteBtn) {{
                                    deleteBtn.disabled = false;
                                    deleteBtn.innerText = 'Delete';
                                }}
                            }}
                        }}
                    }}
                );
            }}

            async function openEditExamModal(examId) {{
                try {{
                    const res = await fetch('/lti/exams/' + examId);
                    if (!res.ok) throw new Error('Failed to load exam details');
                    const exam = await res.json();

                    document.getElementById('edit-exam-id').value = exam.exam_id;
                    document.getElementById('edit-exam-title').value = exam.title;
                    document.getElementById('edit-exam-description').value = exam.description || '';
                    document.getElementById('edit-exam-duration').value = exam.duration;
                    document.getElementById('edit-exam-published').checked = exam.published !== false;

                    document.getElementById('edit-exam-modal').classList.remove('hidden');
                }} catch (err) {{
                    showToast(err.message, 'error');
                }}
            }}

            function closeEditExamModal() {{
                document.getElementById('edit-exam-modal').classList.add('hidden');
            }}

            async function saveExamEdits(e) {{
                e.preventDefault();
                const examId = document.getElementById('edit-exam-id').value;
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.innerText = "Saving...";

                const payload = {{
                    title: document.getElementById('edit-exam-title').value.trim(),
                    description: document.getElementById('edit-exam-description').value.trim(),
                    duration: parseInt(document.getElementById('edit-exam-duration').value),
                    published: document.getElementById('edit-exam-published').checked
                }};

                try {{
                    const res = await fetch('/lti/exams/' + examId, {{
                        method: 'PUT',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(payload)
                    }});
                    const result = await res.json();

                    if (!res.ok) {{
                        throw new Error(result.detail || 'Failed to update exam');
                    }}

                    showToast('Exam updated successfully!');
                    closeEditExamModal();
                    fetchExams();
                }} catch (err) {{
                    showToast(err.message, 'error');
                }} finally {{
                    btn.disabled = false;
                    btn.innerText = "Save Changes";
                }}
            }}

            async function togglePublishExam(examId, targetState) {{
                try {{
                    const resFetch = await fetch('/lti/exams/' + examId);
                    if (!resFetch.ok) throw new Error('Failed to load exam');
                    const exam = await resFetch.json();

                    const res = await fetch('/lti/exams/' + examId, {{
                        method: 'PUT',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            title: exam.title,
                            description: exam.description,
                            duration: exam.duration,
                            published: targetState
                        }})
                    }});
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Unable to update publish state');

                    showToast(targetState ? 'Exam published successfully!' : 'Exam set to draft status.');
                    fetchExams();
                }} catch (err) {{
                    showToast(err.message, 'error');
                }}
            }}

            // ================= 2. QUESTION MANAGER =================

            async function openQuestionManager(examId, examTitle) {{
                currentExamId = examId;
                document.getElementById('qm-exam-title').innerText = "Questions for: " + (examTitle || "Exam " + examId);
                
                document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
                document.getElementById('panel-question-manager').classList.remove('hidden');

                fetchQuestionsList();
            }}

            function backToExamsList() {{
                document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
                document.getElementById('panel-exams-list').classList.remove('hidden');
                fetchExams();
            }}

            async function fetchQuestionsList() {{
                const list = document.getElementById('questions-list-container');
                list.innerHTML = '<div class="text-center py-8 text-gray-500">Loading questions...</div>';

                try {{
                    const res = await fetch('/lti/exams/' + currentExamId);
                    if (!res.ok) throw new Error('Failed to load questions');
                    const exam = await res.json();
                    const questions = exam.questions || [];

                    if (!questions.length) {{
                        list.innerHTML = `
                            <div class="text-center py-10 border-2 border-dashed border-gray-200 rounded-xl">
                                <p class="text-sm text-gray-500 mb-3">No questions created for this exam yet.</p>
                                <button type="button" onclick="openNewQuestionForm()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2 rounded-md">
                                    + Add First Question
                                </button>
                            </div>
                        `;
                        return;
                    }}

                    list.innerHTML = questions.map((q, idx) => `
                        <div class="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between shadow-sm hover:shadow transition">
                            <div class="flex items-center gap-3">
                                <span class="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold text-sm flex items-center justify-center">${{idx + 1}}</span>
                                <div>
                                    <h4 class="font-bold text-gray-800 text-base">${{escapeHtml(q.title)}}</h4>
                                    <div class="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                                        <span>💻 ${{escapeHtml((q.language || 'python').toUpperCase())}}</span>
                                        <span>•</span>
                                        <span>Functional: ${{q.functional_weight}}% / Static: ${{q.static_weight}}%</span>
                                        <span>•</span>
                                        <span>Diff: ${{q.diff_level || 1}}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" onclick="editQuestion(${{q.question_id}})" class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium text-xs px-3 py-1.5 rounded-md transition">
                                    Edit
                                </button>
                                <button type="button" onclick="promptDeleteQuestion(${{q.question_id}}, '${{escapeHtml(q.title)}}')" class="bg-red-50 hover:bg-red-100 text-red-600 font-medium text-xs px-3 py-1.5 rounded-md transition">
                                    Delete
                                </button>
                            </div>
                        </div>
                    `).join('');
                }} catch (err) {{
                    list.innerHTML = `<div class="text-center py-6 text-red-600">Error loading questions: ${{escapeHtml(err.message)}}</div>`;
                }}
            }}

            function promptDeleteQuestion(questionId, title) {{
                showConfirmModal(
                    "Delete Question?",
                    `Are you sure you want to delete "${{title}}"? This will delete all rules and test cases associated with it. This action cannot be undone.`,
                    async () => {{
                        try {{
                            const res = await fetch('/lti/questions/' + questionId, {{ method: 'DELETE' }});
                            if (!res.ok) throw new Error('Failed to delete question');
                            showToast('Question deleted successfully');
                            fetchQuestionsList();
                        }} catch (err) {{
                            showToast(err.message, 'error');
                        }}
                    }}
                );
            }}

            // ================= 3. QUESTION & TESTCASE EDITOR =================

            function openNewQuestionForm() {{
                currentQuestionId = null;
                currentEditingQuestion = null;
                
                document.getElementById('q-editor-title').innerText = "Create New Question";
                document.getElementById('form-question').reset();
                document.getElementById('q-id-hidden').value = "";
                document.getElementById('testcases-section').classList.add('hidden');

                document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
                document.getElementById('panel-question-editor').classList.remove('hidden');

                loadStaticRules('python');
            }}

            async function editQuestion(questionId) {{
                try {{
                    const res = await fetch('/lti/questions/' + questionId);
                    if (!res.ok) throw new Error('Failed to load question details');
                    const q = await res.json();

                    currentQuestionId = q.question_id;
                    currentEditingQuestion = q;

                    document.getElementById('q-editor-title').innerText = "Edit Question: " + q.title;
                    document.getElementById('q-id-hidden').value = q.question_id;
                    document.getElementById('q-title').value = q.title;
                    document.getElementById('q-description').value = q.description;
                    document.getElementById('q-diff').value = q.diff_level || 1;
                    document.getElementById('q-language').value = q.language || 'python';
                    document.getElementById('q-functional-weight').value = q.functional_weight;
                    document.getElementById('q-static-weight').value = q.static_weight;
                    document.getElementById('q-default-code').value = q.default_code || '';

                    loadStaticRules(q.language || 'python', q.static_rules || []);
                    renderTestCases(q.test_cases || []);

                    document.getElementById('testcases-section').classList.remove('hidden');

                    document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
                    document.getElementById('panel-question-editor').classList.remove('hidden');
                }} catch (err) {{
                    showToast(err.message, 'error');
                }}
            }}

            function backToQuestionManager() {{
                document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
                document.getElementById('panel-question-manager').classList.remove('hidden');
                fetchQuestionsList();
            }}

            async function loadStaticRules(language, existingRules = []) {{
                const panel = document.getElementById('static-rules-panel');
                panel.innerHTML = '<div class="text-xs text-gray-500">Loading static analysis rules...</div>';

                try {{
                    let rules = rulesCache[language];
                    if (!rules) {{
                        const res = await fetch('/grading/rules/' + encodeURIComponent(language));
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || 'Failed to load rules');
                        rules = data.rules || [];
                        rulesCache[language] = rules;
                    }}
                    currentRuleDefinitions = rules;
                    renderStaticRules(rules, existingRules);
                }} catch (err) {{
                    panel.innerHTML = `<div class="text-xs text-red-600">Could not load rules: ${{escapeHtml(err.message)}}</div>`;
                }}
            }}

            function renderStaticRules(ruleDefs, existingRules = []) {{
                const panel = document.getElementById('static-rules-panel');

                if (!ruleDefs.length) {{
                    panel.innerHTML = '<div class="text-xs text-gray-500 italic">No static rules available for this language.</div>';
                    return;
                }}

                const existingMap = {{}};
                existingRules.forEach(r => {{ existingMap[r.rule_type] = r; }});

                panel.innerHTML = ruleDefs.map(rule => {{
                    const ruleType = escapeHtml(rule.rule_type);
                    const label = escapeHtml(rule.label || rule.rule_type);
                    const desc = escapeHtml(rule.description || '');
                    const existing = existingMap[rule.rule_type];

                    const isChecked = Boolean(existing);
                    const ruleId = existing ? existing.rule_id : '';
                    const val = existing ? (existing.expected_value ?? '') : '';
                    const weight = existing ? existing.weight : (rule.default_weight || 1.0);

                    let valInput = '';
                    if (rule.input_type === 'text') {{
                        valInput = `<input type="text" data-rule-value="${{ruleType}}" value="${{escapeHtml(val)}}" placeholder="e.g. factorial" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-xs">`;
                    }} else if (rule.input_type === 'number') {{
                        valInput = `<input type="number" data-rule-value="${{ruleType}}" value="${{escapeHtml(val)}}" placeholder="e.g. 2" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-xs">`;
                    }} else if (rule.input_type === 'boolean') {{
                        valInput = `
                            <select data-rule-value="${{ruleType}}" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-xs">
                                <option value="true" ${{val === 'true' || val === true ? 'selected' : ''}}>Required</option>
                                <option value="false" ${{val === 'false' || val === false ? 'selected' : ''}}>Forbidden</option>
                            </select>
                        `;
                    }}

                    return `
                        <div class="border border-gray-200 rounded p-2.5 bg-white shadow-xs">
                            <input type="hidden" data-rule-id="${{ruleType}}" value="${{ruleId}}">
                            <label class="flex items-start gap-2 cursor-pointer">
                                <input type="checkbox" data-rule-enabled="${{ruleType}}" ${{isChecked ? 'checked' : ''}} class="mt-0.5 rounded text-blue-600">
                                <div>
                                    <span class="block text-xs font-bold text-gray-800">${{label}}</span>
                                    <span class="block text-xs text-gray-500">${{desc}}</span>
                                </div>
                            </label>
                            <div class="grid grid-cols-2 gap-2 mt-2">
                                <div>
                                    <label class="block text-xs font-medium text-gray-500">Expected Value</label>
                                    ${{valInput || '<span class="text-xs text-gray-400 font-mono">—</span>'}}
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-500">Weight</label>
                                    <input type="number" step="0.1" min="0" data-rule-weight="${{ruleType}}" value="${{weight}}" class="mt-1 block w-full px-2 py-1 border border-gray-300 rounded text-xs">
                                </div>
                            </div>
                        </div>
                    `;
                }}).join('');
            }}

            function collectStaticRules() {{
                const selected = [];
                for (const rule of currentRuleDefinitions) {{
                    const ruleType = rule.rule_type;
                    const enabled = document.querySelector(`[data-rule-enabled="${{ruleType}}"]`)?.checked;
                    if (!enabled) continue;

                    const ruleIdEl = document.querySelector(`[data-rule-id="${{ruleType}}"]`);
                    const valEl = document.querySelector(`[data-rule-value="${{ruleType}}"]`);
                    const weightEl = document.querySelector(`[data-rule-weight="${{ruleType}}"]`);

                    const expectedValue = valEl ? String(valEl.value || '').trim() : '';
                    const weight = parseFloat(weightEl?.value || rule.default_weight || 1.0);
                    const ruleId = ruleIdEl && ruleIdEl.value ? parseInt(ruleIdEl.value) : null;

                    if ((rule.input_type === 'text' || rule.input_type === 'number') && !expectedValue) {{
                        throw new Error(`Please specify expected value for "${{rule.label || ruleType}}".`);
                    }}

                    if (isNaN(weight) || weight < 0) {{
                        throw new Error(`Weight for "${{rule.label || ruleType}}" must be a non-negative number.`);
                    }}

                    const item = {{
                        rule_type: ruleType,
                        expected_value: expectedValue,
                        weight: weight,
                        required: true
                    }};
                    if (ruleId) item.rule_id = ruleId;
                    selected.push(item);
                }}
                return selected;
            }}

            async function saveQuestion(e) {{
                e.preventDefault();
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.innerText = "Saving Question...";

                const title = document.getElementById('q-title').value.trim();
                const description = document.getElementById('q-description').value.trim();
                const diff_level = parseInt(document.getElementById('q-diff').value);
                const language = document.getElementById('q-language').value;
                const functional_weight = parseFloat(document.getElementById('q-functional-weight').value);
                const static_weight = parseFloat(document.getElementById('q-static-weight').value);
                const default_code = document.getElementById('q-default-code').value;

                if (!title) {{
                    showToast('Question title is required.', 'error');
                    btn.disabled = false;
                    btn.innerText = "Save Question";
                    return;
                }}

                if (isNaN(functional_weight) || isNaN(static_weight) || functional_weight < 0 || static_weight < 0) {{
                    showToast('Grading weights must be non-negative numbers.', 'error');
                    btn.disabled = false;
                    btn.innerText = "Save Question";
                    return;
                }}

                if (Math.abs((functional_weight + static_weight) - 100) > 0.001) {{
                    showToast('Functional and static weights must sum up to 100.', 'error');
                    btn.disabled = false;
                    btn.innerText = "Save Question";
                    return;
                }}

                let static_rules = [];
                try {{
                    static_rules = collectStaticRules();
                }} catch (valErr) {{
                    showToast(valErr.message, 'error');
                    btn.disabled = false;
                    btn.innerText = "Save Question";
                    return;
                }}

                const payload = {{
                    title,
                    description,
                    diff_level,
                    language,
                    functional_weight,
                    static_weight,
                    default_code,
                    static_rules
                }};

                try {{
                    let res, data;
                    if (currentQuestionId) {{
                        res = await fetch('/lti/questions/' + currentQuestionId, {{
                            method: 'PUT',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(payload)
                        }});
                    }} else {{
                        payload.exam_id = currentExamId;
                        res = await fetch('/api/launch/api/question', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(payload)
                        }});
                    }}

                    data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Failed to save question');

                    showToast('Question saved successfully!');
                    currentQuestionId = data.question_id;
                    document.getElementById('q-id-hidden').value = data.question_id;
                    document.getElementById('testcases-section').classList.remove('hidden');
                    
                    if (data.test_cases) renderTestCases(data.test_cases);
                }} catch (err) {{
                    showToast(err.message, 'error');
                }} finally {{
                    btn.disabled = false;
                    btn.innerText = "Save Question";
                }}
            }}

            // ================= TEST CASE MANAGEMENT =================

            function renderTestCases(testCases = []) {{
                const list = document.getElementById('testcases-list');
                if (!testCases.length) {{
                    list.innerHTML = '<div class="text-xs text-gray-500 italic p-3 bg-gray-50 border border-gray-200 rounded">No test cases added yet.</div>';
                    return;
                }}

                list.innerHTML = testCases.map((tc, i) => `
                    <div class="bg-white border border-gray-200 rounded-lg p-3 flex items-start justify-between shadow-xs">
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <span class="font-bold text-xs text-gray-700">Test Case #${{i + 1}}</span>
                                <span class="text-xs px-2 py-0.5 rounded font-semibold ${{tc.is_hidden ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}}">
                                    ${{tc.is_hidden ? 'Hidden' : 'Public'}}
                                </span>
                                <span class="text-xs text-gray-500 font-mono">Weight: ${{tc.weight || 1.0}}</span>
                            </div>
                            <div class="grid grid-cols-2 gap-3 text-xs font-mono bg-gray-50 p-2 rounded border border-gray-100">
                                <div><b class="text-gray-500 font-sans">IN:</b> ${{escapeHtml(tc.input_data)}}</div>
                                <div><b class="text-gray-500 font-sans">OUT:</b> ${{escapeHtml(tc.expected_output)}}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 shrink-0 ml-3">
                            <button type="button" onclick="openTestCaseModal(${{tc.test_case_id}}, '${{escapeHtml(tc.input_data)}}', '${{escapeHtml(tc.expected_output)}}', ${{tc.is_hidden}}, ${{tc.weight || 1.0}})" class="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded font-medium">Edit</button>
                            <button type="button" onclick="promptDeleteTestCase(${{tc.test_case_id}})" class="text-xs px-2 py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded font-medium">Delete</button>
                        </div>
                    </div>
                `).join('');
            }}

            function openTestCaseModal(tcId = null, inputData = '', expectedOutput = '', isHidden = true, weight = 1.0) {{
                document.getElementById('tc-modal-id').value = tcId || '';
                document.getElementById('tc-modal-input').value = inputData;
                document.getElementById('tc-modal-output').value = expectedOutput;
                document.getElementById('tc-modal-hidden').checked = isHidden;
                document.getElementById('tc-modal-weight').value = weight;
                document.getElementById('tc-modal-title').innerText = tcId ? 'Edit Test Case' : 'Add Test Case';

                document.getElementById('testcase-modal').classList.remove('hidden');
            }}

            function closeTestCaseModal() {{
                document.getElementById('testcase-modal').classList.add('hidden');
            }}

            async function saveTestCaseModal(e) {{
                e.preventDefault();
                const tcId = document.getElementById('tc-modal-id').value;
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;

                const payload = {{
                    input_data: document.getElementById('tc-modal-input').value,
                    expected_output: document.getElementById('tc-modal-output').value,
                    is_hidden: document.getElementById('tc-modal-hidden').checked,
                    weight: parseFloat(document.getElementById('tc-modal-weight').value || 1.0)
                }};

                try {{
                    let res;
                    if (tcId) {{
                        res = await fetch('/lti/testcases/' + tcId, {{
                            method: 'PUT',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(payload)
                        }});
                    }} else {{
                        payload.question_id = currentQuestionId;
                        res = await fetch('/lti/testcases', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(payload)
                        }});
                    }}
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Failed to save test case');

                    showToast('Test case saved successfully!');
                    closeTestCaseModal();
                    refreshCurrentQuestionTestCases();
                }} catch (err) {{
                    showToast(err.message, 'error');
                }} finally {{
                    btn.disabled = false;
                }}
            }}

            function promptDeleteTestCase(tcId) {{
                showConfirmModal(
                    "Delete Test Case?",
                    "Are you sure you want to delete this test case?",
                    async () => {{
                        try {{
                            const res = await fetch('/lti/testcases/' + tcId, {{ method: 'DELETE' }});
                            if (!res.ok) throw new Error('Failed to delete test case');
                            showToast('Test case deleted');
                            refreshCurrentQuestionTestCases();
                        }} catch (err) {{
                            showToast(err.message, 'error');
                        }}
                    }}
                );
            }}

            async function refreshCurrentQuestionTestCases() {{
                if (!currentQuestionId) return;
                try {{
                    const res = await fetch('/lti/questions/' + currentQuestionId);
                    if (res.ok) {{
                        const q = await res.json();
                        renderTestCases(q.test_cases || []);
                    }}
                }} catch (err) {{ console.error(err); }}
            }}
        </script>
    </head>
    <body class="bg-slate-50 min-h-screen font-sans text-gray-900">
        <!-- Toast Notification Container -->
        <div id="toast-notification" class="fixed bottom-5 right-5 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium z-50 transition-all duration-300 transform translate-y-20 opacity-0 pointer-events-none">
            <span id="toast-message">Notification</span>
        </div>

        <!-- Linking Overlay Banner -->
        <div id="linking-overlay" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 hidden">
            <div class="bg-white rounded-2xl p-8 max-w-sm text-center shadow-2xl space-y-3">
                <div class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto font-bold text-xl">✓</div>
                <h3 class="font-bold text-lg text-gray-900">Linking Examination</h3>
                <p id="linking-overlay-msg" class="text-xs text-gray-600">Returning to Moodle...</p>
            </div>
        </div>

        <!-- Confirm Modal -->
        <div id="confirm-modal" class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 hidden">
            <div class="bg-white rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4 border border-gray-200">
                <h3 id="confirm-modal-title" class="font-bold text-lg text-gray-900 mb-2">Confirm Action</h3>
                <p id="confirm-modal-message" class="text-sm text-gray-600 mb-6 whitespace-pre-line">Are you sure?</p>
                <div class="flex justify-end gap-3">
                    <button type="button" onclick="closeConfirmModal()" class="px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md">Cancel</button>
                    <button type="button" id="confirm-modal-btn-confirm" class="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md">Confirm</button>
                </div>
            </div>
        </div>

        <!-- New Exam Wizard Modal -->
        <div id="new-exam-modal" class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 hidden">
            <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 border border-gray-200">
                <h3 class="font-bold text-lg text-gray-900 mb-4">Design New Examination</h3>
                <form id="create-exam-form" onsubmit="createNewExam(event)" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Exam Title</label>
                        <input type="text" id="create-exam-title" required placeholder="e.g. CS301 Midterm" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Description</label>
                        <textarea id="create-exam-description" rows="3" placeholder="Overview of the assessment..." class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"></textarea>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-gray-700 mb-1">Duration (Minutes)</label>
                            <input type="number" id="create-exam-duration" value="60" min="1" required class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-700 mb-1">Primary Language</label>
                            <select id="create-exam-language" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                {language_options_html}
                            </select>
                        </div>
                    </div>
                    <div class="flex justify-end gap-3 pt-3 border-t border-gray-200">
                        <button type="button" onclick="closeNewExamModal()" class="px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md">Cancel</button>
                        <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md">Create Examination</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Edit Exam Modal -->
        <div id="edit-exam-modal" class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 hidden">
            <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 border border-gray-200">
                <h3 class="font-bold text-lg text-gray-900 mb-4">Edit Exam Metadata</h3>
                <form onsubmit="saveExamEdits(event)" class="space-y-4">
                    <input type="hidden" id="edit-exam-id">
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Exam Title</label>
                        <input type="text" id="edit-exam-title" required class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Description</label>
                        <textarea id="edit-exam-description" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Duration (Minutes)</label>
                        <input type="number" id="edit-exam-duration" min="1" required class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                    </div>
                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="edit-exam-published" class="rounded text-blue-600">
                        <label for="edit-exam-published" class="text-xs font-semibold text-gray-700">Published / Active</label>
                    </div>
                    <div class="flex justify-end gap-3 pt-3 border-t border-gray-200">
                        <button type="button" onclick="closeEditExamModal()" class="px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md">Cancel</button>
                        <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md">Save Changes</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Test Case Edit/Create Modal -->
        <div id="testcase-modal" class="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 hidden">
            <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 border border-gray-200">
                <h3 id="tc-modal-title" class="font-bold text-lg text-gray-900 mb-4">Add Test Case</h3>
                <form onsubmit="saveTestCaseModal(event)" class="space-y-4">
                    <input type="hidden" id="tc-modal-id">
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Input Data (STDIN / Arguments)</label>
                        <textarea id="tc-modal-input" required rows="2" class="font-mono w-full px-3 py-2 border border-gray-300 rounded-md text-xs"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1">Expected Output</label>
                        <textarea id="tc-modal-output" required rows="2" class="font-mono w-full px-3 py-2 border border-gray-300 rounded-md text-xs"></textarea>
                    </div>
                    <div class="flex items-center justify-between gap-4">
                        <label class="flex items-center gap-2 text-xs font-semibold text-gray-700 cursor-pointer">
                            <input type="checkbox" id="tc-modal-hidden" checked class="rounded text-blue-600"> Hidden Test Case
                        </label>
                        <div>
                            <label class="text-xs font-semibold text-gray-700 mr-2">Weight</label>
                            <input type="number" step="0.1" id="tc-modal-weight" value="1.0" class="w-16 px-2 py-1 border border-gray-300 rounded text-xs">
                        </div>
                    </div>
                    <div class="flex justify-end gap-3 pt-3 border-t border-gray-200">
                        <button type="button" onclick="closeTestCaseModal()" class="px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md">Cancel</button>
                        <button type="submit" class="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md">Save Test Case</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Hidden Form for LTI Deep Link Submit to Return to Moodle -->
        <form id="deep-link-auto-form" action="/api/launch/deep-link/submit" method="POST" class="hidden">
            <input type="hidden" name="id_token" value="{id_token}" />
            <input type="hidden" name="exam_id" id="deep-link-exam-id" />
        </form>

        <!-- MAIN WRAPPER -->
        <div class="w-full max-w-none m-0 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden min-h-screen">
            <div class="border-b border-gray-200 bg-white px-6">
                <nav class="-mb-px flex space-x-8">
                    <button id="btn-tab-exams" onclick="showTab('tab-exams')" class="tab-btn py-4 px-1 text-center border-b-2 font-semibold text-sm border-blue-500 text-blue-600">
                        📚 Examinations
                    </button>
                    <button id="btn-tab-results" onclick="showTab('tab-results')" class="tab-btn py-4 px-1 text-center border-b-2 font-semibold text-sm border-transparent text-gray-500 hover:text-gray-700">
                        📊 Lecturer Results
                    </button>
                </nav>
            </div>

            <div class="p-6">
                <!-- TAB 1: EXAMINATIONS -->
                <div id="tab-exams" class="tab-content">
                    
                    <!-- View Panel 1: Exams List -->
                    <div id="panel-exams-list" class="view-panel space-y-6">
                        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                            <div>
                                <h2 class="text-xl font-bold text-gray-900">Programming Examinations</h2>
                                <p class="text-xs text-gray-500">Author, configure, and manage your course examinations.</p>
                            </div>
                            <button type="button" onclick="openNewExamWizard()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm transition">
                                + New Examination
                            </button>
                        </div>

                        <!-- Search & Status Filter Controls -->
                        <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-gray-50 p-3 rounded-xl border border-gray-200">
                            <div class="relative flex-1">
                                <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm pointer-events-none">🔍</span>
                                <input type="text" oninput="onSearchInput(this.value)" placeholder="Search examinations by title, description, or language..." class="w-full pl-9 pr-4 py-2 bg-white border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-blue-500 shadow-2xs">
                            </div>
                            <div class="flex items-center gap-1 shrink-0">
                                <button type="button" onclick="setStatusFilter('all', this)" class="filter-pill px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white">All</button>
                                <button type="button" onclick="setStatusFilter('published', this)" class="filter-pill px-3 py-1.5 rounded-lg text-xs bg-gray-100 text-gray-600 hover:bg-gray-200">Published</button>
                                <button type="button" onclick="setStatusFilter('draft', this)" class="filter-pill px-3 py-1.5 rounded-lg text-xs bg-gray-100 text-gray-600 hover:bg-gray-200">Draft</button>
                            </div>
                        </div>

                        <div id="exams-grid" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <!-- Populated dynamically via fetchExams() -->
                        </div>
                    </div>

                    <!-- View Panel 2: Question Manager -->
                    <div id="panel-question-manager" class="view-panel hidden space-y-6">
                        <div class="flex justify-between items-center pb-4 border-b border-gray-200">
                            <div>
                                <button type="button" onclick="backToExamsList()" class="text-xs font-semibold text-gray-500 hover:text-gray-700 mb-1 inline-flex items-center gap-1">
                                    ← Back to Examinations
                                </button>
                                <h2 id="qm-exam-title" class="text-xl font-bold text-gray-900">Questions</h2>
                            </div>
                            <button type="button" onclick="openNewQuestionForm()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2 rounded-lg shadow-xs transition">
                                + Add Question
                            </button>
                        </div>

                        <div id="questions-list-container" class="space-y-3">
                            <!-- Populated dynamically -->
                        </div>
                    </div>

                    <!-- View Panel 3: Question & Testcase Editor -->
                    <div id="panel-question-editor" class="view-panel hidden space-y-6">
                        <div class="flex justify-between items-center pb-4 border-b border-gray-200">
                            <div>
                                <button type="button" onclick="backToQuestionManager()" class="text-xs font-semibold text-gray-500 hover:text-gray-700 mb-1 inline-flex items-center gap-1">
                                    ← Back to Question List
                                </button>
                                <h2 id="q-editor-title" class="text-xl font-bold text-gray-900">Question Editor</h2>
                            </div>
                        </div>

                        <form id="form-question" onsubmit="saveQuestion(event)" class="space-y-6">
                            <input type="hidden" id="q-id-hidden">

                            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div class="md:col-span-2 space-y-4">
                                    <div>
                                        <label class="block text-xs font-semibold text-gray-700 mb-1">Question Title</label>
                                        <input type="text" id="q-title" required placeholder="e.g. Recursive Factorial" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                    </div>
                                    <div>
                                        <label class="block text-xs font-semibold text-gray-700 mb-1">Description / Problem Statement</label>
                                        <textarea id="q-description" rows="4" required placeholder="Describe the requirements for students..." class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"></textarea>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div>
                                            <label class="block text-xs font-semibold text-gray-700 mb-1">Programming Language</label>
                                            <select id="q-language" onchange="loadStaticRules(this.value)" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                                {language_options_html}
                                            </select>
                                        </div>
                                        <div>
                                            <label class="block text-xs font-semibold text-gray-700 mb-1">Difficulty Level</label>
                                            <select id="q-diff" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                                <option value="1">1 - Easy</option>
                                                <option value="2">2 - Medium</option>
                                                <option value="3">3 - Hard</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div>
                                            <label class="block text-xs font-semibold text-gray-700 mb-1">Functional Weight (%)</label>
                                            <input type="number" id="q-functional-weight" value="80" step="0.1" min="0" max="100" required class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                        </div>
                                        <div>
                                            <label class="block text-xs font-semibold text-gray-700 mb-1">Static Weight (%)</label>
                                            <input type="number" id="q-static-weight" value="20" step="0.1" min="0" max="100" required class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                        </div>
                                    </div>
                                    <div>
                                        <label class="block text-xs font-semibold text-gray-700 mb-1">Starter Code / Boilerplate</label>
                                        <textarea id="q-default-code" rows="5" class="font-mono w-full px-3 py-2 border border-gray-300 rounded-md text-xs bg-slate-900 text-slate-100">def solution():\n    pass</textarea>
                                    </div>
                                </div>

                                <!-- Static Rules Sidebar -->
                                <div class="space-y-4">
                                    <div class="bg-gray-50 border border-gray-200 rounded-xl p-4">
                                        <div class="flex items-center justify-between mb-2">
                                            <h4 class="font-bold text-xs text-gray-800 uppercase tracking-wider">Static Analysis Rules</h4>
                                        </div>
                                        <p class="text-xs text-gray-500 mb-3">Loaded dynamically based on the selected language registry.</p>
                                        
                                        <div id="static-rules-panel" class="space-y-2">
                                            <!-- Loaded dynamically -->
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-lg shadow-sm transition">
                                Save Question
                            </button>
                        </form>

                        <!-- Test Cases Sub-Section -->
                        <div id="testcases-section" class="pt-6 border-t border-gray-200 space-y-4">
                            <div class="flex justify-between items-center">
                                <div>
                                    <h3 class="font-bold text-lg text-gray-900">Test Cases</h3>
                                    <p class="text-xs text-gray-500">Configure public and hidden test cases for automated functional grading.</p>
                                </div>
                                <button type="button" onclick="openTestCaseModal()" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3 py-2 rounded-md shadow-xs transition">
                                    + Add Test Case
                                </button>
                            </div>

                            <div id="testcases-list" class="space-y-2">
                                <!-- Loaded dynamically -->
                            </div>
                        </div>

                    </div>

                </div>

                <!-- TAB 2: LECTURER RESULTS -->
                <div id="tab-results" class="tab-content hidden">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">View Lecturer Results</h2>
                    <p class="text-sm text-gray-600 mb-4">Open submissions and grades inside Moodle for the selected exam.</p>
                    <form action="/api/launch/results" method="POST" class="space-y-4 max-w-lg">
                        <input type="hidden" name="id_token" value="{id_token}" />
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Exam</label>
                            <select name="exam_id" required class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                                <option value="">-- Choose an exam --</option>
                                {options_html}
                            </select>
                        </div>
                        <button type="submit" class="w-full py-2.5 px-4 rounded-md shadow-xs text-sm font-semibold text-white bg-slate-800 hover:bg-slate-900">
                            View Results in Moodle
                        </button>
                    </form>
                </div>
            </div>
        </div>

        <script>
            // Initialize dashboard view
            fetchExams();
        </script>
    </body>
    </html>
    """
