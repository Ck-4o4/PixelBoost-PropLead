// ==========================================================================
// PixelBoost PropLeadAi — Multi-Tenant Client & Master Admin Controller
// Made with ❤️ By CK
// ==========================================================================

// Indian Real Estate Cities & High-Demand Localities Database
const CITY_AREA_PRESETS = {
  "Ahmedabad": [
    "SG Highway", "Prahlad Nagar", "Bopal / South Bopal", "Satellite", "Bodakdev", 
    "Thaltej", "Science City Road", "Sindhu Bhavan Road", "Vaishnodevi Circle", "Chandkheda", "Shela"
  ],
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
  "Bengaluru": [
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
  "Vadodara": [
    "Alkapuri", "Gotri", "Vasna Road", "Bhayli", "Manjalpur", "Karelibaug", "Sevasi"
  ],
  "Rajkot": [
    "Kalawad Road", "150 Feet Ring Road", "Yagnik Road", "University Road", "Nana Mava", "Raiya Road"
  ],
  "Jaipur": [
    "Vaishali Nagar", "Malviya Nagar", "Mansarovar", "Jagatpura", "C-Scheme", "Tonk Road", "Ajmer Road"
  ],
  "Lucknow": [
    "Gomti Nagar", "Gomti Nagar Extension", "Hazratganj", "Shaheed Path", "Alambagh", "Indira Nagar", "Sushant Golf City"
  ],
  "Chandigarh": [
    "Sector 17 Chandigarh", "Sector 35 Chandigarh", "Mohali Sector 82", "Airport Road Mohali", 
    "Panchkula Sector 20", "Zirakpur VIP Road", "New Chandigarh (Mullanpur)"
  ],
  "Indore": [
    "Vijay Nagar", "Super Corridor", "AB Road", "Palasia", "Nipania", "Mahalaxmi Nagar", "Bypass Road"
  ],
  "Nagpur": [
    "Dharampeth", "Wardha Road", "Manish Nagar", "Besa", "Civil Lines", "MIHAN", "Ramdaspeth"
  ],
  "Coimbatore": [
    "RS Puram", "Peelamedu", "Gandhipuram", "Avinashi Road", "Saravanampatti", "Race Course"
  ],
  "Kochi": [
    "Marine Drive", "Kakkanad (Infopark)", "Edappally", "Panampilly Nagar", "Kaloor", "Aluva"
  ]
};

// State
let currentUser = null;
let currentTab = 'scraper';
let leadsData = [];
let selectedLeadIds = new Set();
let eventSource = null;
let isCustomMode = false;

// Auth Helper
function getAuthToken() {
  return localStorage.getItem('pixelboost_token') || '';
}

function getAuthHeaders(extra = {}) {
  const token = getAuthToken();
  return {
    'Authorization': `Bearer ${token}`,
    ...extra
  };
}

// Check Authentication Session
async function checkAuthSession() {
  const token = getAuthToken();
  if (!token) {
    currentUser = null;
    updateUserProfileUI();
    return true; // Allow guest mode with 5 free leads!
  }

  try {
    const res = await fetch('/api/auth/me', {
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      localStorage.removeItem('pixelboost_token');
      localStorage.removeItem('pixelboost_user');
      currentUser = null;
      updateUserProfileUI();
      return true; // Allow guest mode
    }

    currentUser = await res.json();
    localStorage.setItem('pixelboost_user', JSON.stringify(currentUser));
    updateUserProfileUI();
    return true;
  } catch (err) {
    currentUser = null;
    updateUserProfileUI();
    return true;
  }
}

function updateUserProfileUI() {
  // Sidebar profile
  const nameElem = document.getElementById('user-display-name');
  const emailElem = document.getElementById('user-display-email');
  const avatarElem = document.getElementById('user-avatar-initials');
  const navAdmin = document.getElementById('nav-admin');
  const btnGuestLogin = document.getElementById('btn-guest-login');
  const btnLogout = document.getElementById('btn-logout');

  // Header tenant pill and credits
  const tenantPill = document.getElementById('header-tenant-pill');
  const creditsPill = document.getElementById('header-credits-pill');
  const maxResults = document.getElementById('max-results');
  const targetBadge = document.getElementById('target-count-badge');
  const sliderHelper = document.getElementById('slider-helper-text');

  if (!currentUser) {
    // Guest Trial Mode
    if (nameElem) nameElem.textContent = 'Free Guest Trial';
    if (emailElem) emailElem.textContent = '5 Free Leads Available';
    if (avatarElem) avatarElem.textContent = '🎁';
    if (btnGuestLogin) btnGuestLogin.classList.remove('hidden');
    if (btnLogout) btnLogout.classList.add('hidden');
    if (navAdmin) navAdmin.classList.add('hidden');

    if (tenantPill) tenantPill.textContent = '🎁 5 Free Leads Trial';
    if (creditsPill) {
      creditsPill.textContent = '🎁 Free Trial: 5 Free Leads';
      creditsPill.style.background = '#e0f2fe';
      creditsPill.style.color = '#0284c7';
      creditsPill.style.borderColor = '#bae6fd';
    }

    if (maxResults) {
      maxResults.value = 5;
      maxResults.max = 5;
    }
    if (targetBadge) {
      targetBadge.textContent = '5 Free Leads (Trial)';
    }
    if (sliderHelper) {
      sliderHelper.textContent = '🎁 5 leads free without signup. Upgrade for up to 100+ leads!';
    }
    return;
  }

  // Logged-in Customer or Admin
  if (nameElem) nameElem.textContent = currentUser.name || 'User';
  if (emailElem) emailElem.textContent = currentUser.email || '';
  if (avatarElem) {
    const initials = (currentUser.name || 'U').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    avatarElem.textContent = initials;
  }
  if (btnGuestLogin) btnGuestLogin.classList.add('hidden');
  if (btnLogout) btnLogout.classList.remove('hidden');

  if (tenantPill) {
    tenantPill.textContent = currentUser.company ? `🏢 ${currentUser.company}` : `👤 ${currentUser.name}`;
  }

  if (maxResults) {
    maxResults.max = 100;
  }
  if (sliderHelper) {
    sliderHelper.textContent = 'Extract up to 100 verified leads in one batch.';
  }

  if (creditsPill) {
    if (currentUser.role === 'admin') {
      creditsPill.textContent = '👑 Master Admin (Unlimited)';
      creditsPill.style.background = '#fef3c7';
      creditsPill.style.color = '#b45309';
      creditsPill.style.borderColor = '#fde68a';
    } else {
      const remaining = Math.max(0, (currentUser.credits_limit || 0) - (currentUser.credits_used || 0));
      creditsPill.textContent = `🎯 Credits: ${remaining.toLocaleString()} / ${(currentUser.credits_limit || 0).toLocaleString()} Remaining`;
      creditsPill.style.background = '#ecfdf5';
      creditsPill.style.color = '#059669';
      creditsPill.style.borderColor = '#a7f3d0';
    }
  }

  // Show Master Admin tab if admin
  if (currentUser.role === 'admin') {
    if (navAdmin) navAdmin.classList.remove('hidden');
  } else {
    if (navAdmin) navAdmin.classList.add('hidden');
  }

  // Update export links with token query
  const token = getAuthToken();
  const csvQuick = document.getElementById('crm-quick-csv');
  const excelQuick = document.getElementById('crm-quick-excel');
  const csvMain = document.getElementById('btn-export-csv-main');
  const excelMain = document.getElementById('btn-export-excel-main');

  if (csvQuick) csvQuick.href = `/api/export/csv?token=${encodeURIComponent(token)}`;
  if (excelQuick) excelQuick.href = `/api/export/excel?token=${encodeURIComponent(token)}`;
  if (csvMain) csvMain.href = `/api/export/csv?token=${encodeURIComponent(token)}`;
  if (excelMain) excelMain.href = `/api/export/excel?token=${encodeURIComponent(token)}`;
}

// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const tabPanes = document.querySelectorAll('.tab-pane');
const pageTitle = document.getElementById('page-title');
const pageSubtitle = document.getElementById('page-subtitle');

// Stats Elements
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
const customQueryInput = document.getElementById('custom-query');
const presetCitySelect = document.getElementById('preset-city-select');
const presetLocalitySelect = document.getElementById('preset-locality-select');
const quickLocalityChips = document.getElementById('quick-locality-chips');
const maxResultsSlider = document.getElementById('max-results');
const targetCountBadge = document.getElementById('target-count-badge');

const btnStartScrape = document.getElementById('btn-start-scrape');
const btnStopScrape = document.getElementById('btn-stop-scrape');
const progressContainer = document.getElementById('progress-container');
const progressStatusText = document.getElementById('progress-status-text');
const progressPercent = document.getElementById('progress-percent');
const progressBar = document.getElementById('progress-bar');
const consoleLogs = document.getElementById('console-logs');
const btnClearLogs = document.getElementById('btn-clear-logs');

const liveLeadsList = document.getElementById('live-leads-list');
const streamPlaceholder = document.getElementById('stream-placeholder');
const liveExtractedCounter = document.getElementById('live-extracted-counter');

// CRM Elements
const crmSearch = document.getElementById('crm-search');
const filterStatus = document.getElementById('filter-status');
const filterArea = document.getElementById('filter-area');
const filterPhone = document.getElementById('filter-phone');
const btnRefreshLeads = document.getElementById('btn-refresh-leads');
const leadsTableBody = document.getElementById('leads-table-body');
const selectAllLeads = document.getElementById('select-all-leads');
const bulkActionsBar = document.getElementById('bulk-actions-bar');
const selectedCount = document.getElementById('selected-count');
const bulkStatusSelect = document.getElementById('bulk-status-select');
const btnApplyBulkStatus = document.getElementById('btn-apply-bulk-status');
const btnBulkDelete = document.getElementById('btn-bulk-delete');
const crmFooterStats = document.getElementById('crm-footer-stats');

// Import Elements
const importForm = document.getElementById('import-form');
const importFile = document.getElementById('import-file');
const btnImportSubmit = document.getElementById('btn-import-submit');
const fileNameDisplay = document.getElementById('file-name-display');
const importResult = document.getElementById('import-result');

// Admin Elements
const adminUsersTableBody = document.getElementById('admin-users-table-body');
const adminStatClients = document.getElementById('admin-stat-clients');
const adminStatActiveClients = document.getElementById('admin-stat-active-clients');
const adminStatTotalLeads = document.getElementById('admin-stat-total-leads');
const adminStatCreditsConsumed = document.getElementById('admin-stat-credits-consumed');
const btnOpenAddClientModal = document.getElementById('btn-open-add-client-modal');
const clientModal = document.getElementById('client-modal');
const btnCloseClientModal = document.getElementById('btn-close-client-modal');
const btnCancelClientModal = document.getElementById('btn-cancel-client-modal');
const clientForm = document.getElementById('client-form');
const modalClientId = document.getElementById('modal-client-id');
const modalClientTitle = document.getElementById('modal-client-title');
const clientName = document.getElementById('client-name');
const clientCompany = document.getElementById('client-company');
const clientEmail = document.getElementById('client-email');
const clientPassword = document.getElementById('client-password');
const clientPasswordHelp = document.getElementById('client-password-help');
const clientCredits = document.getElementById('client-credits');
const clientRole = document.getElementById('client-role');
const btnSaveClient = document.getElementById('btn-save-client');

// Pricing Modal Elements
const pricingModal = document.getElementById('pricing-modal');
const btnClosePricingModal = document.getElementById('btn-close-pricing-modal');
const btnHeaderUpgrade = document.getElementById('btn-header-upgrade');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuthSession();

  setupNavigation();
  setupScraperModeToggle();
  populateLocalitiesForSelectedCity();
  setupScraperEvents();
  setupCrmEvents();
  setupImportEvents();
  setupAdminEvents();
  setupPricingEvents();
  setupLogoutEvent();

  fetchStats();
  fetchAreas();
  fetchLeads();
});

