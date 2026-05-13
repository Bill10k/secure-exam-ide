def get_instructor_dashboard_html(id_token: str, exams: list):
    options_html = ""
    for exam in exams:
        options_html += f'<option value="{exam.exam_id}">{exam.title} (Duration: {exam.duration}m)</option>'
        
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ProctorIDE Instructor Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            let currentExamId = null;
            let currentQuestionId = null;

            function showTab(tabId) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
                document.getElementById(tabId).classList.remove('hidden');
                
                document.querySelectorAll('.tab-btn').forEach(el => {{
                    el.classList.remove('border-blue-500', 'text-blue-600');
                    el.classList.add('border-transparent', 'text-gray-500');
                }});
                document.getElementById('btn-' + tabId).classList.remove('border-transparent', 'text-gray-500');
                document.getElementById('btn-' + tabId).classList.add('border-blue-500', 'text-blue-600');
            }}

            async function createExam(e) {{
                e.preventDefault();
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.innerText = "Creating...";

                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                data.duration = parseInt(data.duration);
                
                try {{
                    const res = await fetch('/api/launch/api/exam', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }});
                    const result = await res.json();
                    if (res.ok) {{
                        currentExamId = result.exam_id;
                        document.getElementById('exam-creation-step').classList.add('hidden');
                        document.getElementById('question-creation-step').classList.remove('hidden');
                        document.getElementById('display-exam-title').innerText = "Exam: " + result.title;
                    }} else {{
                        alert("Error: " + JSON.stringify(result));
                        btn.disabled = false;
                        btn.innerText = "Create & Continue to Questions \u2192";
                    }}
                }} catch (err) {{
                    alert("Network error: " + err);
                    btn.disabled = false;
                    btn.innerText = "Create & Continue to Questions \u2192";
                }}
            }}

            async function addQuestion(e) {{
                e.preventDefault();
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.innerText = "Saving Question...";

                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                data.exam_id = currentExamId;
                data.diff_level = parseInt(data.diff_level);
                
                try {{
                    const res = await fetch('/api/launch/api/question', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }});
                    const result = await res.json();
                    if (res.ok) {{
                        currentQuestionId = result.question_id;
                        document.getElementById('question-list').innerHTML += `<li class="text-sm py-1">✅ ${{result.title}}</li>`;
                        e.target.reset();
                        
                        document.getElementById('question-editor-wrapper').classList.add('hidden');
                        document.getElementById('testcase-creation-step').classList.remove('hidden');
                        document.getElementById('display-question-title').innerText = "Test Cases for: " + result.title;
                    }} else {{
                        alert("Error: " + JSON.stringify(result));
                    }}
                }} catch (err) {{ alert("Network error: " + err); }}
                finally {{
                    btn.disabled = false;
                    btn.innerText = "Save Question";
                }}
            }}

            async function addTestCase(e) {{
                e.preventDefault();
                const btn = e.target.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.innerText = "Adding...";

                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                data.question_id = currentQuestionId;
                data.is_hidden = formData.has("is_hidden");
                data.weight = parseFloat(data.weight || 1.0);
                
                try {{
                    const res = await fetch('/api/launch/api/testcase', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }});
                    if (res.ok) {{
                        document.getElementById('testcase-list').innerHTML += `<span class="bg-gray-200 text-xs px-2 py-1 rounded inline-block mr-2 mb-2">Test Case Added</span>`;
                        e.target.reset();
                    }} else {{
                        alert("Error adding test case.");
                    }}
                }} catch (err) {{ alert("Network error"); }}
                finally {{
                    btn.disabled = false;
                    btn.innerText = "Add Test Case";
                }}
            }}

            function doneWithTestCases() {{
                document.getElementById('testcase-creation-step').classList.add('hidden');
                document.getElementById('question-editor-wrapper').classList.remove('hidden');
                document.getElementById('testcase-list').innerHTML = "";
            }}

            function doneWithExam() {{
                // Refresh to inject new exam to the list!
                window.location.reload();
            }}
        </script>
    </head>
    <body class="bg-gray-50 h-screen font-sans">
        <div class="max-w-4xl mx-auto mt-10 bg-white rounded-lg shadow-md overflow-hidden">
            <div class="border-b border-gray-200">
                <nav class="-mb-px flex">
                    <button id="btn-tab-link" onclick="showTab('tab-link')" class="tab-btn w-1/3 py-4 px-1 text-center border-b-2 font-medium text-sm border-blue-500 text-blue-600">
                        Link Existing Exam
                    </button>
                    <button id="btn-tab-create" onclick="showTab('tab-create')" class="tab-btn w-1/3 py-4 px-1 text-center border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300">
                        Create New Exam
                    </button>
                    <button id="btn-tab-results" onclick="showTab('tab-results')" class="tab-btn w-1/3 py-4 px-1 text-center border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300">
                        Lecturer Results
                    </button>
                </nav>
            </div>

            <!-- Tab 1: Link Existing -->
            <div id="tab-link" class="tab-content p-6">
                <h2 class="text-xl font-bold mb-4 text-gray-800">Select Exam for Course</h2>
                <form action="/api/launch/deep-link/submit" method="POST" class="space-y-4">
                    <input type="hidden" name="id_token" value="{id_token}" />
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Available Exams</label>
                        <select name="exam_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md border">
                            <option value="">-- Choose an exam --</option>
                            {options_html}
                        </select>
                    </div>
                    <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
                        Link Exam to Course
                    </button>
                </form>
            </div>

            <!-- Tab 2: Lecturer Results -->
            <div id="tab-results" class="tab-content p-6 hidden">
                <h2 class="text-xl font-bold mb-4 text-gray-800">View Lecturer Results</h2>
                <p class="text-sm text-gray-600 mb-4">Open submissions and grades inside Moodle for the selected exam.</p>
                <form action="/api/launch/results" method="POST" class="space-y-4">
                    <input type="hidden" name="id_token" value="{id_token}" />
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Exam</label>
                        <select name="exam_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md border">
                            <option value="">-- Choose an exam --</option>
                            {options_html}
                        </select>
                    </div>
                    <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-slate-700 hover:bg-slate-800">
                        View Results in Moodle
                    </button>
                </form>
            </div>

            <!-- Tab 3: Create New (Dynamic wizard) -->
            <div id="tab-create" class="tab-content p-6 hidden">
                
                <!-- STEP 1: EXAM -->
                <div id="exam-creation-step">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">Design New Exam</h2>
                    <form onsubmit="createExam(event)" class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Exam Title</label>
                            <input type="text" name="title" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Description</label>
                            <textarea name="description" rows="2" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"></textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Duration (Minutes)</label>
                            <input type="number" name="duration" value="60" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm">
                        </div>
                        <div class="pt-4 border-t border-gray-200">
                            <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700">
                                Create & Continue to Questions \u2192
                            </button>
                        </div>
                    </form>
                </div>

                <!-- STEP 2: QUESTIONS -->
                <div id="question-creation-step" class="hidden">
                    <div class="flex justify-between items-center mb-4 pb-2 border-b border-gray-200">
                        <h2 id="display-exam-title" class="text-xl font-bold text-gray-800">Exam: </h2>
                        <button type="button" onclick="doneWithExam()" class="text-sm bg-gray-200 px-3 py-1 rounded hover:bg-gray-300 text-gray-800 bg-blue-100 text-blue-800 border border-blue-200 font-semibold">Done with Exam</button>
                    </div>

                    <div class="flex gap-6">
                        <!-- Sidebar for created questions -->
                        <div class="w-1/3 bg-gray-50 border border-gray-200 rounded p-3 h-96 overflow-y-auto">
                            <h3 class="text-sm font-bold border-b pb-2 mb-2 text-gray-600 uppercase">Questions Built</h3>
                            <ul id="question-list" class="list-none m-0 p-0 text-gray-700">
                            </ul>
                        </div>
                        
                        <!-- Question Builder Form -->
                        <div class="w-2/3" id="question-editor-wrapper">
                            <h3 class="text-lg font-bold mb-3 text-gray-700">Add a Programming Question</h3>
                            <form onsubmit="addQuestion(event)" class="space-y-3">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">Question Title</label>
                                    <input type="text" name="title" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded sm:text-sm">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">Description / Prompt</label>
                                    <textarea name="description" rows="3" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded sm:text-sm"></textarea>
                                </div>
                                <div class="flex gap-4">
                                    <div class="w-1/2">
                                        <label class="block text-sm font-medium text-gray-700">Difficulty</label>
                                        <select name="diff_level" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded sm:text-sm">
                                            <option value="1">1 - Easy</option>
                                            <option value="2">2 - Medium</option>
                                            <option value="3">3 - Hard</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">Default Code / Boilerplate</label>
                                    <textarea name="default_code" rows="3" class="font-mono mt-1 block w-full px-3 py-2 border border-gray-300 rounded sm:text-sm">def solution():\n    pass</textarea>
                                </div>
                                <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
                                    Save Question
                                </button>
                            </form>
                        </div>

                        <!-- STEP 3: TEST CASES (shows after question is saved) -->
                        <div class="w-2/3 hidden" id="testcase-creation-step">
                            <h3 id="display-question-title" class="text-lg font-bold mb-3 text-gray-700">Test Cases</h3>
                            <div id="testcase-list" class="mb-3"></div>
                            
                            <form onsubmit="addTestCase(event)" class="space-y-3 p-4 bg-yellow-50 border border-yellow-200 rounded">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">Input Data (Arguments / STDIN)</label>
                                    <textarea name="input_data" required rows="2" class="font-mono mt-1 block w-full px-3 py-1 border border-gray-300 rounded text-sm"></textarea>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700">Expected Output</label>
                                    <textarea name="expected_output" required rows="2" class="font-mono mt-1 block w-full px-3 py-1 border border-gray-300 rounded text-sm"></textarea>
                                </div>
                                <div class="flex items-center gap-4">
                                    <label class="flex items-center text-sm">
                                        <input type="checkbox" name="is_hidden" class="mr-2" checked> Hidden from student
                                    </label>
                                    <label class="flex items-center text-sm">
                                        Weight: <input type="number" step="0.1" name="weight" value="1.0" class="ml-2 w-16 border rounded px-1 py-1">
                                    </label>
                                </div>
                                <button type="submit" class="w-full bg-yellow-400 hover:bg-yellow-500 text-yellow-900 font-bold py-1.5 rounded text-sm transition transition-colors">
                                    Add Test Case
                                </button>
                            </form>
                            <button type="button" onclick="doneWithTestCases()" class="mt-4 w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 rounded text-sm">
                                Done Adding Test Cases (Next Question)
                            </button>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </body>
    </html>
    """
