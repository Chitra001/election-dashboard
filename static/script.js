// Global state
let allConstituencies = [];
let activeConstituencies = [];
let currentActiveIndex = 0;
let slideTimer = null;
let refreshTimer = null;
let autoCycle = true;
let progressFrame = null;
let currentConstData = null;

// Base time: May 4, 2026, 10:00:00 IST (04:30 UTC)
const BASE_TIME_IST = new Date(Date.UTC(2026, 4, 4, 4, 30, 0));
const SLIDE_SEC = 15;

// Helper: current IST
function getISTNow() {
    const now = new Date();
    const offsetIST = 5.5 * 60 * 60 * 1000;
    return new Date(now.getTime() + (offsetIST - now.getTimezoneOffset() * 60 * 1000));
}

// Compute starting index based on elapsed seconds since 10:00 IST
function computeStartIndex() {
    if (activeConstituencies.length === 0) return 0;
    const now = getISTNow();
    const elapsedSec = (now - BASE_TIME_IST) / 1000;
    if (elapsedSec < 0) return 0;
    let rawIdx = Math.floor(elapsedSec / SLIDE_SEC);
    return rawIdx % activeConstituencies.length;
}

// Fetch party totals
async function loadPartySummary() {
    try {
        const resp = await fetch('/api/party-totals');
        const data = await resp.json();
        const container = document.getElementById('partySummaryPanel');
        if (!container) return;
        container.innerHTML = data.parties.map(p => `
            <div class="party-card" style="border-bottom-color: ${p.color};">
                <h4>${p.name}</h4>
                <div class="seat-count">${p.seats}</div>
                <div style="font-size: 10px;">seats</div>
            </div>
        `).join('');
    } catch(e) { console.error('Party summary error', e); }
}

// Fetch all constituencies list
async function loadConstituencyList() {
    try {
        const resp = await fetch('/api/constituencies');
        const data = await resp.json();
        allConstituencies = data.constituencies;
        populateDropdown();
        await bootstrapActiveConstituencies();
        if (activeConstituencies.length > 0) {
            currentActiveIndex = computeStartIndex();
            await loadCurrentConstituency();
            startTimers();
        } else {
            document.getElementById('constName').innerHTML = 'No started constituencies – waiting...';
            setTimeout(bootstrapActiveConstituencies, 30000);
        }
    } catch(e) { console.error('List error', e); }
}

// Find first 10 started constituencies
async function bootstrapActiveConstituencies() {
    if (activeConstituencies.length > 0) return;
    for (let i = 0; i < allConstituencies.length && activeConstituencies.length < 10; i++) {
        const constObj = allConstituencies[i];
        try {
            const data = await fetchConstituency(constObj.code);
            if (data.started) {
                activeConstituencies.push(constObj);
            }
        } catch(e) { /* ignore */ }
    }
    if (activeConstituencies.length === 0) {
        setTimeout(() => bootstrapActiveConstituencies(), 15000);
    } else {
        if (slideTimer) stopTimers();
        currentActiveIndex = computeStartIndex();
        await loadCurrentConstituency();
        startTimers();
    }
}

// Fetch one constituency
async function fetchConstituency(code) {
    const resp = await fetch(`/api/constituency/${code}`);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return await resp.json();
}

// Load current constituency, skip if not started
async function loadCurrentConstituency() {
    if (activeConstituencies.length === 0) return;
    const constObj = activeConstituencies[currentActiveIndex];
    try {
        const data = await fetchConstituency(constObj.code);
        currentConstData = data;
        if (!data.started) {
            activeConstituencies.splice(currentActiveIndex, 1);
            if (activeConstituencies.length === 0) {
                await bootstrapActiveConstituencies();
                if (activeConstituencies.length === 0) {
                    document.getElementById('constName').innerHTML = 'No active constituencies – retrying...';
                    return;
                }
            }
            currentActiveIndex = currentActiveIndex % activeConstituencies.length;
            await loadCurrentConstituency();
            return;
        }
        displayConstituency(constObj, data);
        updateDropdownSelection(constObj.code);
    } catch(e) {
        console.error('Fetch error', constObj.code, e);
        activeConstituencies.splice(currentActiveIndex, 1);
        if (activeConstituencies.length === 0) {
            await bootstrapActiveConstituencies();
        }
        if (activeConstituencies.length > 0) {
            currentActiveIndex = currentActiveIndex % activeConstituencies.length;
            await loadCurrentConstituency();
        } else {
            document.getElementById('constName').innerHTML = 'Connection error – retrying...';
            setTimeout(bootstrapActiveConstituencies, 15000);
        }
    }
}

