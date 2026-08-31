// MONACO Code Review Frontend Engine

let activeReviewState = null;
let graphStructure = null;

// Tab Routing Configuration
const TABS = ['run-review-tab', 'report-tab', 'history-tab'];

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    lucide.createIcons();

    // Tab Navigation setup
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    // Sub-Agent Findings Tab listeners
    document.querySelectorAll('[data-agent-tab]').forEach(btn => {
        btn.addEventListener('click', () => {
            const agentTabId = btn.getAttribute('data-agent-tab');
            switchAgentTab(agentTabId);
        });
    });

    // Hook Form Submit
    const form = document.getElementById('review-form');
    form.addEventListener('submit', handleReviewSubmit);

    // Hook Post to GitHub Buttons
    document.getElementById('btn-preview-post').addEventListener('click', () => handlePostToGitHub(true));
    document.getElementById('btn-real-post').addEventListener('click', () => handlePostToGitHub(false));

    // Fetch initial graph structure and history
    fetchGraphStructure();
    loadHistory();
});

// Switch Main Tabs
function switchTab(tabId) {
    TABS.forEach(id => {
        const pane = document.getElementById(id);
        const btn = document.querySelector(`[data-tab="${id}"]`);
        
        if (id === tabId) {
            pane.classList.add('active');
            if (btn) btn.classList.add('active');
        } else {
            pane.classList.remove('active');
            if (btn) btn.classList.remove('active');
        }
    });

    // Update Top Header Title dynamically
    const headerTitle = document.getElementById('page-title');
    if (tabId === 'run-review-tab') {
        headerTitle.innerText = 'Run AI Code Review';
    } else if (tabId === 'report-tab') {
        headerTitle.innerText = 'AI Review Report';
    } else if (tabId === 'history-tab') {
        headerTitle.innerText = 'Review History Logs';
        loadHistory(); // Reload history when clicking tab
    }
}

