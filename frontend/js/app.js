// Utility to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Fetch list of reports for index page
async function loadReports() {
    const body = document.getElementById('reportsTableBody');
    if (!body) return;

    try {
        const response = await fetch('/api/reports');
        const reports = await response.json();

        if (reports.length === 0) {
            document.getElementById('noDataMessage').style.display = 'block';
            return;
        }

        body.innerHTML = '';
        reports.forEach(report => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 700;">${report.trace_id}</div>
                    <div style="font-size: 11px; color: #86868b;">Cluster: ${report.affected_nodes} Nodes</div>
                </td>
                <td>${formatDate(report.date_generated)}</td>
                <td><span class="badge ${report.status === 'SUCCESS' ? 'badge-success' : 'badge-error'}">${report.status}</span></td>
                <td><span style="font-size: 12px; font-weight: 500;">${report.llm_model}</span></td>
                <td><span class="badge ${report.severity === 'Critical' ? 'badge-error' : 'badge-warning'}">${report.severity}</span></td>
                <td><a href="details.html?id=${report.trace_id}" class="view-btn">VIEW DETAILS <i class="fa-solid fa-chevron-right" style="font-size: 10px;"></i></a></td>
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

// Fetch report details for details page
async function loadReportDetails(traceId) {
    try {
        const response = await fetch(`/api/reports/${traceId}`);
        const report = await response.json();

        // Update basic info
        document.getElementById('detailTitle').innerText = `Trace ID #${report.trace_id}`;
        document.getElementById('llmModelName').innerText = report.llm_model;
        document.getElementById('rootCauseText').innerText = report.root_cause;
        document.getElementById('anomalyContext').innerText = report.anomaly_context;
        
        // Detailed Analysis Result (Markdown)
        const detailedContent = document.getElementById('detailedAnalysisContent');
        if (detailedContent) {
            detailedContent.innerText = report.result || "No detailed report provided.";
        }
        
        const sevBadge = document.getElementById('severityBadge');
        sevBadge.innerText = report.severity.toUpperCase();
        sevBadge.className = report.severity === 'Critical' ? 'badge badge-error' : 'badge badge-warning';

        document.getElementById('summaryEvents').innerText = report.total_events.toLocaleString();
        document.getElementById('summaryDuration').innerText = report.duration;
        document.getElementById('summaryNodes').innerText = report.affected_nodes;

        // Recommendations
        const recList = document.getElementById('recommendationsList');
        recList.innerHTML = '';
        report.recommendations.forEach(action => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.gap = '12px';
            li.innerHTML = `
                <i class="fa-solid fa-circle-check" style="color: var(--success); margin-top: 4px;"></i>
                <span style="font-size: 14px;">${action}</span>
            `;
            recList.appendChild(li);
        });

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
}
// Listen for analyze button (Mocking behavior for demonstration)
const analyzeBtn = document.getElementById('analyzeBtn');
if(analyzeBtn) {
    analyzeBtn.onclick = async () => {
        alert("Mock: Sending analysis data to webhook...");
        const mockData = {
            trace_id: "ALPHA-" + Math.floor(Math.random()*1000),
            status: "SUCCESS",
            llm_model: "GPT-4o",
            severity: "Critical",
            root_cause: "The incident correlates with a 40% spike in Zombie Connections detected by the load balancer. AI analysis suggests a Circular Dependency between the Auth Service and the primary DB cluster.",
            anomaly_context: "92% of affected packets show corrupted header metadata inconsistent with standard TLS handshakes.",
            total_events: 142802,
            duration: "18m 42s",
            affected_nodes: 14,
            recommendations: [
                "Implement exponential backoff on auth-microservice-v2 retry logic.",
                "Increase connection pool timeout to 45s for DB read operations.",
                "Purge Redis cache for specific matching keys."
            ],
            error_distribution: { "Timeout Errors": 64, "Auth Failure": 22, "DNS Refusal": 14 },
            log_entries: [
                {
                    timestamp: "04:22:31.442",
                    source: "gw-ingress-04",
                    status: "200 OK",
                    message: "Request handoff initiated to auth-svc-01...",
                    stack_trace: "ERROR [auth-svc-01] 504 Gateway Timeout\nat internal/modules/auth/pipeline.js:142:11\nctx: {\n  'trace_id': '832c-49aa-9111',\n  'retries': 4\n}",
                    metadata_info: { node_id: "US-EAST-1A", client_ip: "192.168.1.184", protocol: "gRPC", latency: "38,001ms" }
                }
            ]
        };
        
        await fetch('/api/webhook/analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mockData)
        });
        loadReports();
    };
}
