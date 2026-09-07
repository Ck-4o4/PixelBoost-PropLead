// Indian Real Estate Cities & High-Demand Localities Database
const CITY_AREA_PRESETS = {
  "Mumbai": [
    "Bandra West", "Andheri West", "Bandra Kurla Complex (BKC)", "South Mumbai (Worli/Lower Parel)", 
    "Powai", "Thane West", "Juhu", "Goregaon West", "Malad West", "Navi Mumbai (Vashi/Palm Beach)", 
    "Borivali West", "Chembur", "Kandivali West", "Ghatkopar East", "Khar West"
  ],
  "Delhi NCR": [
    "Gurgaon Golf Course Road", "Cyber City Gurgaon", "Sohna Road Gurgaon", "Golf Course Extn Gurgaon",
    "Noida Sector 62", "Noida Expressway (Sec 137/150)", "Greater Noida West", "South Extension Delhi", 
    "Greater Kailash", "Connaught Place", "Vasant Kunj", "Dwarka", "Indirapuram Ghaziabad", "Faridabad"
  ],
  "Bangalore": [
    "Indiranagar", "Whitefield", "Koramangala", "HSR Layout", "Electronic City", 
    "Sarjapur Road", "Hebbal", "JP Nagar", "Marathahalli", "Bellandur", "Yelahanka", "Banashankari"
  ],
  "Pune": [
    "Baner", "Hinjewadi", "Wakad", "Koregaon Park", "Kharadi", "Viman Nagar", 
    "Kothrud", "Kalyani Nagar", "Hadapsar / Magarpatta", "Bavdhan", "Balewadi", "Aundh"
  ],
  "Hyderabad": [
    "Gachibowli", "Hitec City", "Jubilee Hills", "Banjara Hills", "Madhapur", 
    "Kondapur", "Financial District", "Kukatpally", "Kokapet", "Manikonda", "Tellapur"
  ],
  "Ahmedabad": [
    "SG Highway", "Prahlad Nagar", "Bopal / South Bopal", "Satellite", "Bodakdev", 
    "Thaltej", "Science City Road", "Sindhu Bhavan Road", "Vaishnodevi Circle", "Chandkheda", "Shela"
  ],
  "Chennai": [
    "OMR (Old Mahabalipuram Rd)", "Anna Nagar", "T. Nagar", "Adyar", "Velachery", 
    "ECR (East Coast Road)", "Porur", "Guindy", "Nungambakkam", "Sholinganallur"
  ],
  "Kolkata": [
    "Salt Lake (Sector V)", "New Town Rajarhat", "Ballygunge", "Park Street", "Alipore", 
    "South City / Jadavpur", "EM Bypass", "Behala", "Garia"
  ],
  "Surat": [
    "Vesu", "Adajan", "Piplod", "Pal", "Varachha", "Dumas Road", "Ghir Road", "Althan"
  ],
  "Jaipur": [
    "Vaishali Nagar", "Malviya Nagar", "Mansarovar", "Jagatpura", "C-Scheme", "Tonk Road", "Ajmer Road"
  ],
  "Lucknow": [
    "Gomti Nagar", "Gomti Nagar Extension", "Hazratganj", "Shaheed Path", "Alambagh", "Indira Nagar", "Sushant Golf City"
  ],
  "Chandigarh Tricity": [
    "Sector 17 Chandigarh", "Sector 35 Chandigarh", "Mohali Sector 82", "Airport Road Mohali", 
    "Panchkula Sector 20", "Zirakpur VIP Road", "New Chandigarh (Mullanpur)"
  ],
  "Indore": [
    "Vijay Nagar", "Super Corridor", "AB Road", "Palasia", "Nipania", "Mahalaxmi Nagar", "Bypass Road"
  ],
  "Goa": [
    "Panaji", "Calangute", "Candolim", "Porvorim", "Margao", "Anjuna", "Assagao", "Vagator"
  ],
  "Kochi": [
    "Marine Drive", "Kakkanad (Infopark)", "Edappally", "Panampilly Nagar", "Kaloor", "Aluva"
  ],
  "Coimbatore": [
    "RS Puram", "Peelamedu", "Gandhipuram", "Avinashi Road", "Saravanampatti", "Race Course"
  ],
  "Nagpur": [
    "Dharampeth", "Wardha Road", "Manish Nagar", "Besa", "Civil Lines", "MIHAN", "Ramdaspeth"
  ],
  "Vadodara": [
    "Alkapuri", "Gotri", "Vasna Road", "Bhayli", "Manjalpur", "Karelibaug", "Sevasi"
  ]
};