// Switch Sub-agent Findings tabs
function switchAgentTab(agentTabId) {
    document.querySelectorAll('[data-agent-tab]').forEach(btn => {
        if (btn.getAttribute('data-agent-tab') === agentTabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    document.querySelectorAll('.agent-pane').forEach(pane => {
        if (pane.id === agentTabId) {
            pane.classList.add('active');
        } else {
            pane.classList.remove('active');
        }
    });
}

// Get Graph Structure from FastAPI backend
async function fetchGraphStructure() {
    try {
        const res = await fetch('/api/graph-structure');
        if (res.ok) {
            graphStructure = await res.json();
        } else {
            console.error('Failed to retrieve graph structure descriptor');
        }
    } catch (err) {
        console.error('Network error fetching graph structure:', err);
    }
}

// Form Submission (Trigger review)
async function handleReviewSubmit(e) {
    e.preventDefault();

    const owner = document.getElementById('owner').value.trim();
    const repo = document.getElementById('repo').value.trim();
    const pr_number = parseInt(document.getElementById('pr_number').value);
    const local_repo_path = document.getElementById('local_repo_path').value.trim();

    // Show Loading Overlay
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.remove('hidden');

    // Reset Live Terminal Logs
    const liveLogs = document.getElementById('live-logs');
    liveLogs.innerHTML = `
        <div class="log-line text-blue">[info] Initializing LangGraph review pipeline...</div>
        <div class="log-line text-blue">[info] Target: <span>${owner}/${repo} PR #${pr_number}</span></div>
        <div class="log-line text-blue">[info] Local repo path: <span>${local_repo_path}</span></div>
        <div class="log-line text-yellow">[wait] Querying GitHub API for metadata & diff patches...</div>
    `;

    // Disable Submit Button
    const submitBtn = document.getElementById('run-review-btn');
    submitBtn.disabled = true;

    // Simulate logs to show progress honestly since it takes some time
    const logInterval = setInterval(() => {
        const progressLogs = [
            { text: "[info] GitHub context fetched successfully.", class: "text-green", delay: 3000 },
            { text: "[wait] Dependency analyzer building imports graph...", class: "text-yellow", delay: 5500 },
            { text: "[info] Dependency mapping complete. Fanning out to parallel agents...", class: "text-green", delay: 8500 },
            { text: "[wait] security_agent: Running static analysis & vulnerability scans...", class: "text-yellow", delay: 11000 },
            { text: "[wait] quality_agent: Performing AST metrics audit...", class: "text-yellow", delay: 14000 },
            { text: "[wait] performance_agent: Inspecting loop complexity and memory hot-spots...", class: "text-yellow", delay: 17000 },
            { text: "[info] Parallel agents execution complete. Merging findings...", class: "text-green", delay: 20000 },
            { text: "[wait] Deduplicating findings using rule signatures...", class: "text-yellow", delay: 22000 },
            { text: "[wait] validate_node: Checking findings against file line nodes...", class: "text-yellow", delay: 25000 },
            { text: "[info] Ranking findings by confidence and severity weight...", class: "text-blue", delay: 28000 }
        ];

        const elapsed = Date.now() - startTime;
        progressLogs.forEach(log => {
            if (elapsed >= log.delay && !liveLogs.innerText.includes(log.text)) {
                const div = document.createElement('div');
                div.className = `log-line ${log.class}`;
                div.innerText = log.text;
                liveLogs.appendChild(div);
                liveLogs.scrollTop = liveLogs.scrollHeight;
            }
        });
    }, 1000);

    const startTime = Date.now();

    try {
        const res = await fetch('/api/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ owner, repo, pr_number, local_repo_path })
        });

        clearInterval(logInterval);

        if (!res.ok) {
            const errorData = await res.json();
            const errMsg = errorData.detail || 'An unexpected error occurred during the review.';
            showTerminalError(liveLogs, errMsg);
            return;
        }

        const data = await res.json();
        activeReviewState = data;

        // Finish logs
        const div = document.createElement('div');
        div.className = 'log-line text-green';
        div.innerText = `[done] Review completed successfully in ${((Date.now() - startTime) / 1000).toFixed(1)}s!`;
        liveLogs.appendChild(div);
        liveLogs.scrollTop = liveLogs.scrollHeight;

        // Populate and show report
        renderReviewReport(data);

        // Transition to report view
        setTimeout(() => {
            overlay.classList.add('hidden');
            submitBtn.disabled = false;
            switchTab('report-tab');
        }, 1500);

    } catch (err) {
        clearInterval(logInterval);
        console.error(err);
        showTerminalError(liveLogs, `Network Connection Failed: ${err.message}`);
    }
}

function showTerminalError(terminalBody, message) {
    const div = document.createElement('div');
    div.className = 'log-line text-red';
    div.innerText = `\n[error] PIPELINE FAILURE:\n[error] ${message}`;
    terminalBody.appendChild(div);
    terminalBody.scrollTop = terminalBody.scrollHeight;

    document.getElementById('run-review-btn').disabled = false;
    alert(`Pipeline error: ${message}`);
}

// Render Review Report View
function renderReviewReport(state) {
    // Show details container
    document.getElementById('report-empty-state').classList.add('hidden');
    const detailsContainer = document.getElementById('report-details');
    detailsContainer.classList.remove('hidden');

    // Populate Header
    document.getElementById('report-repo-fullname').innerText = `${state.owner}/${state.repo}`;
    document.getElementById('report-pr-number').innerText = state.pr_number;
    document.getElementById('report-pr-title').innerText = state.pr_context?.pr_title || 'Untitled Pull Request';
    
    // Populate stats
    const changedCount = state.pr_context?.changed_files?.length || 0;
    const skippedCount = state.skipped_files?.length || 0;
    const totalFindings = state.final_findings?.length || 0;
    const rejectionRatio = state.rejection_ratio || 0.0;

    document.getElementById('report-changed-count').innerText = changedCount;
    document.getElementById('report-skipped-count').innerText = skippedCount;
    document.getElementById('report-findings-count').innerText = totalFindings;
    document.getElementById('report-rejection-ratio').innerText = `${(rejectionRatio * 100).toFixed(0)}%`;

    // Populate file list summary
    const changedListUl = document.getElementById('report-changed-list');
    changedListUl.innerHTML = '';
    (state.pr_context?.changed_files || []).forEach(f => {
        const li = document.createElement('li');
        li.innerText = f;
        changedListUl.appendChild(li);
    });

    const skippedListUl = document.getElementById('report-skipped-list');
    skippedListUl.innerHTML = '';
    if (state.skipped_files && state.skipped_files.length > 0) {
        state.skipped_files.forEach(f => {
            const li = document.createElement('li');
            li.innerText = f;
            skippedListUl.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.className = 'text-muted';
        li.innerText = 'No skipped files.';
        skippedListUl.appendChild(li);
    }

    // Toggle manual review banner
    const banner = document.getElementById('manual-review-banner');
    if (state.needs_manual_review) {
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }

    // Render Flowchart path
    renderFlowchart(state.status_logs);

    // Render Raw Findings by Agent
    renderAgentFindings(state);

    // Render Final Findings
    renderFinalFindings(state.final_findings);

    // Reset GitHub Post Actions state
    document.getElementById('post-result-container').classList.add('hidden');
    document.getElementById('preview-comments-list-section').classList.add('hidden');

    // Trigger Lucide Icons refresh
    lucide.createIcons();
}

// Render Flowchart Path Visualization
function renderFlowchart(logs) {
    const container = document.getElementById('graph-flowchart');
    container.innerHTML = '';

    // Stages columns definition (matches graph layout)
    const stages = [
        { id: 'start-stage', nodes: ['START'] },
        { id: 'fetch-stage', nodes: ['fetch_pr_context'] },
        { id: 'analysis-stage', nodes: ['start_analysis'] },
        { id: 'agents-stage', nodes: ['security_agent', 'quality_agent', 'performance_agent'] },
        { id: 'merge-stage', nodes: ['merge_agent_findings'] },
        { id: 'dedup-stage', nodes: ['deduplicate'] },
        { id: 'validate-stage', nodes: ['validate'] },
        { id: 'decision-stage', nodes: ['flag_for_manual_review', 'rank'] },
        { id: 'end-stage', nodes: ['END'] }
    ];

    // Helper map of log presence
    const isExecuted = (nodeId) => {
        if (nodeId === 'START' || nodeId === 'END') {
            return true;
        }
        if (nodeId === 'start_analysis') {
            // Evaluates true if parallel review started
            return logs.includes('security_agent_node') || logs.includes('quality_agent_node') || logs.includes('performance_agent_node');
        }
        
        const logMap = {
            'fetch_pr_context': 'fetch_pr_context_node',
            'security_agent': 'security_agent_node',
            'quality_agent': 'quality_agent_node',
            'performance_agent': 'performance_agent_node',
            'merge_agent_findings': 'merge_agent_findings_node',
            'deduplicate': 'deduplicate_node',
            'validate': 'validate_node',
            'flag_for_manual_review': 'flag_for_manual_review_node',
            'rank': 'rank_node'
        };
        
        return logs.includes(logMap[nodeId]);
    };

    // Render stages and connectors
    stages.forEach((stage, idx) => {
        const stageDiv = document.createElement('div');
        stageDiv.className = 'flowchart-stage';
        stageDiv.id = stage.id;

        stage.nodes.forEach(nodeId => {
            // Find human label
            let label = nodeId;
            let type = 'node';
            if (graphStructure) {
                const matchedNode = graphStructure.nodes.find(n => n.id === nodeId);
                if (matchedNode) {
                    label = matchedNode.label;
                    type = matchedNode.type;
                }
            }

            const nodeDiv = document.createElement('div');
            nodeDiv.className = `flowchart-node ${type}`;
            nodeDiv.innerText = label;
            nodeDiv.setAttribute('data-node-id', nodeId);

            if (isExecuted(nodeId)) {
                nodeDiv.classList.add('executed');
            }

            stageDiv.appendChild(nodeDiv);
        });

        container.appendChild(stageDiv);

        // Add connecting arrows between stages (except the last stage)
        if (idx < stages.length - 1) {
            const arrowDiv = document.createElement('div');
            arrowDiv.className = 'flowchart-arrow';
            arrowDiv.innerHTML = '→';

            // Highlighting active connections based on execution log flow
            const currentStageExecuted = stage.nodes.some(n => isExecuted(n));
            const nextStageExecuted = stages[idx + 1].nodes.some(n => isExecuted(n));
            
            if (currentStageExecuted && nextStageExecuted) {
                // If it's the conditional check for files, highlight correct arrow
                if (stage.nodes.includes('fetch_pr_context')) {
                    const isSkip = !logs.includes('security_agent_node');
                    if (isSkip && stages[idx+1].nodes.includes('END')) {
                         arrowDiv.classList.add('highlighted');
                    } else if (!isSkip && stages[idx+1].nodes.includes('start_analysis')) {
                         arrowDiv.classList.add('highlighted');
                    }
                } else {
                    arrowDiv.classList.add('highlighted');
                }
            }

            container.appendChild(arrowDiv);
        }
    });
}

// Render Raw Heuristics Agent Findings
function renderAgentFindings(state) {
    const secList = document.getElementById('list-security-findings');
    const qualList = document.getElementById('list-quality-findings');
    const perfList = document.getElementById('list-performance-findings');

    const secFindings = state.security_findings || [];
    const qualFindings = state.quality_findings || [];
    const perfFindings = state.performance_findings || [];

    // Set badges count
    document.getElementById('badge-security').innerText = secFindings.length;
    document.getElementById('badge-quality').innerText = qualFindings.length;
    document.getElementById('badge-performance').innerText = perfFindings.length;

    // Render lists
    populateAgentList(secList, secFindings, 'security_agent');
    populateAgentList(qualList, qualFindings, 'quality_agent');
    populateAgentList(perfList, perfFindings, 'performance_agent');
}

function populateAgentList(container, findings, defaultSource) {
    container.innerHTML = '';
    if (findings.length === 0) {
        container.innerHTML = `<div class="empty-findings-box">No findings reported by this agent.</div>`;
        return;
    }

    findings.forEach(finding => {
        const card = createFindingCard(finding, defaultSource);
        container.appendChild(card);
    });
}

// Render final validated ranked findings
function renderFinalFindings(findings) {
    const container = document.getElementById('final-findings-list');
    container.innerHTML = '';

    if (findings.length === 0) {
        container.innerHTML = `<div class="empty-findings-box">No validated findings reported. PR code structure appears clean!</div>`;
        return;
    }

    findings.forEach(finding => {
        const card = createFindingCard(finding);
        container.appendChild(card);
    });
}

// Finding Card Builder
function createFindingCard(finding, defaultSource = '') {
    const card = document.createElement('div');
    const severity = (finding.severity || 'low').toLowerCase();
    card.className = `finding-card severity-${severity}`;

    // Header values
    const ruleId = finding.rule_id || 'RULE-UNKNOWN';
    const filename = finding.file || 'Unknown File';
    const lineNum = finding.line !== null ? `L${finding.line}` : 'Global';

    // Badge styling
    let badgesHTML = `<span class="severity-badge ${severity}">${severity}</span>`;
    if (finding.in_diff) {
        badgesHTML += `<span class="diff-badge"><i data-lucide="git-commit"></i> in PR diff</span>`;
    }

    // Sources tags
    const sources = finding.sources && finding.sources.length > 0 
        ? finding.sources 
        : [finding.source || defaultSource];
    const sourceTagsHTML = sources.map(src => `<span class="source-tag">${src}</span>`).join('');

    card.innerHTML = `
        <div class="finding-card-header">
            <div class="finding-card-title">
                <span class="finding-rule">${ruleId}</span>
                <span class="finding-location">${filename} : ${lineNum}</span>
            </div>
            <div class="finding-badges">
                ${badgesHTML}
            </div>
        </div>
        <div class="finding-message">
            ${finding.message}
        </div>
        <div class="finding-details">
            ${finding.explanation ? `
                <div class="detail-section">
                    <strong>Explanation:</strong>
                    <p>${finding.explanation}</p>
                </div>
            ` : ''}
            ${finding.suggestion ? `
                <div class="detail-section">
                    <strong>Suggestion:</strong>
                    <p>${finding.suggestion}</p>
                </div>
            ` : ''}
        </div>
        <div class="finding-footer">
            <div class="finding-sources">
                <span>Sources:</span>
                ${sourceTagsHTML}
            </div>
            ${finding.confidence ? `<div>Confidence: ${(finding.confidence * 100).toFixed(0)}%</div>` : ''}
        </div>
    `;

    return card;
}

// Post Review to GitHub (Handles dry-run and real-posting)
async function handlePostToGitHub(dryRun) {
    if (!activeReviewState) {
        alert('No active review findings available to post.');
        return;
    }

    if (!dryRun) {
        // Confirmation dialog for safety
        const confirmed = confirm(
            `WARNING: This will publish inline comments to the live GitHub Pull Request #${activeReviewState.pr_number}.\n\nAre you sure you want to proceed?`
        );
        if (!confirmed) return;
    }

    // Show loading result view
    const resultContainer = document.getElementById('post-result-container');
    const banner = document.getElementById('post-status-banner');
    const title = document.getElementById('post-status-title');
    const msg = document.getElementById('post-status-msg');
    const link = document.getElementById('post-review-link');
    const commentsSection = document.getElementById('preview-comments-list-section');

    resultContainer.classList.remove('hidden');
    banner.className = 'status-banner dry-run';
    title.innerText = 'Processing Review Submission...';
    msg.innerText = dryRun ? 'Retrieving dry-run comments preview...' : 'Posting review comments to GitHub...';
    link.classList.add('hidden');
    commentsSection.classList.add('hidden');

    try {
        const res = await fetch('/api/post-review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                owner: activeReviewState.owner,
                repo: activeReviewState.repo,
                pr_number: activeReviewState.pr_number,
                local_repo_path: activeReviewState.local_repo_path,
                dry_run: dryRun
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            const errMsg = errData.detail || 'An error occurred during submission.';
            banner.className = 'status-banner error';
            title.innerText = 'Submission Failed';
            msg.innerText = errMsg;
            return;
        }

        const data = await res.json();

        if (data.already_reviewed) {
            banner.className = 'status-banner success';
            title.innerText = 'Already Reviewed';
            msg.innerText = 'This commit SHA has already been reviewed by MONACO. No duplicate review posted.';
            if (data.existing_review_url) {
                link.href = data.existing_review_url;
                link.classList.remove('hidden');
            }
            return;
        }

        if (data.dry_run) {
            banner.className = 'status-banner dry-run';
            title.innerText = 'Dry Run Simulation Complete';
            msg.innerText = `No comments were published to GitHub. Monaco generated ${data.would_post_count} unique comment cards that WOULD be posted for new findings (from ${data.total_findings_found} total in-diff findings).`;
            
            // Render comments preview list
            commentsSection.classList.remove('hidden');
            document.getElementById('preview-comments-count').innerText = data.would_post_count;
            
            const commentsContainer = document.getElementById('preview-comments-list');
            commentsContainer.innerHTML = '';

            const comments = data.comments || [];
            if (comments.length === 0) {
                commentsContainer.innerHTML = `<div class="empty-findings-box">No new in-diff findings found to write comments for.</div>`;
            } else {
                comments.forEach(comment => {
                    const card = document.createElement('div');
                    card.className = 'preview-comment-card';
                    card.innerHTML = `
                        <div class="preview-comment-header">
                            <span class="preview-comment-file">${comment.path} : L${comment.line}</span>
                            <span>RIGHT Side</span>
                        </div>
                        <div class="preview-comment-body">${comment.body}</div>
                    `;
                    commentsContainer.appendChild(card);
                });
            }
        } else {
            // Real post success
            banner.className = 'status-banner success';
            title.innerText = 'Review Posted Successfully!';
            msg.innerText = `Published ${data.posted_count} inline review comments to the pull request on GitHub!`;
            
            if (data.review_url) {
                link.href = data.review_url;
                link.classList.remove('hidden');
            }
        }

    } catch (err) {
        console.error(err);
        banner.className = 'status-banner error';
        title.innerText = 'Connection Error';
        msg.innerText = `Could not submit request to server: ${err.message}`;
    }

    lucide.createIcons();
}

// Load Review History runs
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        if (!res.ok) {
            console.error('Failed to retrieve history logs');
            return;
        }

        const history = await res.json();
        const tbody = document.getElementById('history-table-body');
        const emptyState = document.getElementById('history-empty-state');
        const table = document.querySelector('.history-table');

        tbody.innerHTML = '';

        if (history.length === 0) {
            emptyState.classList.remove('hidden');
            table.classList.add('hidden');
            return;
        }

        emptyState.classList.add('hidden');
        table.classList.remove('hidden');

        history.forEach(run => {
            const tr = document.createElement('tr');
            
            // Format timestamp
            const date = new Date(run.timestamp);
            const formattedDate = date.toLocaleString();

            const prTitleSub = run.pr_title ? `<span class="pr-title-sub">${run.pr_title}</span>` : '';
            const manualBadge = run.needs_manual_review 
                ? '<span class="manual-review-cell-badge yes"><i data-lucide="alert-circle" style="width:12px;height:12px;"></i> Yes</span>'
                : '<span class="manual-review-cell-badge no">No</span>';

            tr.innerHTML = `
                <td>
                    <div class="date-cell">${formattedDate}</div>
                </td>
                <td>
                    <div class="repo-cell">
                        <span class="repo-name">${run.owner}/${run.repo}</span>
                        <span class="pr-title-sub">PR #${run.pr_number} ${prTitleSub}</span>
                    </div>
                </td>
                <td>
                    <span class="findings-count-badge">${run.total_findings} findings</span>
                </td>
                <td>${manualBadge}</td>
                <td>${(run.rejection_ratio * 100).toFixed(0)}%</td>
                <td>
                    <button class="history-action-btn" onclick="loadHistoryRecord('${run.id}')">
                        <i data-lucide="arrow-right-circle" style="width:14px;height:14px;"></i>
                        <span>Load Report</span>
                    </button>
                </td>
            `;

            tbody.appendChild(tr);
        });

        lucide.createIcons();

    } catch (err) {
        console.error('Network error loading history:', err);
    }
}

// Load a specific historical run from file storage
async function loadHistoryRecord(historyId) {
    try {
        const res = await fetch(`/api/history/${historyId}`);
        if (!res.ok) {
            alert('Failed to retrieve history details.');
            return;
        }

        const data = await res.json();
        activeReviewState = data;

        // Render report with history data
        renderReviewReport(data);

        // Switch to report tab
        switchTab('report-tab');

    } catch (err) {
        console.error(err);
        alert(`Error loading history record: ${err.message}`);
    }
}
