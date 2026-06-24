"""
api/admin_template.py
HTML templates for the admin dashboard.
LOGIN_HTML  — password gate page
DASHBOARD_HTML — full SPA admin panel (served after auth)
"""

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Login — XOOX Bot</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font-family:'Inter',sans-serif;min-height:100vh;
  display:flex;align-items:center;justify-content:center;
  background-image:radial-gradient(ellipse at 50% 0%,rgba(124,58,237,.12) 0%,transparent 70%)}
.card{background:#161b22;border:1px solid #21262d;border-radius:20px;padding:44px 40px;
  width:100%;max-width:400px;text-align:center;
  box-shadow:0 24px 64px rgba(0,0,0,.5)}
.logo{font-size:52px;margin-bottom:14px;filter:drop-shadow(0 0 20px rgba(124,58,237,.4))}
h1{font-size:22px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px}
.sub{font-size:14px;color:#8b949e;margin-bottom:32px}
.err-box{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.35);
  color:#ef4444;padding:11px 16px;border-radius:10px;font-size:13px;margin-bottom:18px}
input{width:100%;background:#0d1117;border:1px solid #30363d;border-radius:10px;
  padding:13px 16px;color:#e6edf3;font-size:15px;font-family:'Inter',sans-serif;
  outline:none;transition:border-color .2s;margin-bottom:14px;letter-spacing:.5px}
input:focus{border-color:#7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.15)}
input::placeholder{letter-spacing:0;color:#484f58}
button{width:100%;background:linear-gradient(135deg,#7c3aed,#6d28d9);border:none;
  border-radius:10px;padding:14px;color:#fff;font-size:15px;font-weight:600;
  font-family:'Inter',sans-serif;cursor:pointer;transition:all .2s;letter-spacing:.2px}
button:hover{background:linear-gradient(135deg,#8b5cf6,#7c3aed);
  box-shadow:0 8px 24px rgba(124,58,237,.4);transform:translateY(-1px)}
.footer{margin-top:20px;font-size:12px;color:#484f58}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🤖</div>
  <h1>Admin Dashboard</h1>
  <p class="sub">XOOX Bot Control Panel</p>
  ##ERROR##
  <form method="POST" action="/admin/login">
    <input type="password" name="password" placeholder="Enter password" autofocus autocomplete="current-password">
    <button type="submit">Login →</button>
  </form>
  <p class="footer">Restricted access — authorised personnel only</p>
</div>
</body>
</html>"""


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Dashboard — XOOX Bot</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d1117;--surface:#161b22;--surface2:#1c2128;--border:#21262d;
  --accent:#7c3aed;--accent-glow:rgba(124,58,237,.15);--accent-light:#a78bfa;
  --success:#22c55e;--warning:#f59e0b;--danger:#ef4444;--info:#3b82f6;
  --text:#e6edf3;--muted:#8b949e;--font:'Inter',system-ui,sans-serif}
body{background:var(--bg);color:var(--text);font-family:var(--font);min-height:100vh;display:flex}

/* ── Sidebar ── */
.sidebar{width:220px;min-height:100vh;background:var(--surface);border-right:1px solid var(--border);
  display:flex;flex-direction:column;position:fixed;top:0;left:0;bottom:0;z-index:100}
.sidebar-logo{padding:22px 20px 18px;border-bottom:1px solid var(--border)}
.sidebar-logo .bot-name{font-size:17px;font-weight:700;letter-spacing:-.3px}
.sidebar-logo .bot-sub{font-size:11px;color:var(--muted);margin-top:3px}
.nav{flex:1;padding:10px 8px;display:flex;flex-direction:column;gap:2px}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;
  cursor:pointer;font-size:13.5px;font-weight:500;color:var(--muted);
  transition:all .15s;border:1px solid transparent;background:none;width:100%;text-align:left}
.nav-item:hover{background:var(--surface2);color:var(--text)}
.nav-item.active{background:var(--accent-glow);color:var(--accent-light);border-color:rgba(124,58,237,.3)}
.nav-badge{margin-left:auto;background:var(--danger);color:#fff;font-size:10px;
  font-weight:700;padding:2px 7px;border-radius:10px;min-width:20px;text-align:center}
.nav-badge.zero{background:var(--surface2);color:var(--muted)}
.sidebar-footer{padding:10px 8px;border-top:1px solid var(--border)}
.logout-btn{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;
  cursor:pointer;font-size:13.5px;font-weight:500;color:var(--danger);
  transition:all .15s;border:none;background:none;width:100%;text-decoration:none}
.logout-btn:hover{background:rgba(239,68,68,.1)}

/* ── Main ── */
.main{margin-left:220px;flex:1;min-height:100vh;display:flex;flex-direction:column}
.topbar{padding:18px 28px;border-bottom:1px solid var(--border);background:var(--surface);
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  position:sticky;top:0;z-index:50}
.page-title{font-size:18px;font-weight:600;letter-spacing:-.3px}
.topbar-meta{font-size:12px;color:var(--muted)}
.content{padding:24px 28px;flex:1}
.tab-panel{display:none}
.tab-panel.active{display:block}

/* ── Stat cards ── */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-bottom:22px}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:18px;position:relative;overflow:hidden;transition:border-color .2s,transform .2s}
.stat-card:hover{border-color:var(--accent);transform:translateY(-2px)}
.stat-card .lbl{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.6px;margin-bottom:8px}
.stat-card .val{font-size:26px;font-weight:700;letter-spacing:-1px}
.stat-card .ico{position:absolute;right:14px;top:14px;font-size:20px;opacity:.5}
.stat-card.c-accent{border-color:rgba(124,58,237,.35)} .stat-card.c-accent .val{color:var(--accent-light)}
.stat-card.c-success .val{color:var(--success)}
.stat-card.c-warning .val{color:var(--warning)}
.stat-card.c-danger  .val{color:var(--danger)}

/* ── Chart ── */
.chart-wrap{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:20px;margin-bottom:20px}

/* ── Table ── */
.tbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  overflow:hidden;margin-bottom:20px}
.tbl-head{padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.tbl-head h3{font-size:14px;font-weight:600}
.tbl-meta{font-size:12px;color:var(--muted)}
.search-box{background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:7px 12px;color:var(--text);font-size:13px;font-family:var(--font);
  width:230px;outline:none;transition:border-color .15s}
.search-box:focus{border-color:var(--accent)}
.search-box::placeholder{color:var(--muted)}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:10px 16px;font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.5px;background:var(--surface2);
  border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:11px 16px;font-size:13px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.018)}
.mono{font-family:'Courier New',monospace;font-size:12px;color:var(--muted)}

/* ── Badges ── */
.bdg{display:inline-block;padding:3px 8px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:.2px}
.bdg-approved{background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.3)}
.bdg-pending {background:rgba(245,158,11,.15);color:#f59e0b;border:1px solid rgba(245,158,11,.3)}
.bdg-cancelled{background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3)}
.bdg-none   {background:rgba(139,148,158,.12);color:#8b949e;border:1px solid rgba(139,148,158,.25)}
.bdg-stars  {background:rgba(251,191,36,.15);color:#fbbf24;border:1px solid rgba(251,191,36,.3)}
.bdg-crypto {background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3)}
.bdg-regular{background:rgba(139,148,158,.12);color:#8b949e;border:1px solid rgba(139,148,158,.25)}
.bdg-medium {background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3)}
.bdg-premium{background:rgba(251,191,36,.15);color:#fbbf24;border:1px solid rgba(251,191,36,.3)}

/* ── Buttons ── */
.btn{display:inline-flex;align-items:center;gap:4px;padding:5px 10px;border-radius:6px;
  font-size:12px;font-weight:500;cursor:pointer;border:1px solid transparent;
  font-family:var(--font);transition:all .15s}
.btn-approve{background:rgba(34,197,94,.12);color:#22c55e;border-color:rgba(34,197,94,.3)}
.btn-approve:hover{background:rgba(34,197,94,.22)}
.btn-cancel {background:rgba(239,68,68,.12);color:#ef4444;border-color:rgba(239,68,68,.3)}
.btn-cancel:hover{background:rgba(239,68,68,.22)}
.btn-unban  {background:rgba(59,130,246,.12);color:#60a5fa;border-color:rgba(59,130,246,.3)}
.btn-unban:hover{background:rgba(59,130,246,.22)}

/* ── Pagination ── */
.pagination{display:flex;align-items:center;gap:8px;padding:12px 18px;
  border-top:1px solid var(--border);font-size:13px;color:var(--muted)}
.pg-btn{padding:5px 10px;border-radius:6px;border:1px solid var(--border);
  background:var(--surface2);color:var(--text);cursor:pointer;font-size:13px;
  font-family:var(--font);transition:all .15s}
.pg-btn:hover:not([disabled]){border-color:var(--accent);color:var(--accent-light)}
.pg-btn[disabled]{opacity:.4;cursor:not-allowed}

/* ── States ── */
.loading-state{display:flex;align-items:center;justify-content:center;padding:52px;
  color:var(--muted);font-size:14px;gap:10px}
.spinner{width:18px;height:18px;border:2px solid var(--border);
  border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.empty-state{text-align:center;padding:52px;color:var(--muted)}
.empty-icon{font-size:40px;margin-bottom:12px}
.empty-state p{font-size:14px}

/* ── Toast ── */
#toast{position:fixed;bottom:24px;right:24px;background:var(--surface2);
  border:1px solid var(--border);border-radius:10px;padding:12px 18px;font-size:14px;
  box-shadow:0 8px 30px rgba(0,0,0,.4);transform:translateY(60px);opacity:0;
  transition:all .3s cubic-bezier(.34,1.56,.64,1);z-index:999}
#toast.show{transform:translateY(0);opacity:1}
#toast.ok{border-color:rgba(34,197,94,.4)}
#toast.err{border-color:rgba(239,68,68,.4)}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="sidebar-logo">
    <div class="bot-name">🤖 XOOX Admin</div>
    <div class="bot-sub">Control Panel</div>
  </div>
  <nav class="nav">
    <button class="nav-item active" onclick="switchTab('overview',this)">
      <span>📊</span> Overview
    </button>
    <button class="nav-item" onclick="switchTab('users',this)">
      <span>👥</span> Users
    </button>
    <button class="nav-item" onclick="switchTab('buyers',this)">
      <span>💰</span> Buyers
    </button>
    <button class="nav-item" id="nav-pending" onclick="switchTab('pending',this)">
      <span>⏳</span> Pending
      <span class="nav-badge zero" id="pending-badge">0</span>
    </button>
    <button class="nav-item" onclick="switchTab('banned',this)">
      <span>🚫</span> Banned
    </button>
    <button class="nav-item" onclick="switchTab('videos',this)">
      <span>🎬</span> Videos
    </button>
  </nav>
  <div class="sidebar-footer">
    <a href="/admin/logout" class="logout-btn"><span>🚪</span> Logout</a>
  </div>
</aside>

<div class="main">
  <div class="topbar">
    <div class="page-title" id="page-title">📊 Overview</div>
    <div class="topbar-meta" id="topbar-meta">Loading…</div>
  </div>
  <div class="content">

    <!-- Overview -->
    <div class="tab-panel active" id="tab-overview">
      <div class="stats-grid" id="stats-grid"><div class="loading-state"><div class="spinner"></div> Loading…</div></div>
      <div class="chart-wrap" style="height:260px"><canvas id="funnelChart"></canvas></div>
      <div id="overview-tables"></div>
    </div>

    <!-- Users -->
    <div class="tab-panel" id="tab-users">
      <div class="tbl-wrap">
        <div class="tbl-head">
          <h3>All Users</h3>
          <input class="search-box" id="users-search" placeholder="🔍  Search ID, @username, name…" oninput="usersSearchDebounce()">
        </div>
        <div id="users-body"></div>
        <div class="pagination" id="users-pager"></div>
      </div>
    </div>

    <!-- Buyers -->
    <div class="tab-panel" id="tab-buyers">
      <div class="tbl-wrap">
        <div class="tbl-head">
          <h3>Stars Purchases</h3>
          <span class="tbl-meta" id="buyers-meta"></span>
        </div>
        <div id="buyers-body"></div>
        <div class="pagination" id="buyers-pager"></div>
      </div>
    </div>

    <!-- Pending -->
    <div class="tab-panel" id="tab-pending">
      <div class="tbl-wrap">
        <div class="tbl-head">
          <h3>Pending Approvals</h3>
          <span class="tbl-meta" id="pending-meta"></span>
        </div>
        <div id="pending-body"></div>
      </div>
    </div>

    <!-- Banned -->
    <div class="tab-panel" id="tab-banned">
      <div class="tbl-wrap">
        <div class="tbl-head"><h3>Banned Users</h3></div>
        <div id="banned-body"></div>
      </div>
    </div>

    <!-- Videos -->
    <div class="tab-panel" id="tab-videos">
      <div class="tbl-wrap">
        <div class="tbl-head"><h3>Demo Videos</h3></div>
        <div id="videos-body"></div>
      </div>
    </div>

  </div>
</div>

<div id="toast"></div>

<script>
// ── State ──────────────────────────────────────────────────────────────────────
var usersPage = 1, buyersPage = 1, usersSearch = '', searchTimer, funnelChart;

const TAB_TITLES = {
  overview:'📊 Overview', users:'👥 Users', buyers:'💰 Buyers',
  pending:'⏳ Pending', banned:'🚫 Banned', videos:'🎬 Videos'
};

// ── Helpers ────────────────────────────────────────────────────────────────────
function toast(msg, type) {
  var t = document.getElementById('toast');
  t.textContent = (type === 'err' ? '❌ ' : '✅ ') + msg;
  t.className = 'show ' + (type || 'ok');
  setTimeout(function(){ t.className = ''; }, 3500);
}

function setLoading(id) {
  document.getElementById(id).innerHTML = '<div class="loading-state"><div class="spinner"></div> Loading…</div>';
}

function setEmpty(id, msg) {
  document.getElementById(id).innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>' + msg + '</p></div>';
}

function badge(status) {
  var s = status || 'none';
  return '<span class="bdg bdg-' + s + '">' + s.toUpperCase() + '</span>';
}

function methodBadge(m) {
  var s = m || 'crypto';
  return '<span class="bdg bdg-' + s + '">' + s.toUpperCase() + '</span>';
}

function typeBadge(t) {
  var s = t || 'regular';
  return '<span class="bdg bdg-' + s + '">' + s.toUpperCase() + '</span>';
}

function fmtDate(dt) { return dt ? String(dt).slice(0, 10) : '—'; }

function fmtNum(n) { return (n || 0).toLocaleString(); }

async function post(url, data) {
  var r = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  return r.json();
}

function pager(pagerId, page, pages, prevFn, nextFn) {
  var c = document.getElementById(pagerId);
  if (pages <= 1) { c.innerHTML = ''; return; }
  c.innerHTML =
    '<button class="pg-btn" onclick="' + prevFn + '()" ' + (page <= 1 ? 'disabled' : '') + '>← Prev</button>' +
    '<span>Page ' + page + ' of ' + pages + '</span>' +
    '<button class="pg-btn" onclick="' + nextFn + '()" ' + (page >= pages ? 'disabled' : '') + '>Next →</button>';
}

// ── Tab switching ──────────────────────────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(function(p){ p.classList.remove('active'); });
  document.querySelectorAll('.nav-item').forEach(function(b){ b.classList.remove('active'); });
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
  document.getElementById('page-title').textContent = TAB_TITLES[name];
  if (name === 'overview') loadOverview();
  else if (name === 'users') { usersPage = 1; loadUsers(); }
  else if (name === 'buyers') { buyersPage = 1; loadBuyers(); }
  else if (name === 'pending') loadPending();
  else if (name === 'banned') loadBanned();
  else if (name === 'videos') loadVideos();
}

// ── Overview ───────────────────────────────────────────────────────────────────
async function loadOverview() {
  setLoading('stats-grid');
  document.getElementById('topbar-meta').textContent = 'Loading live data…';
  var d = await fetch('/api/admin/stats').then(function(r){ return r.json(); });

  // Badge update
  var badge_el = document.getElementById('pending-badge');
  badge_el.textContent = d.pending;
  badge_el.className = 'nav-badge' + (d.pending > 0 ? '' : ' zero');

  document.getElementById('stats-grid').innerHTML =
    card('c-accent','👥','Total Users', fmtNum(d.total_users)) +
    card('c-success','✅','Approved',    fmtNum(d.approved)) +
    card('c-warning','⏳','Pending',     fmtNum(d.pending)) +
    card('',         '❌','Cancelled',   fmtNum(d.cancelled)) +
    card('',         '📅','New Today',   fmtNum(d.new_today)) +
    card('',         '📆','This Week',   fmtNum(d.new_week)) +
    card('c-success','📈','Conv. Rate',  d.conversion_rate) +
    card('c-accent', '💵','Est. Revenue','$' + fmtNum(d.total_revenue));

  document.getElementById('topbar-meta').textContent = fmtNum(d.total_users) + ' total users';

  // Funnel chart
  if (funnelChart) funnelChart.destroy();
  var ctx = document.getElementById('funnelChart').getContext('2d');
  var f = d.funnel;
  funnelChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Viewed Pricing','Clicked Plan','Submitted','Approved'],
      datasets: [{
        data: [f.viewed_pricing, f.clicked_plan, f.submitted, f.approved],
        backgroundColor: ['rgba(124,58,237,.7)','rgba(124,58,237,.55)','rgba(124,58,237,.4)','rgba(34,197,94,.7)'],
        borderColor: ['#7c3aed','#7c3aed','#7c3aed','#22c55e'],
        borderWidth: 1, borderRadius: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        title: {display: true, text: 'Conversion Funnel', color: '#e6edf3',
          font: {size: 13, family: 'Inter', weight: '600'}}
      },
      scales: {
        x: {ticks:{color:'#8b949e'}, grid:{color:'rgba(255,255,255,.05)'}},
        y: {ticks:{color:'#8b949e'}, grid:{color:'rgba(255,255,255,.05)'}, beginAtZero: true}
      }
    }
  });

  // Extra tables
  var extra = '';
  var plans = d.plan_breakdown;
  if (plans && Object.keys(plans).length > 0) {
    var rows = Object.entries(plans).map(function(e){
      return '<tr><td>' + cap(e[0]) + '</td><td>' + e[1] + '</td></tr>';
    }).join('');
    extra += miniTable('Plan Breakdown (Approved)', '<th>Plan</th><th>Users</th>', rows);
  }
  if (d.top_referrers && d.top_referrers.length > 0) {
    var rrows = d.top_referrers.map(function(r){
      return '<tr><td><span class="mono">' + r.user_id + '</span></td><td>' +
        (r.username ? '@' + r.username : '—') + '</td><td>' + r.referral_count + '</td></tr>';
    }).join('');
    extra += miniTable('Top Referrers', '<th>ID</th><th>Username</th><th>Referrals</th>', rrows);
  }
  document.getElementById('overview-tables').innerHTML = extra;
}

function card(cls, icon, label, val) {
  return '<div class="stat-card ' + cls + '"><div class="ico">' + icon + '</div>' +
    '<div class="lbl">' + label + '</div><div class="val">' + val + '</div></div>';
}

function miniTable(title, heads, rows) {
  return '<div class="tbl-wrap"><div class="tbl-head"><h3>' + title + '</h3></div>' +
    '<table><thead><tr>' + heads + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : '—'; }

// ── Users ──────────────────────────────────────────────────────────────────────
function usersSearchDebounce() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(function(){
    usersSearch = document.getElementById('users-search').value;
    usersPage = 1;
    loadUsers();
  }, 350);
}

async function loadUsers() {
  setLoading('users-body');
  var url = '/api/admin/users?page=' + usersPage + '&search=' + encodeURIComponent(usersSearch);
  var d = await fetch(url).then(function(r){ return r.json(); });
  document.getElementById('topbar-meta').textContent = fmtNum(d.total) + ' users';

  if (!d.users || d.users.length === 0) { setEmpty('users-body', 'No users found.'); return; }

  var rows = d.users.map(function(u){
    return '<tr><td><span class="mono">' + u.user_id + '</span></td>' +
      '<td>' + (u.username ? '@' + u.username : '—') + '</td>' +
      '<td>' + (u.full_name || '—') + '</td>' +
      '<td>' + badge(u.payment_status) + '</td>' +
      '<td>' + cap(u.selected_plan || '—') + '</td>' +
      '<td>⭐ ' + fmtNum(u.stars_balance) + '</td>' +
      '<td>' + methodBadge(u.payment_method) + '</td>' +
      '<td style="color:var(--muted)">' + fmtDate(u.join_date) + '</td>' +
      '<td style="color:var(--muted)">' + fmtDate(u.last_seen) + '</td></tr>';
  }).join('');

  document.getElementById('users-body').innerHTML =
    '<table><thead><tr><th>ID</th><th>Username</th><th>Name</th><th>Status</th>' +
    '<th>Plan</th><th>Stars</th><th>Method</th><th>Joined</th><th>Last Seen</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>';

  pager('users-pager', d.page, d.pages, 'usersPrev', 'usersNext');
}
function usersNext() { usersPage++; loadUsers(); }
function usersPrev() { usersPage--; loadUsers(); }

// ── Buyers ─────────────────────────────────────────────────────────────────────
async function loadBuyers() {
  setLoading('buyers-body');
  var d = await fetch('/api/admin/buyers?page=' + buyersPage).then(function(r){ return r.json(); });
  document.getElementById('buyers-meta').textContent = fmtNum(d.total) + ' total';
  document.getElementById('topbar-meta').textContent = fmtNum(d.total) + ' purchases';

  if (!d.buyers || d.buyers.length === 0) { setEmpty('buyers-body', 'No purchases yet.'); return; }

  var rows = d.buyers.map(function(b){
    var cid = b.telegram_charge_id ? b.telegram_charge_id.slice(0,14) + '…' : '—';
    return '<tr><td><span class="mono">' + b.user_id + '</span></td>' +
      '<td>' + (b.username ? '@' + b.username : '—') + '</td>' +
      '<td>' + (b.full_name || '—') + '</td>' +
      '<td>' + cap(b.plan_id || '—') + '</td>' +
      '<td>' + methodBadge(b.payment_method) + '</td>' +
      '<td><span class="mono" style="font-size:11px">' + cid + '</span></td>' +
      '<td style="color:var(--muted)">' + fmtDate(b.created_at) + '</td></tr>';
  }).join('');

  document.getElementById('buyers-body').innerHTML =
    '<table><thead><tr><th>User ID</th><th>Username</th><th>Name</th>' +
    '<th>Package</th><th>Method</th><th>Charge ID</th><th>Date</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>';

  pager('buyers-pager', d.page, d.pages, 'buyersPrev', 'buyersNext');
}
function buyersNext() { buyersPage++; loadBuyers(); }
function buyersPrev() { buyersPage--; loadBuyers(); }

// ── Pending ────────────────────────────────────────────────────────────────────
async function loadPending() {
  setLoading('pending-body');
  var d = await fetch('/api/admin/pending').then(function(r){ return r.json(); });
  var cnt = (d.users || []).length;
  document.getElementById('pending-meta').textContent = cnt + ' awaiting approval';
  document.getElementById('topbar-meta').textContent = cnt + ' pending';
  var badge_el = document.getElementById('pending-badge');
  badge_el.textContent = cnt;
  badge_el.className = 'nav-badge' + (cnt > 0 ? '' : ' zero');

  if (!d.users || d.users.length === 0) {
    setEmpty('pending-body', '✨ All caught up — no pending payments!'); return;
  }

  var rows = d.users.map(function(u){
    return '<tr id="pr-' + u.user_id + '">' +
      '<td><span class="mono">' + u.user_id + '</span></td>' +
      '<td>' + (u.username ? '@' + u.username : '—') + '</td>' +
      '<td>' + (u.full_name || '—') + '</td>' +
      '<td>' + cap(u.selected_plan || '—') + '</td>' +
      '<td style="color:var(--muted)">' + fmtDate(u.join_date) + '</td>' +
      '<td>' +
        '<button class="btn btn-approve" onclick="doApprove(' + u.user_id + ')">✅ Approve</button> ' +
        '<button class="btn btn-cancel"  onclick="doCancel('  + u.user_id + ')">✗ Cancel</button>' +
      '</td></tr>';
  }).join('');

  document.getElementById('pending-body').innerHTML =
    '<table><thead><tr><th>ID</th><th>Username</th><th>Name</th>' +
    '<th>Plan</th><th>Joined</th><th>Actions</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

async function doApprove(uid) {
  var r = await post('/api/admin/approve', {user_id: uid});
  if (r.ok) {
    toast('User ' + uid + ' approved — send invite via /approve ' + uid + ' in bot');
    var row = document.getElementById('pr-' + uid);
    if (row) row.remove();
    var el = document.getElementById('pending-badge');
    el.textContent = Math.max(0, parseInt(el.textContent || '0') - 1);
  } else { toast('Failed: ' + (r.error || 'unknown'), 'err'); }
}

async function doCancel(uid) {
  var r = await post('/api/admin/cancel', {user_id: uid});
  if (r.ok) {
    toast('User ' + uid + ' cancelled');
    var row = document.getElementById('pr-' + uid);
    if (row) row.remove();
    var el = document.getElementById('pending-badge');
    el.textContent = Math.max(0, parseInt(el.textContent || '0') - 1);
  } else { toast('Failed: ' + (r.error || 'unknown'), 'err'); }
}

// ── Banned ─────────────────────────────────────────────────────────────────────
async function loadBanned() {
  setLoading('banned-body');
  var d = await fetch('/api/admin/banned').then(function(r){ return r.json(); });
  document.getElementById('topbar-meta').textContent = (d.users || []).length + ' banned';

  if (!d.users || d.users.length === 0) { setEmpty('banned-body', 'No banned users.'); return; }

  var rows = d.users.map(function(u){
    return '<tr id="br-' + u.user_id + '">' +
      '<td><span class="mono">' + u.user_id + '</span></td>' +
      '<td>' + (u.reason || '—') + '</td>' +
      '<td style="color:var(--muted)">' + fmtDate(u.banned_at) + '</td>' +
      '<td><button class="btn btn-unban" onclick="doUnban(' + u.user_id + ')">🔓 Unban</button></td>' +
    '</tr>';
  }).join('');

  document.getElementById('banned-body').innerHTML =
    '<table><thead><tr><th>User ID</th><th>Reason</th><th>Banned At</th><th>Action</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>';
}

async function doUnban(uid) {
  var r = await post('/api/admin/unban', {user_id: uid});
  if (r.ok) {
    toast('User ' + uid + ' unbanned');
    var row = document.getElementById('br-' + uid);
    if (row) row.remove();
  } else { toast('Failed: ' + (r.error || 'unknown'), 'err'); }
}

// ── Videos ─────────────────────────────────────────────────────────────────────
async function loadVideos() {
  setLoading('videos-body');
  var d = await fetch('/api/admin/videos').then(function(r){ return r.json(); });
  document.getElementById('topbar-meta').textContent = (d.videos || []).length + ' videos';

  if (!d.videos || d.videos.length === 0) {
    setEmpty('videos-body', 'No videos uploaded yet.'); return;
  }

  var rows = d.videos.map(function(v){
    return '<tr>' +
      '<td>' + v.slot + '</td>' +
      '<td>' + typeBadge(v.video_type) + '</td>' +
      '<td>' + (v.title || ('Preview #' + v.slot)) + '</td>' +
      '<td>⭐ ' + v.price + '</td>' +
      '<td>' + (v.duration ? v.duration + 's' : '—') + '</td>' +
      '<td style="color:var(--muted)">' + fmtDate(v.uploaded_at) + '</td></tr>';
  }).join('');

  document.getElementById('videos-body').innerHTML =
    '<table><thead><tr><th>Slot</th><th>Type</th><th>Title</th>' +
    '<th>Price</th><th>Duration</th><th>Uploaded</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>';
}

// ── Boot ───────────────────────────────────────────────────────────────────────
loadOverview();
</script>
</body>
</html>"""
