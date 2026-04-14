// Utility to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Fetch list of reports for index page
async function loadReports(filters = {}) {
    const body = document.getElementById('reportsTableBody');
    if (!body) return;

    try {
        // Build query string
        const params = new URLSearchParams();
        if (filters.title) params.append('title', filters.title);
        if (filters.dateFrom) params.append('date_from', filters.dateFrom);
        if (filters.dateTo) params.append('date_to', filters.dateTo);

        const url = `/api/reports${params.toString() ? '?' + params.toString() : ''}`;
        const response = await fetch(url);
        const reports = await response.json();

        if (!reports || reports.length === 0) {
            body.innerHTML = '';
            document.getElementById('noDataMessage').style.display = 'block';
            // Reset stats if no data
            document.getElementById('totalAnalyzed').innerText = '0';
            document.getElementById('successRate').innerText = '0%';
            document.getElementById('successProgress').style.width = '0%';
            document.getElementById('criticalErrors').innerText = '0';
            return;
        }

        document.getElementById('noDataMessage').style.display = 'none';
        body.innerHTML = '';
        reports.forEach(report => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 700;">${report.title || report.trace_id}</div>
                    <div style="font-size: 11px; color: #86868b;"><i class="fa-solid fa-server"></i> Host: ${report.host || 'Unknown'} | Files: ${report.total_lines || 0} Lines</div>
                </td>
                <td>${formatDate(report.date_generated)}</td>
                <td><span class="badge ${report.status === 'SUCCESS' ? 'badge-success' : 'badge-error'}">${report.status}</span></td>
                <td><span style="font-size: 12px; font-weight: 500;">${report.llm_model}</span></td>
                <td><span class="badge ${report.severity === 'Critical' ? 'badge-error' : 'badge-warning'}">${report.severity}</span></td>
                <td>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        <a href="details.html?id=${report.trace_id}" class="view-btn">VIEW <i class="fa-solid fa-chevron-right" style="font-size: 10px;"></i></a>
                        <button onclick="deleteReport('${report.id}')" class="delete-btn" title="Delete Report">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </td>
            `;
            body.appendChild(tr);
        });

        // Update stats
        document.getElementById('totalAnalyzed').innerText = reports.length;
        const successCount = reports.filter(r => r.status === 'SUCCESS').length;
        const rate = reports.length > 0 ? Math.round((successCount / reports.length) * 100) : 0;
        document.getElementById('successRate').innerText = `${rate}%`;
        document.getElementById('successProgress').style.width = `${rate}%`;
        document.getElementById('criticalErrors').innerText = reports.filter(r => r.severity === 'Critical').length;
    } catch (error) {
        console.error("Error loading reports:", error);
    }
}

// Delete report function
async function deleteReport(id) {
    if (!confirm("Are you sure you want to delete this report? This action cannot be undone.")) {
        return;
    }

    try {
        const response = await fetch(`/api/reports/${id}/delete`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.status === 'success') {
            loadReports(); // Refresh the list
        } else {
            alert("Error deleting report: " + result.message);
        }
    } catch (error) {
        console.error("Delete request failed:", error);
        alert("Delete request failed. Check console for details.");
    }
}

// Fetch report details for details page
async function loadReportDetails(traceId) {
    try {
        const response = await fetch(`/api/reports/${traceId}`);
        const report = await response.json();

        // Update basic info
        document.getElementById('detailTitle').innerText = report.title || `Trace ID #${report.trace_id}`;
        document.getElementById('llmModelName').innerText = report.llm_model;

        // Update Metadata section
        if (document.getElementById('metaHost')) {
            document.getElementById('metaHost').innerText = report.host || 'Unknown';
            document.getElementById('metaLogFile').innerText = report.log_file || 'N/A';
            document.getElementById('metaTimeRange').innerText = `${report.since || '-'} ~ ${report.until || '-'}`;
            document.getElementById('metaUnit').innerText = report.unit || '';
            document.getElementById('metaTokens').innerText = (report.tokens_used || 0).toLocaleString();
            document.getElementById('metaChunks').innerText = (report.chunks_analyzed || 0).toLocaleString();
            document.getElementById('metaLines').innerText = (report.total_lines || 0).toLocaleString();
            document.getElementById('metaMatches').innerText = (report.match_count || 0).toLocaleString();
            document.getElementById('metaHash').innerText = report.log_hash || 'N/A';
        }
        
        // Detailed Analysis Result (Markdown)
        const detailedContent = document.getElementById('detailedAnalysisContent');
        if (detailedContent && report.result) {
            // Using marked.js to parse markdown
            detailedContent.innerHTML = marked.parse(report.result);
            detailedContent.style.whiteSpace = 'normal'; // Reset pre-wrap for rendered HTML
        } else if (detailedContent) {
            detailedContent.innerText = "No detailed report provided.";
        }
        
        const sevBadge = document.getElementById('severityBadge');
        const severity = report.severity || "Low";
        sevBadge.innerText = severity.toUpperCase();
        sevBadge.className = severity === 'Critical' ? 'badge badge-error' : 'badge badge-warning';

        document.getElementById('summaryEvents').innerText = (report.total_events || 0).toLocaleString();
        document.getElementById('summaryDuration').innerText = report.duration || "N/A";
        document.getElementById('summaryNodes').innerText = report.affected_nodes || 0;

        // Logs
        const logContainer = document.getElementById('logItemsContainer');
        logContainer.innerHTML = '';
        report.log_entries.forEach(entry => {
            const item = document.createElement('div');
            item.className = 'log-item';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="display: flex; gap: 16px; font-size: 13px;">
                        <span style="color: var(--text-secondary);">${entry.timestamp}</span>
                        <span style="font-weight: 700;">${entry.source}</span>
                        <span class="badge ${entry.status.includes('OK') ? 'badge-success' : 'badge-error'}">${entry.status}</span>
                    </div>
                </div>
                <p style="font-size: 14px; color: var(--text-main);">${entry.message}</p>
                ${entry.stack_trace ? `<pre class="stack-trace">${entry.stack_trace}</pre>` : ''}
                <div style="margin-top: 12px; display: flex; gap: 24px; font-size: 12px; color: var(--text-secondary);">
                    <span>Node ID: ${entry.metadata_info?.node_id || '-'}</span>
                    <span>Client IP: ${entry.metadata_info?.client_ip || '-'}</span>
                    <span>Protocol: ${entry.metadata_info?.protocol || '-'}</span>
                    <span style="color: var(--error)">Latency: ${entry.metadata_info?.latency || '-'}</span>
                </div>
            `;
            logContainer.appendChild(item);
        });

        // Charts
        if (report.error_distribution) {
            renderChart(report.error_distribution);
        }

    } catch (error) {
        console.error("Error loading report details:", error);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('errorChart').getContext('2d');
    const labels = Object.keys(data);
    const values = Object.values(data);
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#ff3b30', '#34c759', '#007aff', '#ff9500', '#5856d6'],
                borderWidth: 0,
                borderRadius: 5,
                cutout: '70%',
            }]
        },
        options: {
            plugins: { legend: { display: false } },
            maintainAspectRatio: false
        }
    });

    // Custom Legend
    const legend = document.getElementById('errorLegend');
    legend.innerHTML = '';
    labels.forEach((label, i) => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.fontSize = '13px';
        li.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 8px; height: 8px; border-radius: 50%; background: ${['#ff3b30', '#34c759', '#007aff', '#ff9500', '#5856d6'][i]}"></div>
                ${label}
            </div>
            <span style="font-weight: 700; color: var(--text-secondary);">${values[i]}%</span>
        `;
        legend.appendChild(li);
    });
}

// Initial load for index
if (document.getElementById('reportsTableBody')) {
    loadReports();

    // --- Search Toggle & Logic ---
    const searchNav = document.getElementById('searchNav');
    const searchPanel = document.getElementById('searchPanel');
    const applySearchBtn = document.getElementById('applySearchBtn');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    
    // UI Toggle
    if (searchNav && searchPanel) {
        searchNav.onclick = () => {
            searchPanel.classList.toggle('visible');
            searchNav.classList.toggle('active');
        };
    }

    // Apply Filter
    if (applySearchBtn) {
        applySearchBtn.onclick = () => {
            const filters = {
                title: document.getElementById('searchTitle').value,
                dateFrom: document.getElementById('searchDateFrom').value,
                dateTo: document.getElementById('searchDateTo').value
            };
            loadReports(filters);
        };
    }

    // Clear Filter
    if (clearSearchBtn) {
        clearSearchBtn.onclick = () => {
            document.getElementById('searchTitle').value = '';
            document.getElementById('searchDateFrom').value = '';
            document.getElementById('searchDateTo').value = '';
            loadReports();
        };
    }

    // --- Settings View Logic ---
    const settingsNav = document.getElementById('settingsNav');
    const reportsView = document.getElementById('reportsView');
    const settingsView = document.getElementById('settingsView');
    const dashboardNav = document.getElementById('dashboardNav');

    if (settingsNav && reportsView && settingsView) {
        settingsNav.onclick = (e) => {
            e.preventDefault();
            reportsView.style.display = 'none';
            settingsView.style.display = 'block';
            
            // UI state
            settingsNav.classList.add('active');
            if (dashboardNav) dashboardNav.classList.remove('active');
            if (searchPanel) searchPanel.classList.remove('visible');
            if (searchNav) searchNav.classList.remove('active');
        };
    }

    if (dashboardNav && reportsView && settingsView) {
        dashboardNav.onclick = (e) => {
            e.preventDefault();
            reportsView.style.display = 'block';
            settingsView.style.display = 'none';
            
            // UI state
            dashboardNav.classList.add('active');
            if (settingsNav) settingsNav.classList.remove('active');
            loadReports(); // Refresh data when coming back
        };
    }
}