// State
let currentTab = 'scraper';
let leadsData = [];
let selectedLeadIds = new Set();
let eventSource = null;
let isCustomMode = false;

// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const tabPanes = document.querySelectorAll('.tab-pane');
const pageTitle = document.getElementById('page-title');
const pageSubtitle = document.getElementById('page-subtitle');

// Stats
const statTotal = document.getElementById('stat-total');
const statPhone = document.getElementById('stat-phone');
const statInterested = document.getElementById('stat-interested');
const sidebarLeadCount = document.getElementById('sidebar-lead-count');

// Scraper Elements
const scraperForm = document.getElementById('scraper-form');
const modeBtnPreset = document.getElementById('mode-btn-preset');
const modeBtnCustom = document.getElementById('mode-btn-custom');
const groupPresetCategory = document.getElementById('group-preset-category');
const groupCustomKeyword = document.getElementById('group-custom-keyword');

const searchCategory = document.getElementById('search-category');
const searchQuery = document.getElementById('search-query');
const cityPresetSelect = document.getElementById('city-preset-select');
const areaPresetSelect = document.getElementById('area-preset-select');
const searchCity = document.getElementById('search-city');
const areaChipsContainer = document.getElementById('area-chips-container');

const maxResults = document.getElementById('max-results');
const maxResultsVal = document.getElementById('max-results-val');
const btnStartScrape = document.getElementById('btn-start-scrape');
const btnStopScrape = document.getElementById('btn-stop-scrape');

const progressContainer = document.getElementById('progress-container');
const progressStatusText = document.getElementById('progress-status-text');
const progressPct = document.getElementById('progress-pct');
const progressBarFill = document.getElementById('progress-bar-fill');

const logConsole = document.getElementById('log-console');
const btnClearLogs = document.getElementById('btn-clear-logs');
const liveLeadsList = document.getElementById('live-leads-list');
const streamCount = document.getElementById('stream-count');

// CRM Elements
const crmSearch = document.getElementById('crm-search');
const filterStatus = document.getElementById('filter-status');
const filterArea = document.getElementById('filter-area');
const filterPhone = document.getElementById('filter-phone');
const btnRefreshLeads = document.getElementById('btn-refresh-leads');
const leadsTableBody = document.getElementById('leads-table-body');
const selectAllLeads = document.getElementById('select-all-leads');
const bulkActionsBar = document.getElementById('bulk-actions-bar');
const selectedCountText = document.getElementById('selected-count-text');
const bulkStatusSelect = document.getElementById('bulk-status-select');
const btnBulkStatus = document.getElementById('btn-bulk-status');
const btnBulkDelete = document.getElementById('btn-bulk-delete');
const tableSummaryText = document.getElementById('table-summary-text');

// Import Elements
const importForm = document.getElementById('import-form');
const importFile = document.getElementById('import-file');
const fileNameDisplay = document.getElementById('file-name-display');
const btnImportSubmit = document.getElementById('btn-import-submit');
const importResult = document.getElementById('import-result');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupAreaPresets();
  setupModeSwitching();
  setupScraperEvents();
  setupCrmEvents();
  setupImportEvents();
  fetchStats();
  fetchAreas();
  fetchLeads();
});

// Toast System
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Navigation Setup
function setupNavigation() {
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tab = item.dataset.tab;
      switchTab(tab);
    });
  });
}

function switchTab(tabId) {
  currentTab = tabId;
  navItems.forEach(item => item.classList.toggle('active', item.dataset.tab === tabId));
  tabPanes.forEach(pane => pane.classList.toggle('active', pane.id === `tab-${tabId}`));

  if (tabId === 'scraper') {
    pageTitle.textContent = 'Lead Generation Studio';
    pageSubtitle.textContent = 'Extract verified phone numbers, WhatsApp contacts & local real estate brokers directly from Google Maps';
  } else if (tabId === 'crm') {
    pageTitle.textContent = 'Calling Leads CRM';
    pageSubtitle.textContent = 'Manage leads, direct dial contacts, launch WhatsApp chats, and save agent call logs';
    fetchAreas();
    fetchLeads();
  } else if (tabId === 'export') {
    pageTitle.textContent = 'Export & Import Calling Lists';
    pageSubtitle.textContent = 'Download formatted calling sheets for your staff or merge existing Excel/CSV files';
  }
}