// Logout
function setupLogoutEvent() {
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to log out?')) {
        localStorage.removeItem('pixelboost_token');
        localStorage.removeItem('pixelboost_user');
        currentUser = null;
        updateUserProfileUI();
        showToast('Logged out successfully', 'info');
      }
    });
  }
}

// Navigation Tabs
function setupNavigation() {
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tab = item.getAttribute('data-tab');
      switchTab(tab);
    });
  });
}

function switchTab(tab) {
  currentTab = tab;
  navItems.forEach(n => {
    if (n.getAttribute('data-tab') === tab) {
      n.classList.add('active');
    } else {
      n.classList.remove('active');
    }
  });

  tabPanes.forEach(pane => {
    if (pane.id === `tab-${tab}`) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  if (tab === 'scraper') {
    pageTitle.textContent = 'Lead Generation Studio';
    pageSubtitle.textContent = 'Extract verified phone numbers, WhatsApp contacts & local real estate brokers directly from Google Maps';
  } else if (tab === 'crm') {
    pageTitle.textContent = 'Calling Leads CRM';
    pageSubtitle.textContent = 'Manage leads, direct dial contacts, launch WhatsApp chats, and save caller logs';
    fetchLeads();
    fetchAreas();
  } else if (tab === 'export') {
    pageTitle.textContent = 'Export & Import Calling Sheets';
    pageSubtitle.textContent = 'Download formatted telecalling spreadsheets and merge existing lead lists';
  } else if (tab === 'pricing') {
    pageTitle.textContent = 'Plans & Pricing';
    pageSubtitle.textContent = 'Get verified real estate leads with instant WhatsApp delivery & CRM access';
  } else if (tab === 'admin') {
    pageTitle.textContent = 'Master Admin Management Hub';
    pageSubtitle.textContent = 'Manage customer tenants, allocate lead quotas, and oversee platform usage';
    fetchAdminStats();
    fetchAdminUsers();
  }
}

// Scraper Mode Toggle
function setupScraperModeToggle() {
  modeBtnPreset.addEventListener('click', () => {
    isCustomMode = false;
    modeBtnPreset.classList.add('active');
    modeBtnCustom.classList.remove('active');
    groupPresetCategory.classList.remove('hidden');
    groupCustomKeyword.classList.add('hidden');
    document.getElementById('chips-area-group').classList.remove('hidden');
  });

  modeBtnCustom.addEventListener('click', () => {
    isCustomMode = true;
    modeBtnCustom.classList.add('active');
    modeBtnPreset.classList.remove('active');
    groupPresetCategory.classList.add('hidden');
    groupCustomKeyword.classList.remove('hidden');
  });

  presetCitySelect.addEventListener('change', () => {
    populateLocalitiesForSelectedCity();
  });

  maxResultsSlider.addEventListener('input', (e) => {
    targetCountBadge.textContent = `${e.target.value} Leads`;
  });

  btnClearLogs.addEventListener('click', () => {
    consoleLogs.innerHTML = '';
  });
}

function populateLocalitiesForSelectedCity() {
  const city = presetCitySelect.value;
  const localities = CITY_AREA_PRESETS[city] || [
    "Central Area", "North Zone", "South Zone", "Commercial District", "Tech Hub", "VIP Road"
  ];

  presetLocalitySelect.innerHTML = '';
  const optAll = document.createElement('option');
  optAll.value = `All Popular Areas (${city})`;
  optAll.textContent = `📍 Entire City / All Popular Hubs (${city})`;
  presetLocalitySelect.appendChild(optAll);

  localities.forEach(loc => {
    const opt = document.createElement('option');
    opt.value = loc;
    opt.textContent = `📍 ${loc}`;
    presetLocalitySelect.appendChild(opt);
  });

  quickLocalityChips.innerHTML = '';
  localities.slice(0, 7).forEach((loc, idx) => {
    const chip = document.createElement('div');
    chip.className = `area-chip ${idx === 0 ? 'active' : ''}`;
    chip.textContent = loc;
    chip.addEventListener('click', () => {
      document.querySelectorAll('.area-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      presetLocalitySelect.value = loc;
    });
    quickLocalityChips.appendChild(chip);
  });

  presetLocalitySelect.value = localities[0];
}

// Scraper Engine Execution
function setupScraperEvents() {
  scraperForm.addEventListener('submit', (e) => {
    e.preventDefault();
    startScraping();
  });

  btnStopScrape.addEventListener('click', () => {
    stopScraping();
  });
}

function startScraping() {
  if (!currentUser && guestLeads.length >= 5) {
    openPricingModal(
      "🔒 5 Free Leads Limit Reached",
      "You have used your 5 free trial leads! Sign in or choose a plan below to extract 40 to 100+ verified contacts."
    );
    return;
  }

  let query = "";
  const city = presetCitySelect.value;
  const selectedLocality = presetLocalitySelect.value;
  const maxResults = parseInt(maxResultsSlider.value, 10);
  const category = searchCategory.value;

  if (isCustomMode) {
    query = customQueryInput.value.trim();
    if (!query) {
      showToast('Please enter a search keyword.', 'error');
      return;
    }
  } else {
    if (selectedLocality && !selectedLocality.startsWith("All Popular Areas")) {
      query = `${category} in ${selectedLocality} ${city}`;
    } else {
      query = `${category} in ${city}`;
    }
  }

  if (!currentUser) {
    guestLeads = [];
  }

  btnStartScrape.classList.add('hidden');
  btnStopScrape.classList.remove('hidden');
  progressContainer.classList.remove('hidden');
  progressBar.style.width = '5%';
  progressPercent.textContent = '5%';
  progressStatusText.textContent = 'Launching Headless Playwright Browser...';

  streamPlaceholder.classList.add('hidden');
  liveLeadsList.innerHTML = '';
  liveExtractedCounter.textContent = '0 Extracted';

  appendLog(`Starting extraction for query: "${query}" in ${city} (Target: ${maxResults} leads)...`, 'info');

  const token = getAuthToken();
  const url = `/api/scrape/stream?query=${encodeURIComponent(query)}&city=${encodeURIComponent(city)}&category=${encodeURIComponent(category)}&max_results=${maxResults}&token=${encodeURIComponent(token)}`;

  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      handleScrapeEvent(data);
    } catch (err) {
      console.error('SSE JSON error:', err);
    }
  };

  eventSource.onerror = (err) => {
    appendLog('Connection to scraping stream closed.', 'warn');
    cleanupScraperState();
  };
}

function handleScrapeEvent(data) {
  if (data.type === 'log') {
    appendLog(data.message, 'info');
  } else if (data.type === 'lead') {
    if (!currentUser && data.lead) {
      // Avoid duplicate push
      if (!guestLeads.some(l => l.id === data.lead.id || (l.name === data.lead.name && l.phone === data.lead.phone))) {
        guestLeads.push(data.lead);
      }
      statTotal.textContent = guestLeads.length;
      statPhone.textContent = guestLeads.filter(l => l.phone).length;
      sidebarLeadCount.textContent = guestLeads.length;
    }
    renderStreamLead(data.lead, data.is_new);
    liveExtractedCounter.textContent = `${data.scraped_count} Extracted`;
    
    if (data.progress) {
      progressBar.style.width = `${data.progress.percent}%`;
      progressPercent.textContent = `${data.progress.percent}%`;
      progressStatusText.textContent = `Extracting lead ${data.progress.current} of ${data.progress.total}...`;
    }

    // Refresh CRM stats and user credits dynamically
    if (currentUser) {
      fetchStats();
    }
  } else if (data.type === 'complete') {
    appendLog(`🎉 ${data.message}`, 'success');
    showToast(data.message, 'success');
    progressBar.style.width = '100%';
    progressPercent.textContent = '100%';
    progressStatusText.textContent = 'Extraction Complete!';
    cleanupScraperState();
    fetchStats();
    fetchLeads();
    fetchAreas();

    // If guest user extracted their 5 free leads: Show blurred cards + Lock button + Open pricing modal
    if (!currentUser && guestLeads.length >= 5) {
      // Render blurred stream card below extracted leads
      if (!document.getElementById('blurred-stream-block')) {
        const blurBlock = document.createElement('div');
        blurBlock.id = 'blurred-stream-block';
        blurBlock.className = 'blurred-stream-wrapper';
        blurBlock.innerHTML = `
          <div class="stream-lead-card blurred-lead-card">
            <div class="stream-lead-top"><span class="stream-lead-name">Shree Ram Property Consultants</span><span class="count-pill">⭐ 4.9 (128)</span></div>
            <div class="stream-lead-meta"><span class="phone-action-pill">+91 98250 XXXXX 🔒</span></div>
            <div class="stream-lead-addr">SG Highway, Ahmedabad, Gujarat</div>
          </div>
          <div class="stream-lead-card blurred-lead-card">
            <div class="stream-lead-top"><span class="stream-lead-name">Apex Realty Channel Partner</span><span class="count-pill">⭐ 4.8 (94)</span></div>
            <div class="stream-lead-meta"><span class="phone-action-pill">+91 97240 XXXXX 🔒</span></div>
            <div class="stream-lead-addr">Prahlad Nagar, Ahmedabad, Gujarat</div>
          </div>
          <div class="locked-lead-overlay">
            <div class="locked-lock-icon">🔒</div>
            <div class="locked-lead-title">45+ More Verified Brokers in this Area</div>
            <div class="locked-lead-desc">You've unlocked 5 free trial leads! Sign in or select a plan to extract 40 to 100+ verified contacts.</div>
            <button class="btn-unlock-leads-cta" onclick="app.openPricingModal()">⚡ Unlock Full List — Choose Plan</button>
          </div>
        `;
        liveLeadsList.appendChild(blurBlock);
      }

      // Lock extractor button
      btnStartScrape.innerHTML = '<span>🔒 5 Free Leads Used — Upgrade to Extract More</span>';
      btnStartScrape.classList.add('btn-locked');
      btnStartScrape.onclick = (e) => {
        e.preventDefault();
        openPricingModal(
          "🔒 Free Trial Limit Reached (5/5 Leads)",
          "You've experienced real-time lead extraction! Choose a plan below or sign in to extract more leads."
        );
      };

      const sliderHelper = document.getElementById('slider-helper-text');
      if (sliderHelper) {
        sliderHelper.textContent = '🔒 Free trial limit reached (5/5 leads). Sign in or choose a plan to extract 40 to 100+ leads.';
      }
      const targetBadge = document.getElementById('target-count-badge');
      if (targetBadge) {
        targetBadge.textContent = '5 / 5 Leads (Limit Reached)';
      }

      setTimeout(() => {
        openPricingModal(
          "🎉 5 Free Leads Extracted!",
          "You've experienced real-time lead extraction! Choose a plan below or sign in to unlock full CRM access & 100+ verified leads."
        );
      }, 900);
    }
  } else if (data.type === 'error') {
    appendLog(`❌ Error: ${data.message}`, 'error');
    showToast(data.message, 'error');
    cleanupScraperState();
  }
}

function stopScraping() {
  fetch('/api/scrape/stop', {
    method: 'POST',
    headers: getAuthHeaders()
  });
  appendLog('Cancellation requested by user...', 'warn');
  cleanupScraperState();
}

function cleanupScraperState() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  btnStartScrape.classList.remove('hidden');
  btnStopScrape.classList.add('hidden');
}