// Display constituency data
function displayConstituency(constObj, data) {
    document.getElementById('constName').innerHTML = constObj.name;
    const roundInfo = data.round_current ? `${data.round_current}/${data.round_total}` : '0/20';
    document.getElementById('constExtras').innerHTML = `AC ${constObj.ac_no} • Round ${roundInfo}`;
    
    const grid = document.getElementById('dynamicCandidatesGrid');
    if (!data.candidates || data.candidates.length === 0) {
        grid.innerHTML = '<div class="col-12 text-center">No candidate data available</div>';
        return;
    }
    const candidatesHtml = data.candidates.map(cand => {
        const statusClass = cand.status === 'leading' ? 'status-lead' : 'status-trail';
        const statusText = cand.status === 'leading' ? 'Leading' : 'Trailing';
        const marginHtml = cand.margin ? `<span>${cand.margin}</span>` : '';
        const imgSrc = cand.img_src || 'https://placehold.co/70x70?text=No+Image';
        return `
            <div class="candidate-card">
                <div class="candidate-img">
                    <img src="${imgSrc}" alt="${cand.name}" onerror="this.src='https://placehold.co/70x70?text=No+Image'">
                </div>
                <div class="candidate-info">
                    <div class="candidate-name">${escapeHtml(cand.name)}</div>
                    <div class="candidate-party"><i class="fas fa-tag"></i> ${escapeHtml(cand.party)}</div>
                    <div class="vote-detail">
                        <span><i class="fas fa-vote-yea"></i> ${cand.votes.toLocaleString()}</span>
                        <span class="${statusClass}">${statusText} ${marginHtml}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    grid.innerHTML = candidatesHtml;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Next slide
function nextSlide() {
    if (!autoCycle) return;
    if (activeConstituencies.length === 0) return;
    currentActiveIndex = (currentActiveIndex + 1) % activeConstituencies.length;
    loadCurrentConstituency();
    resetProgressBar();
}

// Progress bar animation
function resetProgressBar() {
    if (progressFrame) cancelAnimationFrame(progressFrame);
    const progressEl = document.getElementById('timerProgress');
    if (!progressEl) return;
    progressEl.style.width = '0%';
    let startTime = performance.now();
    function animate(now) {
        const elapsed = (now - startTime) / 1000;
        const percent = Math.min((elapsed / SLIDE_SEC) * 100, 100);
        progressEl.style.width = percent + '%';
        if (elapsed < SLIDE_SEC) {
            progressFrame = requestAnimationFrame(animate);
        } else {
            progressFrame = null;
        }
    }
    progressFrame = requestAnimationFrame(animate);
}

// Timers
function startSlideTimer() {
    if (slideTimer) clearInterval(slideTimer);
    slideTimer = setInterval(() => nextSlide(), SLIDE_SEC * 1000);
}

function startRefreshTimer() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
        if (autoCycle && activeConstituencies.length > 0) {
            loadCurrentConstituency();
        }
    }, 60000);
}

function startTimers() {
    startSlideTimer();
    startRefreshTimer();
    resetProgressBar();
}

function stopTimers() {
    if (slideTimer) clearInterval(slideTimer);
    if (refreshTimer) clearInterval(refreshTimer);
    if (progressFrame) cancelAnimationFrame(progressFrame);
    slideTimer = null;
    refreshTimer = null;
    progressFrame = null;
}

// Control functions
function pauseAutoCycle() {
    autoCycle = false;
    stopTimers();
    const btn = document.getElementById('resetRotationBtn');
    btn.innerHTML = '<i class="fas fa-play"></i> Resume';
    btn.onclick = resumeAutoCycle;
}

function resumeAutoCycle() {
    autoCycle = true;
    if (activeConstituencies.length > 0) {
        currentActiveIndex = computeStartIndex();
        loadCurrentConstituency();
    }
    startTimers();
    const btn = document.getElementById('resetRotationBtn');
    btn.innerHTML = '<i class="fas fa-redo-alt"></i> Next constituency';
    btn.onclick = () => nextSlide();
}

// Dropdown
function populateDropdown() {
    const dropdown = document.getElementById('constituencyDropdown');
    if (!dropdown) return;
    dropdown.innerHTML = '<option value="">-- Jump to constituency --</option>';
    allConstituencies.forEach(c => {
        const option = document.createElement('option');
        option.value = c.code;
        option.textContent = `${c.ac_no} - ${c.name}`;
        dropdown.appendChild(option);
    });
    dropdown.addEventListener('change', async (e) => {
        const selectedCode = e.target.value;
        if (!selectedCode) return;
        pauseAutoCycle();
        let found = activeConstituencies.find(c => c.code === selectedCode);
        if (!found) {
            const data = await fetchConstituency(selectedCode);
            if (data.started) {
                const constObj = allConstituencies.find(c => c.code === selectedCode);
                activeConstituencies.push(constObj);
                found = constObj;
            } else {
                alert('Counting not started for this constituency yet.');
                resumeAutoCycle();
                return;
            }
        }
        currentActiveIndex = activeConstituencies.findIndex(c => c.code === selectedCode);
        await loadCurrentConstituency();
    });
}

function updateDropdownSelection(code) {
    const dropdown = document.getElementById('constituencyDropdown');
    if (dropdown) dropdown.value = code;
}

// Initialise
async function init() {
    await loadPartySummary();
    await loadConstituencyList();
    document.getElementById('resetRotationBtn').onclick = () => nextSlide();
}

init();