// Mode Switcher (Industry Preset vs Custom Keyword)
function setupModeSwitching() {
  if (modeBtnPreset && modeBtnCustom) {
    modeBtnPreset.addEventListener('click', () => {
      isCustomMode = false;
      modeBtnPreset.classList.add('active');
      modeBtnCustom.classList.remove('active');
      groupPresetCategory.classList.remove('hidden');
      groupCustomKeyword.classList.add('hidden');
    });

    modeBtnCustom.addEventListener('click', () => {
      isCustomMode = true;
      modeBtnCustom.classList.add('active');
      modeBtnPreset.classList.remove('active');
      groupCustomKeyword.classList.remove('hidden');
      groupPresetCategory.classList.add('hidden');
      searchQuery.focus();
    });
  }
}

// Area Presets Logic
function setupAreaPresets() {
  updateAreaUI(cityPresetSelect.value);

  cityPresetSelect.addEventListener('change', (e) => {
    const city = e.target.value;
    if (city === 'custom') {
      areaPresetSelect.innerHTML = '<option value="">-- All Localities --</option>';
      areaChipsContainer.innerHTML = '';
      searchCity.value = '';
    } else {
      updateAreaUI(city);
    }
  });

  areaPresetSelect.addEventListener('change', (e) => {
    const area = e.target.value;
    const city = cityPresetSelect.value;
    if (area) {
      searchCity.value = `${area}, ${city}`;
      highlightActiveChip(area);
    } else if (city !== 'custom') {
      searchCity.value = city;
      clearChipActive();
    }
  });
}

function updateAreaUI(city) {
  const areas = CITY_AREA_PRESETS[city] || [];
  
  // Populate Area Dropdown
  areaPresetSelect.innerHTML = `<option value="">📍 Entire ${city} (All Localities)</option>`;
  areas.forEach(area => {
    const opt = document.createElement('option');
    opt.value = area;
    opt.textContent = `📍 ${area}`;
    areaPresetSelect.appendChild(opt);
  });

  // Default to first area
  if (areas.length > 0) {
    areaPresetSelect.value = areas[0];
    searchCity.value = `${areas[0]}, ${city}`;
  } else {
    searchCity.value = city;
  }

  // Populate Compact Top 6 Chips
  areaChipsContainer.innerHTML = '';
  const topChips = areas.slice(0, 6);
  topChips.forEach((area, index) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `area-chip ${index === 0 ? 'active' : ''}`;
    chip.dataset.area = area;
    chip.textContent = area;
    chip.addEventListener('click', () => {
      areaPresetSelect.value = area;
      searchCity.value = `${area}, ${city}`;
      highlightActiveChip(area);
    });
    areaChipsContainer.appendChild(chip);
  });
}

function highlightActiveChip(areaName) {
  const chips = areaChipsContainer.querySelectorAll('.area-chip');
  chips.forEach(chip => {
    chip.classList.toggle('active', chip.dataset.area === areaName);
  });
}

function clearChipActive() {
  const chips = areaChipsContainer.querySelectorAll('.area-chip');
  chips.forEach(chip => chip.classList.remove('active'));
}

// Fetch Stats
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();
    statTotal.textContent = data.total_leads || 0;
    statPhone.textContent = data.with_phone || 0;
    
    const interestedCount = (data.status_counts?.['Interested'] || 0) + (data.status_counts?.['Deal Closed'] || 0);
    statInterested.textContent = interestedCount;
    sidebarLeadCount.textContent = data.total_leads || 0;
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

// Fetch Areas
async function fetchAreas() {
  try {
    const res = await fetch('/api/areas');
    if (!res.ok) return;
    const data = await res.json();
    const areas = data.areas || [];
    
    filterArea.innerHTML = '<option value="">📍 All Areas / Cities</option>';
    areas.forEach(area => {
      const opt = document.createElement('option');
      opt.value = area;
      opt.textContent = `📍 ${area}`;
      filterArea.appendChild(opt);
    });
  } catch (err) {
    console.error('Error fetching areas:', err);
  }
}

