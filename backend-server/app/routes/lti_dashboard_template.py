import json
from ..services.language_registry import LANGUAGE_REGISTRY


def get_instructor_dashboard_html(id_token: str, exams: list):
    initial_exams_data = [
        {
            "exam_id": exam.exam_id,
            "title": exam.title,
            "description": exam.description or "",
            "duration": exam.duration,
            "language": exam.language or "python",
            "question_count": len(exam.questions),
            "submission_count": len(exam.submissions),
            "published": exam.published,
        }
        for exam in exams
    ]
    initial_exams_json = json.dumps(initial_exams_data)

    cards_list = []
    if exams:
        for exam in exams:
            is_published = exam.published
            badge_class = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" if is_published else "bg-amber-500/20 text-amber-300 border-amber-500/40"
            badge_text = "Published" if is_published else "Draft"
            use_disabled = "" if is_published else "disabled"
            use_class = "bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs" if is_published else "bg-emerald-900/30 text-emerald-500 cursor-not-allowed opacity-60"
            use_title = "Use this examination for the active Moodle course activity" if is_published else "Publish this examination before using it for a course."
            q_count = len(exam.questions)
            s_count = len(exam.submissions)
            sub_class = "text-emerald-400 font-bold" if s_count > 0 else "text-gray-400"
            lang_upper = (exam.language or 'python').upper()
            title_escaped = (exam.title or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", "&#039;")
            desc_escaped = (exam.description or 'No description provided.').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", "&#039;")
            not_pub_str = "true" if not is_published else "false"

            cards_list.append(f"""
                <div class="bg-gray-800/90 border border-gray-700 text-white rounded-xl shadow-sm hover:shadow-md transition p-5 flex flex-col justify-between" id="exam-card-{exam.exam_id}">
                    <div>
                        <div class="flex items-start justify-between gap-2 mb-2">
                            <h3 class="font-bold text-lg text-white line-clamp-1">{title_escaped}</h3>
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border {badge_class}">
                                {badge_text}
                            </span>
                        </div>
                        <p class="text-xs text-gray-300 mb-4 line-clamp-2">{desc_escaped}</p>
                        
                        <div class="flex items-center gap-4 text-xs text-gray-300 bg-gray-900/60 p-2.5 rounded-lg border border-gray-700 mb-4 flex-wrap">
                            <div>&#9201; <b class="text-white">{exam.duration}</b> min</div>
                            <div>&#128221; <b class="text-white">{q_count}</b> questions</div>
                            <div>&#128229; <b class="{sub_class}">{s_count}</b> submissions</div>
                            <div>&#128187; <b class="text-white">{lang_upper}</b></div>
                        </div>
                    </div>

                    <div class="flex items-center gap-2 pt-3 border-t border-gray-700 flex-wrap">
                        <button type="button" onclick="openEditExamModal({exam.exam_id})" class="flex-1 bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                            Edit Exam
                        </button>
                        <button type="button" onclick="openQuestionManager({exam.exam_id}, '{title_escaped}')" class="flex-1 bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 text-xs font-semibold py-2 px-3 rounded-md transition text-center border border-blue-500/30">
                            Manage Questions
                        </button>
                        <button type="button" onclick="togglePublishExam({exam.exam_id}, {not_pub_str})" class="bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                            {'Unpublish' if is_published else 'Publish'}
                        </button>
                        <button type="button" {use_disabled} title="{use_title}" onclick="useExamForCourse({exam.exam_id})" class="btn-use-exam text-xs font-semibold py-2 px-3 rounded-md transition text-center {use_class}">
                            Use for This Course
                        </button>
                        <button type="button" onclick="promptDeleteExam({exam.exam_id}, '{title_escaped}')" class="btn-delete-exam bg-red-900/40 hover:bg-red-900/60 text-red-300 text-xs font-semibold py-2 px-3 rounded-md transition text-center border border-red-700/50">
                            Delete
                        </button>
                    </div>
                </div>
            """)
        initial_cards_html = "".join(cards_list)
    else:
        initial_cards_html = """
            <div class="col-span-2 text-center py-12 border-2 border-dashed border-gray-700 rounded-xl bg-gray-800/50">
                <p class="text-base font-semibold text-gray-200 mb-1">No examinations created yet</p>
                <p class="text-xs text-gray-400 mb-4">Create your first programming examination to get started.</p>
                <button type="button" onclick="openNewExamWizard()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm">
                    + New Examination
                </button>
            </div>
        """
    init_subs_str = "0"
    init_avg_str = "0%"
    init_median_str = "0%"
    init_high_low_str = "0% / 0%"
    init_pass_rate_str = "0%"
    init_sync_ratio_str = "0 / 0"
    initial_results_hidden = "hidden"

    if exams:
        selected_exam = exams[0]
        initial_results_hidden = ""
        subs = selected_exam.submissions
        init_subs_str = str(len(subs))
        scores = [s.final_score if s.final_score is not None else (s.score or 0.0) for s in subs]
        if scores:
            import statistics
            init_avg_str = f"{round(statistics.mean(scores), 1)}%"
            init_median_str = f"{round(statistics.median(scores), 1)}%"
            init_high_low_str = f"{round(max(scores), 1)}% / {round(min(scores), 1)}%"
            passed = sum(1 for s in subs if (s.status == 1 or s.status_label == "Passed"))
            init_pass_rate_str = f"{round(passed / len(scores) * 100, 1)}%"
            synced = sum(1 for s in subs if s.sync_status == "synced")
            init_sync_ratio_str = f"{synced} / {len(subs)}"

    options_html = ""
    for idx, exam in enumerate(exams):
        sub_count = len(exam.submissions)
        sub_text = "1 submission" if sub_count == 1 else f"{sub_count} submissions"
        icon = "🟢" if sub_count > 0 else "⚪"
        options_html += f'<option value="{exam.exam_id}">{icon} {exam.title} ({exam.duration}m) — {sub_text}</option>'

    initial_results_hidden = "hidden"

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
        let allExamsList = {initial_exams_json};
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
                    document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
                    const listPanel = document.getElementById('panel-exams-list');
                    if (listPanel) listPanel.classList.remove('hidden');
                    fetchExams();
                }} else if (tabId === 'tab-results') {{
                    loadResultsTab();
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
                if (!container) return;

                try {{
                    const res = await fetch('/lti/exams');
                    if (!res.ok) throw new Error('Failed to load examinations from server');
                    const fetched = await res.json();
                    if (Array.isArray(fetched)) {{
                        allExamsList = fetched;
                    }} else {{
                        allExamsList = [];
                    }}
                    renderExamsGrid();
                }} catch (err) {{
                    console.error("fetchExams error:", err);
                    if (!Array.isArray(allExamsList) || !allExamsList.length) {{
                        container.innerHTML = `<div class="col-span-2 text-center py-8 text-red-400 font-semibold">Error loading examinations: ${{escapeHtml(err.message)}}</div>`;
                    }} else {{
                        renderExamsGrid();
                    }}
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
                if (!container) return;
                if (!Array.isArray(allExamsList)) {{
                    allExamsList = [];
                }}

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
                        <div class="col-span-2 text-center py-12 border-2 border-dashed border-gray-700 rounded-xl bg-gray-800/50">
                            <p class="text-base font-semibold text-gray-200 mb-1">No examinations created yet</p>
                            <p class="text-xs text-gray-400 mb-4">Create your first programming examination to get started.</p>
                            <button type="button" onclick="openNewExamWizard()" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm">
                                + New Examination
                            </button>
                        </div>
                    `;
                    return;
                }}

                if (!filtered.length) {{
                    container.innerHTML = `
                        <div class="col-span-2 text-center py-10 border border-gray-700 rounded-xl bg-gray-800/50">
                            <p class="text-sm font-semibold text-gray-200 mb-1">No examinations match your search</p>
                            <p class="text-xs text-gray-400">Try adjusting your search query or filter selection.</p>
                        </div>
                    `;
                    return;
                }}

                container.innerHTML = filtered.map(exam => {{
                    const isPublished = exam.published !== false;
                    const badgeClass = isPublished ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border-amber-500/40';
                    const badgeText = isPublished ? 'Published' : 'Draft';

                    const useBtnDisabled = !isPublished;
                    const useBtnClass = useBtnDisabled 
                        ? 'bg-emerald-900/30 text-emerald-500 cursor-not-allowed opacity-60' 
                        : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs';
                    const useBtnTitle = useBtnDisabled ? 'Publish this examination before using it for a course.' : 'Use this examination for the active Moodle course activity';

                    return `
                        <div class="bg-gray-800/90 border border-gray-700 text-white rounded-xl shadow-sm hover:shadow-md transition p-5 flex flex-col justify-between" id="exam-card-${{exam.exam_id}}">
                            <div>
                                <div class="flex items-start justify-between gap-2 mb-2">
                                    <h3 class="font-bold text-lg text-white line-clamp-1">${{escapeHtml(exam.title)}}</h3>
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${{badgeClass}}">
                                        ${{badgeText}}
                                    </span>
                                </div>
                                <p class="text-xs text-gray-300 mb-4 line-clamp-2">${{escapeHtml(exam.description || 'No description provided.')}}</p>
                                
                                <div class="flex items-center gap-4 text-xs text-gray-300 bg-gray-900/60 p-2.5 rounded-lg border border-gray-700 mb-4 flex-wrap">
                                    <div>&#9201; <b class="text-white">${{exam.duration}}</b> min</div>
                                    <div>&#128221; <b class="text-white">${{exam.question_count}}</b> questions</div>
                                    <div>&#128229; <b class="${{(exam.submission_count || 0) > 0 ? 'text-emerald-400 font-bold' : 'text-gray-400'}}">${{exam.submission_count || 0}}</b> submissions</div>
                                    <div>&#128187; <b class="text-white">${{escapeHtml((exam.language || 'python').toUpperCase())}}</b></div>
                                </div>
                            </div>

                            <div class="flex items-center gap-2 pt-3 border-t border-gray-700 flex-wrap">
                                <button type="button" onclick="openEditExamModal(${{exam.exam_id}})" class="flex-1 bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                                    Edit Exam
                                </button>
                                <button type="button" onclick="openQuestionManager(${{exam.exam_id}}, '${{escapeHtml(exam.title)}}')" class="flex-1 bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 text-xs font-semibold py-2 px-3 rounded-md transition text-center border border-blue-500/30">
                                    Manage Questions
                                </button>
                                <button type="button" onclick="togglePublishExam(${{exam.exam_id}}, ${{!isPublished}})" class="bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold py-2 px-3 rounded-md transition text-center">
                                    ${{isPublished ? 'Unpublish' : 'Publish'}}
                                </button>
                                <button type="button" ${{useBtnDisabled ? 'disabled' : ''}} title="${{useBtnTitle}}" onclick="useExamForCourse(${{exam.exam_id}})" class="btn-use-exam text-xs font-semibold py-2 px-3 rounded-md transition text-center ${{useBtnClass}}">
                                    Use for This Course
                                </button>
                                <button type="button" onclick="promptDeleteExam(${{exam.exam_id}}, '${{escapeHtml(exam.title)}}')" class="btn-delete-exam bg-red-900/40 hover:bg-red-900/60 text-red-300 text-xs font-semibold py-2 px-3 rounded-md transition text-center border border-red-700/50">
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
                    await fetchExams();
                    
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
                renderTestCases([]);

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
                    
                    renderTestCases(data.test_cases || []);
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
                if (!tcId && !currentQuestionId) {{
                    showToast('Please save the question first before adding test cases.', 'error');
                    return;
                }}
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
                            {initial_cards_html}
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

                <!-- TAB 2: LECTURER RESULTS DASHBOARD -->
                <div id="tab-results" class="tab-content hidden space-y-6">
                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-200">
                        <div>
                            <h2 class="text-xl font-bold text-gray-900">Lecturer Assessment Dashboard</h2>
                            <p class="text-xs text-gray-500">Monitor real-time exam progress, inspect student submissions, view static analysis & functional test breakdowns, and manage Moodle grade sync.</p>
                        </div>
                        <div class="flex items-center gap-3">
                            <select id="results-exam-select" onchange="loadSelectedExamResults()" class="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white font-semibold text-gray-800 shadow-xs">
                                <option value="" selected>-- Choose an examination --</option>
                                {options_html}
                            </select>
                            <span id="results-autorefresh-toggle" onclick="toggleAutoRefreshPause()" title="Click to pause or resume auto-refresh" class="px-3 py-2 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-full text-xs font-semibold cursor-pointer select-none">
                                🔄 Auto-Refresh: 20s
                            </span>
                        </div>
                    </div>

                    <div id="results-select-prompt" class="bg-gray-800/90 border border-gray-700 rounded-xl p-12 text-center space-y-3">
                        <div class="text-4xl">📋</div>
                        <h3 class="text-lg font-bold text-white">Select an Examination</h3>
                        <p class="text-xs text-gray-400 max-w-md mx-auto">Please select an examination from the dropdown above to view student submissions, metrics, and grade sync status.</p>
                    </div>

                    <div id="results-dashboard-container" class="space-y-6 hidden">
                        <!-- Summary Cards -->
                        <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm">
                                <div class="text-xs font-semibold text-gray-400 uppercase">Submissions</div>
                                <div class="text-2xl font-bold text-white mt-1" id="stat-total-subs">{init_subs_str}</div>
                            </div>
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm">
                                <div class="text-xs font-semibold text-gray-400 uppercase">Average Score</div>
                                <div class="text-2xl font-bold text-blue-400 mt-1" id="stat-avg-score">{init_avg_str}</div>
                            </div>
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm">
                                <div class="text-xs font-semibold text-gray-400 uppercase">Median Score</div>
                                <div class="text-2xl font-bold text-indigo-400 mt-1" id="stat-median-score">{init_median_str}</div>
                            </div>
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm">
                                <div class="text-xs font-semibold text-gray-400 uppercase">High / Low</div>
                                <div class="text-lg font-bold text-gray-200 mt-1" id="stat-highest-lowest">{init_high_low_str}</div>
                            </div>
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm">
                                <div class="text-xs font-semibold text-gray-400 uppercase">Pass Rate</div>
                                <div class="text-2xl font-bold text-emerald-400 mt-1" id="stat-pass-rate">{init_pass_rate_str}</div>
                            </div>
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm">
                                <div class="text-xs font-semibold text-gray-400 uppercase">Moodle Synced</div>
                                <div class="text-xl font-bold text-white mt-1" id="stat-sync-ratio">{init_sync_ratio_str}</div>
                            </div>
                        </div>

                        <!-- Charts & Analytics Section -->
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <!-- Grade Distribution Histogram -->
                            <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-5 shadow-sm space-y-3">
                                <h3 class="font-bold text-sm text-gray-200 uppercase tracking-wider">Grade Distribution Histogram</h3>
                                <div class="h-32 flex items-end justify-between gap-2 pt-4 border-b border-gray-700">
                                    <div class="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                                        <span class="text-xs text-gray-300" id="hist-100-val">0</span>
                                        <div id="hist-100-bar" class="w-full bg-emerald-500 rounded-t transition-all duration-500" style="height: 8%"></div>
                                        <span class="text-[10px] text-gray-400 font-semibold">100%</span>
                                    </div>
                                    <div class="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                                        <span class="text-xs text-gray-300" id="hist-90-99-val">0</span>
                                        <div id="hist-90-99-bar" class="w-full bg-blue-500 rounded-t transition-all duration-500" style="height: 8%"></div>
                                        <span class="text-[10px] text-gray-400 font-semibold">90-99</span>
                                    </div>
                                    <div class="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                                        <span class="text-xs text-gray-300" id="hist-80-89-val">0</span>
                                        <div id="hist-80-89-bar" class="w-full bg-indigo-500 rounded-t transition-all duration-500" style="height: 8%"></div>
                                        <span class="text-[10px] text-gray-400 font-semibold">80-89</span>
                                    </div>
                                    <div class="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                                        <span class="text-xs text-gray-300" id="hist-70-79-val">0</span>
                                        <div id="hist-70-79-bar" class="w-full bg-amber-500 rounded-t transition-all duration-500" style="height: 8%"></div>
                                        <span class="text-[10px] text-gray-400 font-semibold">70-79</span>
                                    </div>
                                    <div class="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                                        <span class="text-xs text-gray-300" id="hist-below-70-val">0</span>
                                        <div id="hist-below-70-bar" class="w-full bg-red-500 rounded-t transition-all duration-500" style="height: 8%"></div>
                                        <span class="text-[10px] text-gray-400 font-semibold">&lt;70</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Static Rules Failure Heatmap -->
                            <div class="md:col-span-2 bg-gray-800/90 border border-gray-700 rounded-xl p-5 shadow-sm space-y-3">
                                <div class="flex items-center justify-between">
                                    <h3 class="font-bold text-sm text-gray-200 uppercase tracking-wider">Static Rule Failure Heatmap</h3>
                                    <span class="text-xs text-gray-400">Class-wide common mistakes</span>
                                </div>
                                <div id="rule-heatmap-container" class="space-y-3 max-h-32 overflow-y-auto pr-1">
                                    <p class="text-xs text-gray-400">Loading static rule evaluation statistics...</p>
                                </div>
                            </div>
                        </div>

                        <!-- Toolbar: Search, Filters, Sorting & Export -->
                        <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
                            <div class="flex items-center gap-3 w-full md:w-auto">
                                <input type="text" oninput="setResultsSearch(this.value)" placeholder="Search student name, email, or submission ID..." class="w-full md:w-80 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-400 focus:outline-none focus:border-blue-500">
                                <div class="flex items-center gap-1">
                                    <button type="button" onclick="setResultsStatusFilter('all', this)" class="results-filter-pill px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white">All</button>
                                    <button type="button" onclick="setResultsStatusFilter('passed', this)" class="results-filter-pill px-3 py-1.5 rounded-lg text-xs text-gray-300 bg-gray-700 hover:bg-gray-600">Passed</button>
                                    <button type="button" onclick="setResultsStatusFilter('failed', this)" class="results-filter-pill px-3 py-1.5 rounded-lg text-xs text-gray-300 bg-gray-700 hover:bg-gray-600">Failed</button>
                                    <button type="button" onclick="setResultsStatusFilter('not_synced', this)" class="results-filter-pill px-3 py-1.5 rounded-lg text-xs text-gray-300 bg-gray-700 hover:bg-gray-600">Not Synced</button>
                                </div>
                            </div>

                            <div class="flex items-center gap-3 w-full md:w-auto justify-end">
                                <select onchange="setResultsSortBy(this.value)" class="px-3 py-1.5 border border-gray-700 rounded-lg text-xs bg-gray-900 text-gray-200">
                                    <option value="submitted_at_desc">Sort by Date (Newest)</option>
                                    <option value="name_asc">Sort by Student Name (A-Z)</option>
                                    <option value="score_desc">Sort by Score (High to Low)</option>
                                    <option value="score_asc">Sort by Score (Low to High)</option>
                                    <option value="duration_desc">Sort by Duration (Slowest)</option>
                                    <option value="sync_status">Sort by Moodle Sync Status</option>
                                </select>

                                <button type="button" onclick="exportResults('csv')" class="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-3 py-2 rounded-lg shadow-xs flex items-center gap-1">
                                    📥 Export CSV
                                </button>
                            </div>
                        </div>

                        <!-- Results Table -->
                        <div class="bg-gray-800/90 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
                            <div class="overflow-x-auto">
                                <table class="w-full text-left border-collapse">
                                    <thead>
                                        <tr class="bg-gray-900/80 border-b border-gray-700 text-xs font-bold text-gray-300 uppercase tracking-wider">
                                            <th class="py-3 px-4">Sub ID</th>
                                            <th class="py-3 px-4">Student</th>
                                            <th class="py-3 px-4">Score</th>
                                            <th class="py-3 px-4">Status</th>
                                            <th class="py-3 px-4">Moodle AGS</th>
                                            <th class="py-3 px-4">Duration</th>
                                            <th class="py-3 px-4">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="results-table-body">
                                        <tr><td colspan="7" class="text-center py-8 text-gray-400">Select an examination to display student results.</td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div id="results-pagination-container" class="p-4 bg-gray-900/40 border-t border-gray-700 text-gray-300"></div>
                        </div>
                    </div>
                </div>

                <!-- VIEW SUBMISSION MODAL -->
                <div id="modal-submission-detail" class="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center z-50 hidden p-4">
                    <div class="bg-gray-900 rounded-2xl shadow-2xl border border-gray-700 max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden text-white">
                        <div class="px-6 py-4 bg-gray-950 text-white flex items-center justify-between border-b border-gray-800">
                            <div>
                                <div class="flex items-center gap-2">
                                    <h3 class="text-lg font-bold text-white" id="modal-student-name">Student Name</h3>
                                    <span class="font-mono text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300" id="modal-sub-id">#0</span>
                                </div>
                                <p class="text-xs text-gray-400" id="modal-student-email">student@example.com</p>
                            </div>
                            <div class="flex items-center gap-4">
                                <div class="text-right">
                                    <div class="text-xl font-extrabold text-emerald-400" id="modal-final-score">0%</div>
                                    <div class="text-[10px] text-gray-400 font-mono">Graded in <span id="modal-duration">0 ms</span></div>
                                </div>
                                <button type="button" onclick="closeSubmissionModal()" class="text-gray-400 hover:text-white text-xl font-bold px-2">✕</button>
                            </div>
                        </div>

                        <div class="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-gray-200">
                            <!-- Code Viewer Section -->
                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <h4 class="font-bold text-xs text-gray-400 uppercase tracking-wider">Submitted Source Code</h4>
                                    <div id="modal-snapshot-buttons" class="flex items-center gap-1 overflow-x-auto py-1"></div>
                                </div>
                                <div class="bg-gray-950 text-gray-100 font-mono text-xs overflow-x-auto p-4 rounded-xl border border-gray-800 shadow-inner max-h-60" id="modal-code-display"></div>
                                <div class="flex justify-between text-[11px] text-gray-400 font-mono">
                                    <span>SHA-256 Hash: <span id="modal-sub-hash" class="text-gray-300">N/A</span></span>
                                    <span>Engine: Secure Isolation Container</span>
                                </div>
                            </div>

                            <!-- Score Breakdown Cards -->
                            <div class="grid grid-cols-2 gap-4">
                                <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-3">
                                    <div class="text-xs font-semibold text-blue-400">Functional Test Score</div>
                                    <div class="text-lg font-bold text-blue-300 mt-1" id="modal-func-score">0 / 100</div>
                                </div>
                                <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-3">
                                    <div class="text-xs font-semibold text-indigo-400">Static Analysis Score</div>
                                    <div class="text-lg font-bold text-indigo-300 mt-1" id="modal-static-score">0 / 100</div>
                                </div>
                            </div>

                            <!-- Functional Test Results Table -->
                            <div class="space-y-2">
                                <h4 class="font-bold text-xs text-gray-400 uppercase tracking-wider">Functional Test Cases Breakdown</h4>
                                <div class="border border-gray-700 rounded-xl overflow-hidden bg-gray-800/90">
                                    <table class="w-full text-left border-collapse">
                                        <thead>
                                            <tr class="bg-gray-900 border-b border-gray-700 text-[11px] font-bold text-gray-300 uppercase">
                                                <th class="py-2 px-3">Test Case</th>
                                                <th class="py-2 px-3">Input</th>
                                                <th class="py-2 px-3">Expected</th>
                                                <th class="py-2 px-3">Output</th>
                                                <th class="py-2 px-3">Weight</th>
                                                <th class="py-2 px-3">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody id="modal-func-table"></tbody>
                                    </table>
                                </div>
                            </div>

                            <!-- Static Analysis Breakdown Table -->
                            <div class="space-y-2">
                                <h4 class="font-bold text-xs text-gray-400 uppercase tracking-wider">Static Analysis Rule Breakdown</h4>
                                <div class="border border-gray-700 rounded-xl overflow-hidden bg-gray-800/90">
                                    <table class="w-full text-left border-collapse">
                                        <thead>
                                            <tr class="bg-gray-900 border-b border-gray-700 text-[11px] font-bold text-gray-300 uppercase">
                                                <th class="py-2 px-3">Rule</th>
                                                <th class="py-2 px-3">Expected</th>
                                                <th class="py-2 px-3">Status</th>
                                                <th class="py-2 px-3">Weight</th>
                                                <th class="py-2 px-3">Earned</th>
                                            </tr>
                                        </thead>
                                        <tbody id="modal-static-table"></tbody>
                                    </table>
                                </div>
                            </div>

                            <!-- Submission Timeline & Moodle Sync Panel -->
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 space-y-2">
                                    <h4 class="font-bold text-xs text-gray-400 uppercase tracking-wider">Submission Timeline</h4>
                                    <div id="modal-timeline" class="space-y-2"></div>
                                </div>
                                <div class="bg-gray-800/90 border border-gray-700 rounded-xl p-4 space-y-2">
                                    <h4 class="font-bold text-xs text-gray-400 uppercase tracking-wider">Moodle AGS Synchronization</h4>
                                    <div class="text-xs">
                                        <div>Status: <span id="modal-sync-status" class="font-bold text-white">PENDING</span></div>
                                        <div class="text-gray-400 mt-1" id="modal-sync-message">No telemetry message available.</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Initialize dashboard view immediately from embedded server state
            if (allExamsList && allExamsList.length) {{
                renderExamsGrid();
            }}
            fetchExams();

            let currentResultsPage = 1;
            let currentResultsPageSize = 20;
            let currentResultsSearch = '';
            let currentResultsStatusFilter = 'all';
            let currentResultsSortBy = 'submitted_at_desc';
            let autoRefreshTimerTable = null;
            let autoRefreshTimerAnalytics = null;
            let autoRefreshPaused = false;
            let currentSubmissionModalId = null;

            function getCurrentExamId() {{
                const select = document.getElementById('results-exam-select');
                if (!select) return null;
                return select.value || null;
            }}

            // Auto-load selected results on startup with document.readyState check
            function initResultsDashboard() {{
                loadSelectedExamResults();
            }}

            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initResultsDashboard);
            }} else {{
                initResultsDashboard();
            }}
               async function loadResultsTab() {{
                const select = document.getElementById('results-exam-select');
                if (!allExamsList || !allExamsList.length) {{
                    try {{
                        const res = await fetch('/lti/exams');
                        if (res.ok) allExamsList = await res.json();
                    }} catch (e) {{}}
                }}
                
                if (allExamsList && allExamsList.length) {{
                    const currentVal = select ? select.value : '';
                    select.innerHTML = '<option value="" ' + (!currentVal ? 'selected' : '') + '>-- Choose an examination --</option>' +
                        allExamsList.map((e) => {{
                            const subCount = e.submission_count || 0;
                            const subText = subCount === 1 ? '1 submission' : `${{subCount}} submissions`;
                            const icon = subCount > 0 ? '🟢' : '⚪';
                            const sel = (currentVal && String(currentVal) === String(e.exam_id)) ? 'selected' : '';
                            return `<option value="${{e.exam_id}}" ${{sel}}>${{icon}} ${{escapeHtml(e.title)}} (${{e.duration}}m) — ${{subText}}</option>`;
                        }}).join('');
                    loadSelectedExamResults();
                }} else {{
                    select.innerHTML = '<option value="">No examinations available</option>';
                }}
            }}

            function loadSelectedExamResults() {{
                const examId = getCurrentExamId();
                const container = document.getElementById('results-dashboard-container');
                const prompt = document.getElementById('results-select-prompt');

                if (!examId) {{
                    if (container) container.classList.add('hidden');
                    if (prompt) prompt.classList.remove('hidden');
                    stopResultsAutoRefresh();
                    return;
                }}

                if (prompt) prompt.classList.add('hidden');
                if (container) container.classList.remove('hidden');
                currentResultsPage = 1;
                fetchResultsTable();
                fetchResultsAnalytics();

                startResultsAutoRefresh();
            }}

            function startResultsAutoRefresh() {{
                stopResultsAutoRefresh();
                autoRefreshTimerTable = setInterval(() => {{
                    if (!autoRefreshPaused && getCurrentExamId() && !currentSubmissionModalId) {{
                        fetchResultsTable(currentResultsPage, true);
                    }}
                }}, 20000);

                autoRefreshTimerAnalytics = setInterval(() => {{
                    if (!autoRefreshPaused && getCurrentExamId() && !currentSubmissionModalId) {{
                        fetchResultsAnalytics(true);
                    }}
                }}, 60000);
            }}

            function stopResultsAutoRefresh() {{
                if (autoRefreshTimerTable) clearInterval(autoRefreshTimerTable);
                if (autoRefreshTimerAnalytics) clearInterval(autoRefreshTimerAnalytics);
                autoRefreshTimerTable = null;
                autoRefreshTimerAnalytics = null;
            }}

            function toggleAutoRefreshPause() {{
                autoRefreshPaused = !autoRefreshPaused;
                const badge = document.getElementById('results-autorefresh-toggle');
                if (autoRefreshPaused) {{
                    badge.innerHTML = '⏸ Auto-Refresh PAUSED';
                    badge.className = 'px-3 py-2 bg-amber-100 text-amber-800 border border-amber-300 rounded-full text-xs font-semibold cursor-pointer select-none';
                }} else {{
                    badge.innerHTML = '🔄 Auto-Refresh: 20s';
                    badge.className = 'px-3 py-2 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-full text-xs font-semibold cursor-pointer select-none';
                }}
            }}

            async function fetchResultsTable(page = 1, isSilent = false) {{
                const examId = getCurrentExamId();
                if (!examId) return;
                currentResultsPage = page;
                const tbody = document.getElementById('results-table-body');
                if (!isSilent) {{
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-400">Loading student results...</td></tr>';
                }}

                try {{
                    const url = `/lti/results/${{examId}}?page=${{page}}&page_size=${{currentResultsPageSize}}&search=${{encodeURIComponent(currentResultsSearch)}}&status_filter=${{currentResultsStatusFilter}}&sort_by=${{currentResultsSortBy}}`;
                    const res = await fetch(url);
                    if (!res.ok) throw new Error('Failed to fetch results');
                    const data = await res.json();
                    renderResultsTable(data);
                }} catch (err) {{
                    if (!isSilent) {{
                        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-red-400">Error: ${{escapeHtml(err.message)}}</td></tr>`;
                    }}
                }}
            }}

            async function fetchResultsAnalytics(isSilent = false) {{
                const examId = getCurrentExamId();
                if (!examId) return;
                try {{
                    const res = await fetch(`/lti/results/${{examId}}/analytics`);
                    if (!res.ok) return;
                    const data = await res.json();
                    renderResultsAnalytics(data);
                }} catch (e) {{}}
            }}

            function renderResultsTable(data) {{
                const tbody = document.getElementById('results-table-body');
                const pagination = document.getElementById('results-pagination-container');
                const submissions = data.submissions || [];

                if (!submissions.length) {{
                    const isFiltered = Boolean(currentResultsSearch || (currentResultsStatusFilter && currentResultsStatusFilter !== 'all'));
                    if (isFiltered) {{
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="7" class="text-center py-12 text-gray-300">
                                    <div class="space-y-1">
                                        <p class="text-sm font-semibold text-gray-200">🔍 No submissions match your search or filter</p>
                                        <p class="text-xs text-gray-400">Try adjusting your search term or selecting a different status filter pill.</p>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }} else {{
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="7" class="text-center py-12 text-gray-300">
                                    <div class="space-y-1">
                                        <p class="text-sm font-semibold text-gray-200">📥 No students have submitted this examination yet</p>
                                        <p class="text-xs text-gray-400">Student submissions will automatically populate here once code is submitted.</p>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }}
                    if (pagination) pagination.innerHTML = '';
                    return;
                }}

                tbody.innerHTML = submissions.map(item => {{
                    let statusBadge = '';
                    if (item.status_label === 'Passed') {{
                        statusBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">✅ Passed</span>';
                    }} else if (item.status_label === 'Compile Error') {{
                        statusBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">⚠️ Compile Error</span>';
                    }} else if (item.status_label === 'Runtime Error') {{
                        statusBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">⚠️ Runtime Error</span>';
                    }} else {{
                        statusBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">❌ Failed</span>';
                    }}

                    let syncBadge = '';
                    const syncMsg = escapeHtml(item.sync_message || 'No telemetry detail available.');
                    const timeStr = item.synced_at ? new Date(item.synced_at).toLocaleString() : 'N/A';
                    if (item.sync_status === 'synced') {{
                        syncBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 cursor-help" id="sync-badge-${{item.submission_id}}" title="Successfully synchronized to Moodle AGS at ${{timeStr}}.&#10;Details: ${{syncMsg}}">✓ Synced</span>`;
                    }} else if (item.sync_status === 'failed') {{
                        syncBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200 cursor-help" id="sync-badge-${{item.submission_id}}" title="AGS Sync Failed (Attempted: ${{timeStr}}).&#10;Reason: ${{syncMsg}}">✗ Failed</span>`;
                    }} else if (item.sync_status === 'not_available') {{
                        syncBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200 cursor-help" id="sync-badge-${{item.submission_id}}" title="Moodle Grade Sync Not Configured on this activity launch.&#10;Reason: ${{syncMsg}}">Not Configured</span>`;
                    }} else {{
                        syncBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-200 cursor-help" id="sync-badge-${{item.submission_id}}" title="Pending synchronization.&#10;Details: ${{syncMsg}}">Pending</span>`;
                    }}

                    const retryBtnHtml = (item.sync_status === 'failed' || item.sync_status === 'not_available') 
                        ? `<button type="button" onclick="retryMoodleSync(${{item.submission_id}}, this)" class="bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-2.5 py-1 rounded shadow-xs transition">Retry Moodle Sync</button>`
                        : '';

                    return `
                        <tr class="hover:bg-gray-700/50 border-b border-gray-700/60 text-sm">
                            <td class="py-3 px-4 font-mono text-xs text-gray-400">#${{item.submission_id}}</td>
                            <td class="py-3 px-4">
                                <div class="font-semibold text-white">${{escapeHtml(item.student_name)}}</div>
                                <div class="text-xs text-gray-400">${{escapeHtml(item.student_email)}}</div>
                            </td>
                            <td class="py-3 px-4 font-bold text-white">
                                ${{item.final_score}}%
                                <div class="text-[10px] font-normal text-gray-400">Func: ${{item.functional_score}} | Stat: ${{item.static_score}}</div>
                            </td>
                            <td class="py-3 px-4">${{statusBadge}}</td>
                            <td class="py-3 px-4">${{syncBadge}}</td>
                            <td class="py-3 px-4 text-xs text-gray-300 font-mono">${{item.grading_duration_ms}} ms</td>
                            <td class="py-3 px-4 space-x-2">
                                <button type="button" onclick="openSubmissionModal(${{item.submission_id}})" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded shadow-xs transition">
                                    View Submission
                                </button>
                                ${{retryBtnHtml}}
                            </td>
                        </tr>
                    `;
                }}).join('');

                const totalPages = data.total_pages || 1;
                const currentPage = data.current_page || 1;
                if (pagination) {{
                    const prevDisabled = currentPage <= 1 ? 'disabled opacity-50 cursor-not-allowed' : '';
                    const nextDisabled = currentPage >= totalPages ? 'disabled opacity-50 cursor-not-allowed' : '';
                    pagination.innerHTML = `
                        <div class="flex items-center justify-between text-xs">
                            <div>Showing page <b>${{currentPage}}</b> of <b>${{totalPages}}</b> (${{data.total_items}} total submissions)</div>
                            <div class="flex items-center gap-2">
                                <button type="button" onclick="fetchResultsTable(${{currentPage - 1}})" ${{prevDisabled}} class="px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 transition">Previous</button>
                                <button type="button" onclick="fetchResultsTable(${{currentPage + 1}})" ${{nextDisabled}} class="px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 transition">Next</button>
                            </div>
                        </div>
                    `;
                }}
            }}

            function renderResultsAnalytics(data) {{
                const ov = data.overview || {{}};
                document.getElementById('stat-total-subs').innerText = data.total_submissions || 0;
                document.getElementById('stat-avg-score').innerText = (ov.average_score || 0) + '%';
                document.getElementById('stat-median-score').innerText = (ov.median_score || 0) + '%';
                document.getElementById('stat-highest-lowest').innerText = (ov.highest_score || 0) + '% / ' + (ov.lowest_score || 0) + '%';
                document.getElementById('stat-pass-rate').innerText = (ov.pass_rate_pct || 0) + '%';
                document.getElementById('stat-sync-ratio').innerText = (ov.synced_count || 0) + ' / ' + (data.total_submissions || 0);

                const hist = data.histogram || {{}};
                const maxVal = Math.max(1, hist.score_100 || 0, hist.score_90_99 || 0, hist.score_80_89 || 0, hist.score_70_79 || 0, hist.score_below_70 || 0);

                const renderBar = (id, count) => {{
                    const pct = Math.round((count / maxVal) * 100);
                    document.getElementById(id + '-bar').style.height = Math.max(8, pct) + '%';
                    document.getElementById(id + '-val').innerText = count;
                }};
                renderBar('hist-100', hist.score_100 || 0);
                renderBar('hist-90-99', hist.score_90_99 || 0);
                renderBar('hist-80-89', hist.score_80_89 || 0);
                renderBar('hist-70-79', hist.score_70_79 || 0);
                renderBar('hist-below-70', hist.score_below_70 || 0);

                const heatmapContainer = document.getElementById('rule-heatmap-container');
                const heatmapList = data.rule_heatmap || [];
                if (!heatmapList.length) {{
                    heatmapContainer.innerHTML = '<p class="text-xs text-gray-400">No static rules evaluated.</p>';
                }} else {{
                    heatmapContainer.innerHTML = heatmapList.map(r => {{
                        const pct = Math.round((r.failed_count / Math.max(1, r.total_evaluations)) * 100);
                        return `
                            <div class="space-y-1">
                                <div class="flex justify-between text-xs font-semibold text-gray-700">
                                    <span>${{escapeHtml(r.rule_name)}}</span>
                                    <span>${{r.failed_count}} / ${{r.total_evaluations}} failed (${{pct}}%)</span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-amber-500 h-2 rounded-full" style="width: ${{pct}}%"></div>
                                </div>
                            </div>
                        `;
                    }}).join('');
                }}
            }}

            function setResultsSearch(val) {{
                currentResultsSearch = val;
                fetchResultsTable(1);
            }}

            function setResultsStatusFilter(filterStr, btnEl) {{
                currentResultsStatusFilter = filterStr;
                document.querySelectorAll('.results-filter-pill').forEach(el => {{
                    el.classList.remove('bg-blue-600', 'text-white', 'font-semibold');
                    el.classList.add('bg-gray-100', 'text-gray-600', 'hover:bg-gray-200');
                }});
                btnEl.classList.remove('bg-gray-100', 'text-gray-600', 'hover:bg-gray-200');
                btnEl.classList.add('bg-blue-600', 'text-white', 'font-semibold');
                fetchResultsTable(1);
            }}

            function setResultsSortBy(val) {{
                currentResultsSortBy = val;
                fetchResultsTable(1);
            }}

            function extractErrorMessage(data, fallback = 'An error occurred') {{
                if (typeof data === 'string') return data;
                if (data && data.message) return data.message;
                if (data && data.detail) {{
                    if (typeof data.detail === 'string') return data.detail;
                    if (Array.isArray(data.detail)) return data.detail.map(d => d.msg || d.detail || JSON.stringify(d)).join('; ');
                }}
                return fallback;
            }}

            async function retryMoodleSync(submissionId, btnEl) {{
                if (btnEl) {{
                    btnEl.disabled = true;
                    btnEl.innerText = "⏳ Syncing...";
                    btnEl.className = "bg-gray-400 text-white text-xs font-semibold px-2.5 py-1 rounded cursor-not-allowed";
                }}

                try {{
                    const res = await fetch(`/lti/sync/retry/${{submissionId}}`, {{method: 'POST'}});
                    const data = await res.json();
                    if (res.ok && data.sync_status === 'synced') {{
                        showToast("✓ Grade pushed to Moodle successfully!", "success");
                        const badge = document.getElementById('sync-badge-' + submissionId);
                        if (badge) {{
                            const nowStr = new Date().toLocaleString();
                            badge.innerText = "✓ Synced";
                            badge.className = "px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 cursor-help";
                            badge.title = `Successfully synchronized to Moodle AGS at ${{nowStr}}.\nDetails: ${{data.message || 'Score posted'}}`;
                        }}
                        if (btnEl) btnEl.remove();
                    }} else {{
                        const errMsg = extractErrorMessage(data, `HTTP ${{res.status}} ${{res.statusText || 'Sync error'}}`);
                        showToast("✗ Moodle Sync: " + errMsg, "error");
                        if (btnEl) {{
                            btnEl.disabled = false;
                            btnEl.innerText = "Retry Moodle Sync";
                            btnEl.className = "bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-2.5 py-1 rounded shadow-xs transition";
                        }}
                    }}
                }} catch (err) {{
                    showToast("Sync error: " + err.message, "error");
                    if (btnEl) {{
                        btnEl.disabled = false;
                        btnEl.innerText = "Retry Moodle Sync";
                        btnEl.className = "bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-2.5 py-1 rounded shadow-xs transition";
                    }}
                }}
            }}

            async function openSubmissionModal(submissionId) {{
                currentSubmissionModalId = submissionId;
                const modal = document.getElementById('modal-submission-detail');
                modal.classList.remove('hidden');

                document.getElementById('modal-student-name').innerText = "Loading...";
                document.getElementById('modal-code-display').innerText = "Loading code...";
                document.getElementById('modal-func-table').innerHTML = "";
                document.getElementById('modal-static-table').innerHTML = "";
                document.getElementById('modal-snapshot-buttons').innerHTML = "";
                document.getElementById('modal-timeline').innerHTML = "";

                try {{
                    const res = await fetch(`/lti/submissions/${{submissionId}}`);
                    if (!res.ok) throw new Error("Failed to load submission details");
                    const data = await res.json();

                    document.getElementById('modal-student-name').innerText = data.student_name || "Student";
                    document.getElementById('modal-student-email').innerText = data.student_email || "";
                    document.getElementById('modal-sub-id').innerText = "#" + data.submission_id;
                    document.getElementById('modal-sub-hash').innerText = data.submission_hash ? data.submission_hash.substring(0, 16) + '...' : 'N/A';
                    document.getElementById('modal-duration').innerText = (data.grading_duration_ms || 0) + " ms";

                    document.getElementById('modal-final-score').innerText = (data.final_score || 0) + "%";
                    document.getElementById('modal-func-score').innerText = (data.functional_score || 0) + " / 100 (Weight: " + data.functional_weight + "%)";
                    document.getElementById('modal-static-score').innerText = (data.static_score || 0) + " / 100 (Weight: " + data.static_weight + "%)";

                    window.activeModalCodePayload = data.submitted_code || "";
                    renderModalCodeDisplay(window.activeModalCodePayload, data.language);

                    const snapshots = data.snapshots || [];
                    const snapContainer = document.getElementById('modal-snapshot-buttons');
                    if (!snapshots.length) {{
                        snapContainer.innerHTML = '<span class="text-xs text-gray-400">No save snapshots.</span>';
                    }} else {{
                        snapContainer.innerHTML = snapshots.map((s, idx) => `
                            <button type="button" onclick="inspectSnapshotCode(${{idx}})" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-white text-xs font-mono transition">
                                v${{s.version}} (${{new Date(s.saved_at).toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit'}})}})
                            </button>
                        `).join('') + `
                            <button type="button" onclick="renderModalCodeDisplay(window.activeModalCodePayload, '${{data.language}}')" class="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition">
                                Final Submission
                            </button>
                        `;
                        window.activeModalSnapshots = snapshots;
                    }}

                    const funcResults = data.functional_results || [];
                    const funcTable = document.getElementById('modal-func-table');
                    if (!funcResults.length) {{
                        funcTable.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-xs text-gray-400">No test cases executed.</td></tr>';
                    }} else {{
                        funcTable.innerHTML = funcResults.map((tc, idx) => {{
                            const passed = tc.passed !== false && tc.status === 'passed';
                            const badge = passed ? '<span class="text-emerald-600 font-bold text-xs">PASS</span>' : '<span class="text-red-600 font-bold text-xs">FAIL</span>';
                            return `
                                <tr class="border-b border-gray-100 text-xs">
                                    <td class="py-2 px-3 font-semibold">Test Case ${{idx + 1}}</td>
                                    <td class="py-2 px-3 font-mono bg-gray-50">${{escapeHtml(tc.input || tc.input_data || 'None')}}</td>
                                    <td class="py-2 px-3 font-mono bg-gray-50">${{escapeHtml(tc.expected || tc.expected_output || '')}}</td>
                                    <td class="py-2 px-3 font-mono bg-gray-50">${{escapeHtml(tc.output || tc.actual_output || '')}}</td>
                                    <td class="py-2 px-3 font-semibold">${{tc.weight || 1.0}}</td>
                                    <td class="py-2 px-3">${{badge}}</td>
                                </tr>
                            `;
                        }}).join('');
                    }}

                    const staticResults = data.static_analysis || [];
                    const staticTable = document.getElementById('modal-static-table');
                    if (!staticResults.length) {{
                        staticTable.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-xs text-gray-400">No static rules configured.</td></tr>';
                    }} else {{
                        staticTable.innerHTML = staticResults.map(r => {{
                            const passed = Boolean(r.passed);
                            const badge = passed ? '<span class="text-emerald-400 font-bold text-xs">PASS</span>' : '<span class="text-red-400 font-bold text-xs">FAIL</span>';
                            return `
                                <tr class="border-b border-gray-700/60 text-xs text-gray-200 hover:bg-gray-700/40">
                                    <td class="py-2 px-3 font-semibold text-white">${{escapeHtml(r.rule_type || r.label || 'Rule')}}</td>
                                    <td class="py-2 px-3 font-mono text-gray-300">${{escapeHtml(String(r.expected_value ?? 'Required'))}}</td>
                                    <td class="py-2 px-3">${{badge}}</td>
                                    <td class="py-2 px-3 font-semibold text-gray-300">${{r.weight || 1.0}}</td>
                                    <td class="py-2 px-3 font-semibold text-emerald-400">${{r.earned || (passed ? (r.weight || 1.0) : 0)}}</td>
                                </tr>
                            `;
                        }}).join('');
                    }}

                    const timeline = data.timeline || [];
                    document.getElementById('modal-timeline').innerHTML = timeline.map(tl => `
                        <div class="flex items-center gap-3 text-xs">
                            <span class="font-mono text-gray-400">${{new Date(tl.time).toLocaleTimeString([], {{hour:'2-digit', minute:'2-digit', second:'2-digit'}})}}</span>
                            <span class="font-semibold text-gray-200">${{escapeHtml(tl.event)}}</span>
                        </div>
                    `).join('');

                    document.getElementById('modal-sync-status').innerText = (data.sync_status || 'pending').toUpperCase();
                    document.getElementById('modal-sync-message').innerText = data.sync_message || 'No telemetry message.';

                }} catch (err) {{
                    showToast("Failed to load submission detail: " + err.message, "error");
                }}
            }}

            function inspectSnapshotCode(idx) {{
                if (window.activeModalSnapshots && window.activeModalSnapshots[idx]) {{
                    const snap = window.activeModalSnapshots[idx];
                    renderModalCodeDisplay(snap.code, 'python');
                }}
            }}

            function renderModalCodeDisplay(codeText, lang) {{
                const el = document.getElementById('modal-code-display');
                const lines = (codeText || "").split(/\\r?\\n/);
                el.innerHTML = lines.map((line, idx) => {{
                    return `<div class="table-row"><span class="table-cell select-none text-slate-500 pr-4 text-right">${{idx + 1}}</span><span class="table-cell">${{escapeHtml(line)}}</span></div>`;
                }}).join('');
            }}

            function closeSubmissionModal() {{
                currentSubmissionModalId = null;
                document.getElementById('modal-submission-detail').classList.add('hidden');
            }}

            function exportResults(format) {{
                const examId = getCurrentExamId();
                if (!examId) {{
                    showToast("Please select an examination first.", "error");
                    return;
                }}
                window.open(`/lti/results/${{examId}}/export?format=${{format}}`, '_blank');
            }}
        </script>
    </body>
    </html>
    """