function appendLog(message, level = 'info') {
  const line = document.createElement('div');
  line.className = `log-line text-${level === 'error' ? 'rose' : level === 'success' ? 'emerald' : level === 'warn' ? 'amber' : 'dim'}`;
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  line.textContent = `[${time}] ${message}`;
  consoleLogs.appendChild(line);
  consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

function renderStreamLead(lead, isNew) {
  const item = document.createElement('div');
  item.className = 'stream-lead-card';
  
  const cleanNum = (lead.phone || '').replace(/[^\d+]/g, '');
  let waNum = cleanNum.replace(/\+/g, '');
  if (waNum.length === 10) waNum = '91' + waNum;

  const stars = lead.rating ? `⭐ ${lead.rating} (${lead.reviews_count || 0})` : '';

  item.innerHTML = `
    <div class="stream-lead-top">
      <span class="stream-lead-name">${escapeHtml(lead.name)}</span>
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

// CRM Pipeline Logic
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
      const id = parseInt(cb.getAttribute('data-id'), 10);
      if (isChecked) {
        selectedLeadIds.add(id);
      } else {
        selectedLeadIds.delete(id);
      }
    });
    updateBulkBar();
  });

  btnApplyBulkStatus.addEventListener('click', async () => {
    const status = bulkStatusSelect.value;
    if (!status) {
      showToast('Select a status to apply', 'warn');
      return;
    }
    if (selectedLeadIds.size === 0) return;

    try {
      const res = await fetch('/api/leads/bulk-status', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ ids: Array.from(selectedLeadIds), call_status: status })
      });
      if (res.ok) {
        showToast(`Updated status for ${selectedLeadIds.size} leads`, 'success');
        selectedLeadIds.clear();
        selectAllLeads.checked = false;
        fetchLeads();
        fetchStats();
      }
    } catch (err) {
      showToast('Failed to apply bulk status', 'error');
    }
  });

  btnBulkDelete.addEventListener('click', async () => {
    if (selectedLeadIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedLeadIds.size} selected leads?`)) return;

    try {
      const res = await fetch('/api/leads/bulk-delete', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ ids: Array.from(selectedLeadIds) })
      });
      if (res.ok) {
        showToast('Selected leads deleted', 'success');
        selectedLeadIds.clear();
        selectAllLeads.checked = false;
        fetchLeads();
        fetchStats();
      }
    } catch (err) {
      showToast('Failed to delete leads', 'error');
    }
  });
}