// Scraper Logic
function setupScraperEvents() {
  maxResults.addEventListener('input', (e) => {
    maxResultsVal.textContent = `${e.target.value} Leads`;
  });

  btnClearLogs.addEventListener('click', () => {
    logConsole.innerHTML = '';
  });

  scraperForm.addEventListener('submit', (e) => {
    e.preventDefault();
    startScraping();
  });

  btnStopScrape.addEventListener('click', () => {
    stopScraping();
  });
}

function appendLog(message, isError = false) {
  const line = document.createElement('div');
  line.className = `log-line ${isError ? 'text-rose' : 'text-secondary'}`;
  const timestamp = new Date().toLocaleTimeString();
  line.textContent = `[${timestamp}] ${message}`;
  logConsole.appendChild(line);
  logConsole.scrollTop = logConsole.scrollHeight;
}

function startScraping() {
  const query = (isCustomMode ? searchQuery.value : searchCategory.value).trim();
  const city = searchCity.value.trim();
  const category = (!isCustomMode ? searchCategory.value : 'Business');
  const count = parseInt(maxResults.value, 10);

  if (!query) {
    showToast('Please enter search keywords', 'error');
    return;
  }

  // Toggle UI
  btnStartScrape.classList.add('hidden');
  btnStopScrape.classList.remove('hidden');
  progressContainer.classList.remove('hidden');
  progressPct.textContent = '0%';
  progressBarFill.style.width = '0%';
  progressStatusText.textContent = 'Connecting to Google Maps engine...';

  liveLeadsList.innerHTML = '';
  streamCount.textContent = '0 Extracted';

  appendLog(`Initiating search: "${query}" in "${city || 'any'}" (Target: ${count})`);

  const params = new URLSearchParams({
    query: query,
    city: city,
    category: category,
    max_results: count
  });

  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource(`/api/scrape/stream?${params.toString()}`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        appendLog(data.message);
      } else if (data.type === 'progress') {
        progressPct.textContent = `${data.percent}%`;
        progressBarFill.style.width = `${data.percent}%`;
        progressStatusText.textContent = `Discovered ${data.discovered} of ~${data.target} listings...`;
      } else if (data.type === 'lead') {
        renderStreamLead(data.lead, data.is_new);
        streamCount.textContent = `${data.scraped_count} Extracted`;
        if (data.progress) {
          progressPct.textContent = `${data.progress.percent}%`;
          progressBarFill.style.width = `${data.progress.percent}%`;
          progressStatusText.textContent = `Extracting contact details (${data.progress.current}/${data.progress.total})...`;
        }
        fetchStats();
      } else if (data.type === 'complete') {
        appendLog(data.message);
        showToast(data.message, 'success');
        finishScraping();
      } else if (data.type === 'error') {
        appendLog(data.message, true);
        showToast(data.message, 'error');
        finishScraping();
      }
    } catch (err) {
      console.error('SSE parse error:', err);
    }
  };

  eventSource.onerror = (err) => {
    console.error('SSE Error:', err);
    appendLog('Scraper stream connection closed.');
    finishScraping();
  };
}

async function stopScraping() {
  try {
    await fetch('/api/scrape/stop', { method: 'POST' });
    appendLog('Cancellation signal sent to scraper engine...');
    showToast('Stopping scraper...', 'info');
  } catch (err) {
    console.error(err);
  }
}

function finishScraping() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  btnStartScrape.classList.remove('hidden');
  btnStopScrape.classList.add('hidden');
  progressStatusText.textContent = 'Completed';
  progressPct.textContent = '100%';
  progressBarFill.style.width = '100%';
  fetchStats();
}

function renderStreamLead(lead, isNew) {
  // Remove empty state
  const emptyState = liveLeadsList.querySelector('.stream-empty');
  if (emptyState) emptyState.remove();

  const item = document.createElement('div');
  item.className = 'stream-lead-card';

  const stars = lead.rating > 0 ? `⭐ ${lead.rating} (${lead.reviews_count || 0})` : '';
  const digits = lead.phone ? lead.phone.replace(/\D/g, '') : '';
  const cleanNum = lead.phone ? lead.phone.replace(/[^\d+]/g, '') : '';
  const waNum = digits.length === 10 ? '91' + digits : digits;

  item.innerHTML = `
    <div class="stream-lead-top">
      <div>
        <span class="stream-lead-name">${escapeHtml(lead.name)}</span>
        <div style="font-size: 0.72rem; color: var(--text-dim); margin-top: 2px;">${escapeHtml(lead.category || 'Real Estate')}</div>
      </div>
      ${stars ? `<span class="count-pill">${stars}</span>` : ''}
    </div>
    <div class="stream-lead-meta">
      ${lead.phone ? `
        <a href="tel:${cleanNum}" class="phone-action-pill" title="Click to Dial ${escapeHtml(lead.phone)}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
          </svg>
          <span>${escapeHtml(lead.phone)}</span>
        </a>
        <a href="https://wa.me/${waNum}" target="_blank" class="wa-action-pill" title="Send WhatsApp Message">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
          </svg>
          <span>WhatsApp</span>
        </a>
      ` : '<span class="text-dim-xs">No phone detected</span>'}
      ${lead.instagram ? `
        <a href="${escapeHtml(lead.instagram)}" target="_blank" class="ig-action-pill" title="${lead.instagram.includes('instagram.com') ? 'View Instagram Profile' : 'Find Instagram Profile'}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
            <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
          </svg>
          <span>Instagram</span>
        </a>
      ` : ''}
    </div>
    <div class="stream-lead-addr">${escapeHtml(lead.address || 'Address captured on Google Maps')}</div>
  `;

  liveLeadsList.insertBefore(item, liveLeadsList.firstChild);
}

// CRM Logic
function setupCrmEvents() {
  crmSearch.addEventListener('input', debounce(() => fetchLeads(), 300));
  filterStatus.addEventListener('change', () => fetchLeads());
  filterArea.addEventListener('change', () => fetchLeads());
  filterPhone.addEventListener('change', () => fetchLeads());
  btnRefreshLeads.addEventListener('click', () => {
    fetchAreas();
    fetchLeads();
  });

  selectAllLeads.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    const checkboxes = leadsTableBody.querySelectorAll('.lead-checkbox');
    checkboxes.forEach(cb => {
      cb.checked = isChecked;
      const id = parseInt(cb.dataset.id, 10);
      if (isChecked) selectedLeadIds.add(id);
      else selectedLeadIds.delete(id);
    });
    updateBulkBar();
  });

  btnBulkDelete.addEventListener('click', async () => {
    if (selectedLeadIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedLeadIds.size} selected leads?`)) return;

    try {
      const res = await fetch('/api/leads/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedLeadIds) })
      });
      const data = await res.json();
      showToast(`Deleted ${data.deleted_count} leads`, 'success');
      selectedLeadIds.clear();
      selectAllLeads.checked = false;
      fetchAreas();
      fetchLeads();
      fetchStats();
    } catch (err) {
      showToast('Error deleting leads', 'error');
    }
  });

  btnBulkStatus.addEventListener('click', async () => {
    const status = bulkStatusSelect.value;
    if (!status || selectedLeadIds.size === 0) {
      showToast('Please choose a status to apply', 'info');
      return;
    }

    try {
      const res = await fetch('/api/leads/bulk-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedLeadIds), call_status: status })
      });
      const data = await res.json();
      showToast(`Updated status for ${data.updated_count} leads`, 'success');
      selectedLeadIds.clear();
      selectAllLeads.checked = false;
      fetchLeads();
      fetchStats();
    } catch (err) {
      showToast('Error updating status', 'error');
    }
  });
}

function updateBulkBar() {
  if (selectedLeadIds.size > 0) {
    bulkActionsBar.classList.remove('hidden');
    selectedCountText.textContent = `${selectedLeadIds.size} lead${selectedLeadIds.size > 1 ? 's' : ''} selected`;
  } else {
    bulkActionsBar.classList.add('hidden');
  }
}

async function fetchLeads() {
  const search = crmSearch.value.trim();
  const status = filterStatus.value;
  const area = filterArea.value;
  const hasPhone = filterPhone.value;

  const params = new URLSearchParams({
    search: search,
    status: status,
    city: area,
    limit: 500
  });

  if (hasPhone !== '') {
    params.append('has_phone', hasPhone);
  }

  // Update quick export links
  const quickExcel = document.getElementById('quick-export-excel');
  const quickCsv = document.getElementById('quick-export-csv');
  if (quickExcel) quickExcel.href = `/api/export/excel?${params.toString()}`;
  if (quickCsv) quickCsv.href = `/api/export/csv?${params.toString()}`;

  try {
    const res = await fetch(`/api/leads?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    leadsData = data.leads || [];
    renderLeadsTable(leadsData);
    tableSummaryText.textContent = `Showing ${leadsData.length} leads`;
  } catch (err) {
    console.error('Error fetching leads:', err);
  }
}