function updateBulkBar() {
  if (selectedLeadIds.size > 0) {
    bulkActionsBar.classList.remove('hidden');
    selectedCount.textContent = selectedLeadIds.size;
  } else {
    bulkActionsBar.classList.add('hidden');
  }
}

async function fetchStats() {
  try {
    const res = await fetch('/api/stats', {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();

    statTotal.textContent = data.total_leads || 0;
    statPhone.textContent = data.with_phone || 0;
    statInterested.textContent = (data.status_counts && (data.status_counts['Interested'] || 0) + (data.status_counts['Deal Closed'] || 0)) || 0;
    sidebarLeadCount.textContent = data.total_leads || 0;

    // Update remaining credits pill if returned
    if (data.user_credits && currentUser) {
      currentUser.credits_limit = data.user_credits.limit;
      currentUser.credits_used = data.user_credits.used;
      updateUserProfileUI();
    }
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

async function fetchAreas() {
  try {
    const res = await fetch('/api/areas', {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();
    filterArea.innerHTML = '<option value="">📍 All Areas / Cities</option>';
    (data.areas || []).forEach(area => {
      const opt = document.createElement('option');
      opt.value = area;
      opt.textContent = `📍 ${area}`;
      filterArea.appendChild(opt);
    });
  } catch (err) {
    console.error('Error fetching areas:', err);
  }
}

let guestLeads = [];

async function fetchLeads() {
  if (!currentUser) {
    // In Guest mode: display only the leads extracted during this session!
    leadsData = guestLeads;
    renderLeadsTable(leadsData);
    statTotal.textContent = guestLeads.length;
    statPhone.textContent = guestLeads.filter(l => l.phone).length;
    sidebarLeadCount.textContent = guestLeads.length;
    return;
  }

  const search = crmSearch.value.trim();
  const status = filterStatus.value;
  const city = filterArea.value;
  const hasPhone = filterPhone.value;

  let url = `/api/leads?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}&city=${encodeURIComponent(city)}&limit=500`;
  if (hasPhone) {
    url += `&has_phone=${hasPhone}`;
  }

  try {
    const res = await fetch(url, {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();
    leadsData = data.leads || [];
    renderLeadsTable(leadsData);
  } catch (err) {
    console.error('Error fetching leads:', err);
  }
}

function renderLeadsTable(leads) {
  leadsTableBody.innerHTML = '';
  selectedLeadIds.clear();
  updateBulkBar();
  selectAllLeads.checked = false;

  if (leads.length === 0) {
    leadsTableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-dim);">
          ${currentUser ? 'No leads matching your current filter. Click "Start Extracting Leads" to collect new contacts.' : 'No leads extracted yet. Go to "Lead Generator" and click "Start Extracting 5 Free Leads" to get your 5 free contacts!'}
        </td>
      </tr>
    `;
    crmFooterStats.textContent = 'Showing 0 of 0 leads';
    return;
  }

  crmFooterStats.textContent = `Showing ${leads.length} verified leads`;

  leads.forEach(lead => {
    const tr = document.createElement('tr');
    tr.id = `lead-row-${lead.id}`;

    const cleanNum = (lead.phone || '').replace(/[^\d+]/g, '');
    let waNum = cleanNum.replace(/\+/g, '');
    if (waNum.length === 10) waNum = '91' + waNum;

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
        <select class="status-pill status-${(lead.call_status || 'new').toLowerCase().replace(/\s+/g, '')}" onchange="updateLeadStatus(${lead.id}, this.value)">
          <option value="New" ${lead.call_status === 'New' ? 'selected' : ''}>🟢 New</option>
          <option value="Interested" ${lead.call_status === 'Interested' ? 'selected' : ''}>⭐ Interested</option>
          <option value="Follow-up" ${lead.call_status === 'Follow-up' ? 'selected' : ''}>📅 Follow-up</option>
          <option value="RNR" ${lead.call_status === 'RNR' ? 'selected' : ''}>📵 RNR / No Ans</option>
          <option value="Not Interested" ${lead.call_status === 'Not Interested' ? 'selected' : ''}>❌ Not Interested</option>
          <option value="Deal Closed" ${lead.call_status === 'Deal Closed' ? 'selected' : ''}>🏆 Deal Closed</option>
        </select>
      </td>
      <td>
        <input type="text" class="notes-inline-input" value="${escapeHtml(lead.call_notes || '')}" placeholder="Click to add note..." onchange="saveLeadNotes(${lead.id}, this.value)">
      </td>
      <td style="text-align: right;">
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          ${lead.maps_url ? `
            <a href="${escapeHtml(lead.maps_url)}" target="_blank" class="btn-control" style="padding: 4px 6px;" title="View on Maps">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </a>
          ` : ''}
          <button class="btn-control" style="padding: 4px 6px; color: var(--rose);" onclick="deleteLeadSingle(${lead.id})" title="Delete Lead">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </td>
    `;

    const checkbox = tr.querySelector('.lead-checkbox');
    checkbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        selectedLeadIds.add(lead.id);
      } else {
        selectedLeadIds.delete(lead.id);
      }
      updateBulkBar();
    });

    leadsTableBody.appendChild(tr);
  });

  // If Guest user has 5 free leads, append 3 blurred rows and upgrade banner
  if (!currentUser && leads.length >= 5) {
    const dummyNames = [
      { name: "Shree Ram Property Consultants", phone: "98250", loc: "SG Highway", cat: "Real Estate Brokers" },
      { name: "Apex Realty Channel Partner", phone: "97240", loc: "Prahlad Nagar", cat: "Builders & Developers" },
      { name: "Gujarat Commercial Real Estate Network", phone: "99090", loc: "Sindhu Bhavan Rd", cat: "Commercial Realty" }
    ];

    dummyNames.forEach(d => {
      const blurTr = document.createElement('tr');
      blurTr.className = 'blurred-row';
      blurTr.innerHTML = `
        <td><input type="checkbox" disabled></td>
        <td>
          <div class="contact-cell">
            <span class="contact-name">${d.name}</span>
            <span class="contact-cat">${d.cat} • Web • IG</span>
          </div>
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <span class="phone-action-pill">+91 ${d.phone} XXXXX 🔒</span>
            <span class="wa-action-pill">WA 🔒</span>
          </div>
        </td>
        <td><span style="font-size: 0.78rem; color: var(--text-secondary);">${d.loc}</span></td>
        <td><span class="count-pill">⭐ 4.9 (86)</span></td>
        <td><span class="status-pill status-new">🟢 New</span></td>
        <td><input type="text" class="notes-inline-input" value="Verified broker contact..." disabled></td>
        <td style="text-align: right;"><span class="text-dim-xs">🔒 Locked</span></td>
      `;
      leadsTableBody.appendChild(blurTr);
    });

    const bannerTr = document.createElement('tr');
    bannerTr.innerHTML = `
      <td colspan="8" style="padding: 14px 18px; background: #fffbeb; border-top: 1px dashed #fde68a;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.4rem;">🔒</span>
            <div>
              <strong style="font-size: 0.88rem; color: #92400e;">45+ More Verified Brokers in this Area (Hidden)</strong>
              <div style="font-size: 0.78rem; color: #b45309;">You've unlocked 5 free trial leads! Sign in or choose a plan to access the complete list with dialer & Excel exports.</div>
            </div>
          </div>
          <button class="btn-crm-unlock" onclick="app.openPricingModal()">⚡ Unlock Full List — View Plans</button>
        </div>
      </td>
    `;
    leadsTableBody.appendChild(bannerTr);
  }
}

// Inline Status Update
async function updateLeadStatus(leadId, status) {
  try {
    const res = await fetch(`/api/leads/${leadId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ call_status: status })
    });
    if (res.ok) {
      showToast(`Status updated to ${status}`, 'success');
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
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
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
    const res = await fetch(`/api/leads/${leadId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
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

// Copy to Clipboard
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
        headers: getAuthHeaders(),
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

// ==========================================================================
// Master Admin Management Logic (CK Super Admin)
// ==========================================================================
function setupAdminEvents() {
  if (btnOpenAddClientModal) {
    btnOpenAddClientModal.addEventListener('click', () => {
      openClientModal();
    });
  }

  if (btnCloseClientModal) {
    btnCloseClientModal.addEventListener('click', () => closeClientModal());
  }

  if (btnCancelClientModal) {
    btnCancelClientModal.addEventListener('click', () => closeClientModal());
  }

  if (clientForm) {
    clientForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      saveClientAccount();
    });
  }
}

async function fetchAdminStats() {
  try {
    const res = await fetch('/api/admin/stats', {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();
    if (adminStatClients) adminStatClients.textContent = data.total_clients || 0;
    if (adminStatActiveClients) adminStatActiveClients.textContent = data.active_clients || 0;
    if (adminStatTotalLeads) adminStatTotalLeads.textContent = (data.total_leads || 0).toLocaleString();
    if (adminStatCreditsConsumed) adminStatCreditsConsumed.textContent = (data.total_credits_consumed || 0).toLocaleString();
  } catch (err) {
    console.error('Error fetching admin stats:', err);
  }
}

async function fetchAdminUsers() {
  try {
    const res = await fetch('/api/admin/users', {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();
    renderAdminUsersTable(data.users || []);
  } catch (err) {
    console.error('Error fetching admin users:', err);
  }
}

function renderAdminUsersTable(users) {
  if (!adminUsersTableBody) return;
  adminUsersTableBody.innerHTML = '';

  if (users.length === 0) {
    adminUsersTableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 30px; color: var(--text-dim);">
          No customer accounts found. Click "+ Add New Customer Account" to onboard your first client.
        </td>
      </tr>
    `;
    return;
  }

  users.forEach(user => {
    const tr = document.createElement('tr');
    const limit = user.credits_limit || 1000;
    const used = user.credits_used || 0;
    const pct = Math.min(100, Math.round((used / limit) * 100));
    const isSuspended = user.status === 'suspended';

    tr.innerHTML = `
      <td>
        <div class="contact-cell">
          <span class="contact-name">${escapeHtml(user.name)}</span>
          <span class="contact-cat">${escapeHtml(user.company || 'Direct Client')}</span>
        </div>
      </td>
      <td>
        <span style="font-family: monospace; font-size: 0.82rem; color: var(--text-secondary);">${escapeHtml(user.email)}</span>
      </td>
      <td>
        <span class="status-pill ${user.role === 'admin' ? 'status-interested' : 'status-new'}">${user.role.toUpperCase()}</span>
      </td>
      <td>
        <div class="credit-bar-container">
          <div class="credit-bar-text">
            <span>${used.toLocaleString()} / ${limit >= 999999 ? 'Unlimited' : limit.toLocaleString()}</span>
            <span style="float: right;">${limit >= 999999 ? '—' : pct + '%'}</span>
          </div>
          <div class="credit-bar-bg">
            <div class="credit-bar-fill" style="width: ${limit >= 999999 ? '100%' : pct + '%'}; background: ${pct > 90 ? 'var(--rose)' : 'var(--primary)'};"></div>
          </div>
        </div>
      </td>
      <td>
        <span class="count-pill">📊 ${(user.actual_leads_count || 0).toLocaleString()} Leads</span>
      </td>
      <td>
        <span class="status-pill ${isSuspended ? 'status-notinterested' : 'status-dealclosed'}">
          ${isSuspended ? '🔴 Suspended' : '🟢 Active'}
        </span>
      </td>
      <td style="text-align: right;">
        <div style="display: flex; justify-content: flex-end; gap: 6px;">
          <button class="btn-control" onclick="editClientAccount(${user.id})" title="Edit Credits / Details">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            <span>Edit</span>
          </button>
          ${user.role !== 'admin' ? `
            <button class="btn-control" onclick="toggleUserStatus(${user.id}, '${isSuspended ? 'active' : 'suspended'}')" title="${isSuspended ? 'Activate Client' : 'Suspend Client'}">
              <span>${isSuspended ? 'Activate' : 'Suspend'}</span>
            </button>
            <button class="btn-control" style="color: var(--rose);" onclick="deleteClientAccount(${user.id}, '${escapeJs(user.name)}')" title="Delete Client">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          ` : ''}
        </div>
      </td>
    `;
    adminUsersTableBody.appendChild(tr);
  });
}

function openClientModal(client = null) {
  if (client) {
    modalClientId.value = client.id;
    modalClientTitle.textContent = `Edit Customer: ${client.name}`;
    clientName.value = client.name || '';
    clientCompany.value = client.company || '';
    clientEmail.value = client.email || '';
    clientEmail.disabled = true;
    clientPassword.value = '';
    clientPasswordHelp.textContent = 'Leave blank to keep existing password';
    clientCredits.value = client.credits_limit || 1000;
    clientRole.value = client.role || 'client';
  } else {
    modalClientId.value = '';
    modalClientTitle.textContent = 'Add New Customer Tenant';
    clientName.value = '';
    clientCompany.value = '';
    clientEmail.value = '';
    clientEmail.disabled = false;
    clientPassword.value = '';
    clientPassword.required = true;
    clientPasswordHelp.textContent = 'Set initial login password (min 6 chars)';
    clientCredits.value = '1000';
    clientRole.value = 'client';
  }
  clientModal.classList.remove('hidden');
}

function closeClientModal() {
  clientModal.classList.add('hidden');
}

window.editClientAccount = async function(userId) {
  try {
    const res = await fetch('/api/admin/users', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    const client = (data.users || []).find(u => u.id === userId);
    if (client) {
      openClientModal(client);
    }
  } catch (err) {
    showToast('Failed to load client details', 'error');
  }
};

window.toggleUserStatus = async function(userId, newStatus) {
  try {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`Client account status changed to ${newStatus}`, 'success');
      fetchAdminStats();
      fetchAdminUsers();
    }
  } catch (err) {
    showToast('Failed to update status', 'error');
  }
};

window.deleteClientAccount = async function(userId, userName) {
  if (!confirm(`Are you sure you want to delete customer "${userName}" and all their leads?`)) return;
  try {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Customer account deleted', 'success');
      fetchAdminStats();
      fetchAdminUsers();
    }
  } catch (err) {
    showToast('Failed to delete user', 'error');
  }
};

async function saveClientAccount() {
  const id = modalClientId.value;
  const name = clientName.value.trim();
  const company = clientCompany.value.trim();
  const email = clientEmail.value.trim();
  const password = clientPassword.value;
  const credits = parseInt(clientCredits.value, 10);
  const role = clientRole.value;

  btnSaveClient.disabled = true;
  btnSaveClient.innerHTML = '<span>Saving Account...</span>';

  try {
    let res;
    if (id) {
      // Edit
      const payload = {
        name,
        company,
        credits_limit: credits,
        role
      };
      if (password) payload.password = password;
      res = await fetch(`/api/admin/users/${id}`, {
        method: 'PATCH',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      });
    } else {
      // Create
      res = await fetch('/api/admin/users', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          name,
          company,
          email,
          password,
          credits_limit: credits,
          role
        })
      });
    }

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to save customer account.');
    }

    showToast(data.message || 'Customer saved successfully!', 'success');
    closeClientModal();
    fetchAdminStats();
    fetchAdminUsers();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btnSaveClient.disabled = false;
    btnSaveClient.innerHTML = '<span>Save Customer Account</span>';
  }
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

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast-item';
  if (type === 'error') toast.style.background = '#e11d48';
  if (type === 'success') toast.style.background = '#059669';
  if (type === 'warn') toast.style.background = '#d97706';
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// Pricing & Upgrade Modal Functions
function setupPricingEvents() {
  if (btnHeaderUpgrade) {
    btnHeaderUpgrade.addEventListener('click', () => {
      switchTab('pricing');
    });
  }

  if (btnClosePricingModal) {
    btnClosePricingModal.addEventListener('click', () => {
      closePricingModal();
    });
  }

  if (pricingModal) {
    pricingModal.addEventListener('click', (e) => {
      if (e.target === pricingModal) {
        closePricingModal();
      }
    });
  }
}

function openPricingModal(customTitle, customSubtitle) {
  if (!pricingModal) return;
  const titleEl = document.getElementById('pricing-modal-title');
  const subEl = document.getElementById('pricing-modal-subtitle');
  if (titleEl && customTitle) titleEl.textContent = customTitle;
  if (subEl && customSubtitle) subEl.textContent = customSubtitle;
  pricingModal.classList.remove('hidden');
}

function closePricingModal() {
  if (pricingModal) pricingModal.classList.add('hidden');
}

function buyPlan(planName, leads, price) {
  const isCustom = price === 'Custom' || String(price).toLowerCase().includes('custom');
  const priceText = isCustom ? 'Custom Enterprise Quote' : `₹${price}`;
  const leadsText = isCustom ? '250+ Custom Leads' : `${leads} Leads`;

  const msg = `Hi CK! I want to activate the *${planName} Plan* (${leadsText} @ ${priceText}) for PixelBoost PropLeadAi.\n\nPlease share payment details / UPI to activate my account.`;
  const waUrl = `https://wa.me/919999999999?text=${encodeURIComponent(msg)}`;

  showToast(`Opening WhatsApp order for ${planName} Plan (${priceText})...`, 'success');
  window.open(waUrl, '_blank');
}

function startFreeTrial() {
  switchTab('scraper');
  const maxResults = document.getElementById('max-results');
  if (maxResults) {
    maxResults.value = 5;
    const badge = document.getElementById('target-count-badge');
    if (badge) badge.textContent = '5 Free Leads (Trial)';
  }
  showToast("🎁 Free Trial Active! Choose your target city and click 'Start Extracting 5 Free Leads'.", "info");
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Expose on global window object for HTML inline buttons
window.app = {
  buyPlan,
  startFreeTrial,
  openPricingModal,
  closePricingModal,
  switchTab
};