function renderLeadsTable(leads) {
  leadsTableBody.innerHTML = '';
  selectedLeadIds.clear();
  selectAllLeads.checked = false;
  updateBulkBar();

  if (leads.length === 0) {
    leadsTableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-dim);">
          No leads found matching current filters. Start a scrape query or reset filters.
        </td>
      </tr>
    `;
    return;
  }

  leads.forEach(lead => {
    const tr = document.createElement('tr');
    tr.id = `lead-row-${lead.id}`;

    const statusClass = getStatusClass(lead.call_status);
    const cleanNum = lead.phone ? lead.phone.replace(/[^\d+]/g, '') : '';
    const digits = lead.phone ? lead.phone.replace(/\D/g, '') : '';
    const waNum = digits.length === 10 ? '91' + digits : digits;

    tr.innerHTML = `
      <td>
        <input type="checkbox" class="lead-checkbox" data-id="${lead.id}">
      </td>
      <td>
        <div class="contact-cell">
          <span class="contact-name">${escapeHtml(lead.name)}</span>
          <span class="contact-cat">
            ${escapeHtml(lead.category || 'Real Estate')}
            ${lead.website ? `• <a href="${escapeHtml(lead.website)}" target="_blank" class="btn-text-link">Web</a>` : ''}
            ${lead.instagram ? `• <a href="${escapeHtml(lead.instagram)}" target="_blank" class="btn-text-link" style="color: #fb7185; font-weight: 700;">IG</a>` : ''}
          </span>
        </div>
      </td>
      <td>
        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
          ${lead.phone ? `
            <a href="tel:${cleanNum}" class="phone-action-pill" title="Click to Dial ${escapeHtml(lead.phone)}">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
              </svg>
              <span>${escapeHtml(lead.phone)}</span>
            </a>
            <a href="https://wa.me/${waNum}" target="_blank" class="wa-action-pill" title="Send WhatsApp Message">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
              </svg>
              <span>WA</span>
            </a>
            <button class="console-clear" onclick="copyToClipboard('${escapeJs(lead.phone)}')" title="Copy Phone">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
          ` : '<span class="text-dim-xs">No Phone</span>'}
          ${lead.instagram ? `
            <a href="${escapeHtml(lead.instagram)}" target="_blank" class="ig-action-pill" title="${lead.instagram.includes('instagram.com') ? 'Open Instagram Profile' : 'Find Instagram Profile'}">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
              </svg>
              <span>IG</span>
            </a>
          ` : ''}
        </div>
      </td>
      <td>
        <span style="font-size: 0.78rem; color: var(--text-secondary);">${escapeHtml(lead.address || '—')}</span>
      </td>
      <td>
        ${lead.rating > 0 ? `<span class="count-pill">⭐ ${lead.rating} (${lead.reviews_count || 0})</span>` : '<span class="text-dim-xs">—</span>'}
      </td>
      <td>
        <select class="status-pill ${statusClass}" onchange="updateLeadStatus(${lead.id}, this)">
          <option value="New" ${lead.call_status === 'New' ? 'selected' : ''}>🟢 New</option>
          <option value="Interested" ${lead.call_status === 'Interested' ? 'selected' : ''}>⭐ Interested</option>
          <option value="Follow-up" ${lead.call_status === 'Follow-up' ? 'selected' : ''}>📅 Follow-up</option>
          <option value="Ring No Response" ${lead.call_status === 'Ring No Response' ? 'selected' : ''}>📵 RNR</option>
          <option value="Not Interested" ${lead.call_status === 'Not Interested' ? 'selected' : ''}>❌ Not Interested</option>
          <option value="Deal Closed" ${lead.call_status === 'Deal Closed' ? 'selected' : ''}>🏆 Closed</option>
        </select>
      </td>
      <td>
        <input 
          type="text" 
          class="notes-inline-input" 
          value="${escapeHtml(lead.call_notes || '')}" 
          placeholder="Click to add note..."
          onblur="saveLeadNotes(${lead.id}, this.value)"
          onkeydown="if(event.key === 'Enter') this.blur();"
        >
      </td>
      <td>
        <div style="display: flex; gap: 6px;">
          ${lead.maps_url ? `
            <a href="${escapeHtml(lead.maps_url)}" target="_blank" class="console-clear" title="View on Google Maps">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </a>
          ` : ''}
          <button class="console-clear" style="color: var(--rose);" onclick="deleteLeadSingle(${lead.id})" title="Delete Lead">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </td>
    `;

    const checkbox = tr.querySelector('.lead-checkbox');
    checkbox.addEventListener('change', (e) => {
      const id = lead.id;
      if (e.target.checked) selectedLeadIds.add(id);
      else selectedLeadIds.delete(id);
      updateBulkBar();
    });

    leadsTableBody.appendChild(tr);
  });
}

function getStatusClass(status) {
  switch (status) {
    case 'New': return 'status-new';
    case 'Interested': return 'status-interested';
    case 'Follow-up': return 'status-followup';
    case 'Ring No Response': return 'status-rnr';
    case 'Not Interested': return 'status-notinterested';
    case 'Deal Closed': return 'status-dealclosed';
    default: return 'status-new';
  }
}

// Inline Status Update
async function updateLeadStatus(leadId, selectElem) {
  const newStatus = selectElem.value;
  selectElem.className = `status-pill ${getStatusClass(newStatus)}`;

  try {
    const res = await fetch(`/api/leads/${leadId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ call_status: newStatus })
    });
    if (res.ok) {
      showToast(`Status updated to ${newStatus}`, 'success');
      fetchStats();
    }
  } catch (err) {
    showToast('Failed to update status', 'error');
  }
}

// Inline Notes Update
async function saveLeadNotes(leadId, notes) {
  try {
    const res = await fetch(`/api/leads/${leadId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ call_notes: notes })
    });
    if (res.ok) {
      showToast('Call note saved', 'info');
    }
  } catch (err) {
    showToast('Failed to save note', 'error');
  }
}

// Single Delete
async function deleteLeadSingle(leadId) {
  if (!confirm('Are you sure you want to delete this lead?')) return;
  try {
    const res = await fetch(`/api/leads/${leadId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Lead deleted', 'success');
      const row = document.getElementById(`lead-row-${leadId}`);
      if (row) row.remove();
      fetchStats();
    }
  } catch (err) {
    showToast('Error deleting lead', 'error');
  }
}

// Copy to Clipboard helper
window.copyToClipboard = function(text) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`Copied ${text} to clipboard!`, 'info');
  }).catch(() => {
    showToast('Failed to copy', 'error');
  });
};

window.updateLeadStatus = updateLeadStatus;
window.saveLeadNotes = saveLeadNotes;
window.deleteLeadSingle = deleteLeadSingle;

// CSV Import Logic
function setupImportEvents() {
  importFile.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      fileNameDisplay.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      btnImportSubmit.disabled = false;
    }
  });

  importForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = importFile.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    btnImportSubmit.disabled = true;
    btnImportSubmit.innerHTML = '<span>Importing & Deduplicating...</span>';

    try {
      const res = await fetch('/api/import/csv', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        importResult.innerHTML = `
          <div class="toast-item" style="margin-top: 10px; border-color: var(--emerald-border); color: #34d399;">
            ✅ Successfully processed ${data.total_processed} records (${data.new_leads_added} new leads added).
          </div>
        `;
        showToast('CSV import complete', 'success');
        fetchStats();
        fetchLeads();
      } else {
        importResult.innerHTML = `
          <div class="toast-item" style="margin-top: 10px; border-color: rgba(239, 68, 68, 0.4); color: #fca5a5;">
            ❌ ${data.detail || 'Import failed'}
          </div>
        `;
      }
    } catch (err) {
      importResult.innerHTML = `<div class="toast-item" style="margin-top: 10px; color: #fca5a5;">❌ Network error</div>`;
    } finally {
      btnImportSubmit.disabled = false;
      btnImportSubmit.innerHTML = '<span>Import & Merge Into CRM</span>';
    }
  });
}

// Utility Helpers
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/'/g, "\\'");
}
