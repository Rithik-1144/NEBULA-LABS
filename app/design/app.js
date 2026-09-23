const form = document.querySelector('#command-form');
const input = document.querySelector('#command-input');
const body = document.querySelector('#result-body');
const title = document.querySelector('#result-title');
const status = document.querySelector('#result-status');
const workspaceBody = document.querySelector('#workspace-body');
const workspaceTitle = document.querySelector('#workspace-title');
const workspaceEyebrow = document.querySelector('#workspace-eyebrow');
const workspaceSearch = document.querySelector('#workspace-search');
const workspaceAction = document.querySelector('#workspace-action');
let snapshot = {products: [], low_stock: [], bills: [], customers: []};
let activeTab = 'inventory';
let activeChart = 'stock';

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'}[character]));
}

function formatValue(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return escapeHtml(value);
}

function showResult(payload) {
  const values = Object.entries(payload).filter(([key]) => !['summary', 'invoice_pdf'].includes(key));
  title.textContent = payload.action ? payload.action.replaceAll('_', ' ') : 'Completed';
  status.textContent = 'SUCCESS';
  status.className = 'status-badge success';
  body.innerHTML = `<div class="result-card-content"><strong>${escapeHtml(payload.summary || 'Operation completed.')}</strong><dl>${values.map(([key, value]) => `<div><dt>${escapeHtml(key.replaceAll('_', ' '))}</dt><dd>${formatValue(value)}</dd></div>`).join('')}</dl></div>`;
  const agentResult = document.querySelector('#agent-result');
  if (agentResult) {
    agentResult.innerHTML = `<span class="agent-result-label">LATEST AGENT RESULT</span><b>${escapeHtml(payload.summary || 'Operation completed.')}</b>`;
    agentResult.classList.add('has-result');
  }
  body.scrollIntoView({behavior: 'smooth', block: 'center'});
}

async function runCommand(command) {
  input.value = command;
  body.innerHTML = '<p class="loading">PROCESSING COMMAND...</p>';
  status.textContent = 'RUNNING';
  status.className = 'status-badge';
  try {
    const response = await fetch('/telegram/message', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: command})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'The command could not be completed.');
    showResult(payload);
  } catch (error) {
    title.textContent = 'Request failed';
    status.textContent = 'ERROR';
    status.className = 'status-badge error';
    body.innerHTML = `<div class="result-card-content"><strong>${escapeHtml(error.message)}</strong><p>Check that the API is running and try again.</p></div>`;
  }
}

async function loadSnapshot() {
  workspaceBody.innerHTML = '<p class="loading">LOADING LIVE DATA...</p>';
  try {
    const response = await fetch('/api/dashboard/snapshot');
    if (!response.ok) throw new Error('Unable to load live workspace data.');
    snapshot = await response.json();
    renderWorkspace();
    renderCharts();
  } catch (error) {
    workspaceBody.innerHTML = `<div class="workspace-error"><b>${escapeHtml(error.message)}</b><small>Refresh the page after checking the API connection.</small></div>`;
  }
}

function renderCharts() {
  const primary = document.querySelector('#primary-chart');
  const title = document.querySelector('#chart-title');
  const signalTitle = document.querySelector('#signal-title');
  const signalValue = document.querySelector('#signal-value');
  const signalCopy = document.querySelector('#signal-copy');
  if (!primary) return;

  if (activeChart === 'stock') {
    const counts = ['healthy', 'low', 'critical'].map((state) => ({label: state, value: snapshot.products.filter((item) => item.stock_state === state).length}));
    const max = Math.max(...counts.map((item) => item.value), 1);
    title.textContent = 'Stock health';
    primary.innerHTML = `<div class="bar-chart" aria-label="Stock health distribution">${counts.map((item) => `<div class="bar-column" data-label="${item.label}"><div class="bar ${item.label === 'low' ? 'warning' : item.label === 'critical' ? 'danger' : ''}" style="--bar-height:${Math.max(8, item.value / max * 100)}%" title="${item.value} products" aria-label="${item.value} ${item.label} products"><span class="bar-value">${item.value}</span></div></div>`).join('')}</div><div class="chart-legend"><span class="legend-item"><i class="legend-dot teal"></i>Healthy ${counts[0].value}</span><span class="legend-item"><i class="legend-dot amber"></i>Low ${counts[1].value}</span><span class="legend-item"><i class="legend-dot coral"></i>Critical ${counts[2].value}</span></div>`;
    const pressure = snapshot.products.length ? Math.round((snapshot.low_stock.length / snapshot.products.length) * 100) : 0;
    signalTitle.textContent = 'Reorder pressure';
    signalValue.textContent = `${pressure}%`;
    signalCopy.textContent = `${snapshot.low_stock.length} of ${snapshot.products.length} products need attention.`;
    renderSignalBars(counts.map((item) => item.value));
  } else if (activeChart === 'payments') {
    const grouped = snapshot.bills.reduce((result, bill) => { const method = bill.payment_method || 'unknown'; result[method] = (result[method] || 0) + Number(bill.grand_total || 0); return result; }, {});
    const entries = Object.entries(grouped).sort((a, b) => b[1] - a[1]);
    const total = entries.reduce((sum, [, value]) => sum + value, 0);
    const palette = ['var(--teal)', 'var(--coral)', 'var(--amber)', '#6b8791'];
    let cursor = 0;
    const stops = entries.map(([method, value], index) => { const start = total ? cursor / total * 360 : 0; cursor += value; const end = total ? cursor / total * 360 : 0; return `${palette[index % palette.length]} ${start}deg ${end}deg`; });
    title.textContent = 'Bill mix by payment';
    primary.innerHTML = entries.length ? `<div class="donut-layout"><div class="donut" style="background:conic-gradient(${stops.join(',')})"><div class="donut-center"><strong>Rs ${total.toFixed(0)}</strong><small>gross bill value</small></div></div><div class="donut-legend">${entries.map(([method, value], index) => `<div><i class="legend-dot" style="background:${palette[index % palette.length]}"></i><span>${escapeHtml(method)}</span><b>${((value / Math.max(total, 1)) * 100).toFixed(0)}%</b></div>`).join('')}</div></div>` : '<div class="empty-chart">No bill data available yet.</div>';
    signalTitle.textContent = 'Bill activity';
    signalValue.textContent = `${snapshot.bills.length}`;
    signalCopy.textContent = 'Recent bills currently available in the operational store.';
    renderSignalBars(snapshot.bills.slice(0, 12).map((bill) => Number(bill.grand_total || 0)));
  } else {
    const customers = snapshot.customers.filter((customer) => customer.balance > 0).sort((a, b) => b.balance - a.balance).slice(0, 5);
    const total = snapshot.customers.reduce((sum, customer) => sum + Math.max(0, customer.balance), 0);
    title.textContent = 'Customers with outstanding credit';
    primary.innerHTML = customers.length ? `<div class="credit-list">${customers.map((customer) => `<div class="credit-row"><span><b>${escapeHtml(customer.name)}</b><small>${escapeHtml(customer.phone || 'No phone recorded')}</small></span><strong class="credit-amount">Rs ${customer.balance.toFixed(2)}</strong></div>`).join('')}</div>` : '<div class="empty-chart">No outstanding customer credit.</div>';
    signalTitle.textContent = 'Total exposure';
    signalValue.textContent = `Rs ${total.toFixed(0)}`;
    signalCopy.textContent = `${customers.length} customer${customers.length === 1 ? '' : 's'} with a positive due balance.`;
    renderSignalBars(customers.map((customer) => customer.balance));
  }
}

function renderSignalBars(values) {
  const target = document.querySelector('#signal-chart');
  if (!target) return;
  const max = Math.max(...values, 1);
  target.innerHTML = values.length ? values.map((value, index) => `<span class="signal-bar" style="--bar-height:${Math.max(5, value / max * 100)}%;--bar-delay:${index * 35}ms" title="${value}"><b>${Number(value).toFixed(value % 1 ? 1 : 0)}</b></span>`).join('') : '<span class="chart-loading">NO DATA</span>';
}

async function loadTelegramStatus() {
  const copy = document.querySelector('#telegram-status-copy');
  const value = document.querySelector('#telegram-status-value');
  try {
    const response = await fetch('/api/dashboard/telegram-status');
    const payload = await response.json();
    copy.textContent = payload.message;
    value.textContent = payload.running ? 'ONLINE' : 'SETUP NEEDED';
  } catch (error) {
    copy.textContent = 'Unable to reach the Telegram bridge status endpoint.';
    value.textContent = 'ERROR';
  }
}

function renderWorkspace() {
  const query = workspaceSearch.value.trim().toLowerCase();
  if (activeTab === 'agent') {
    workspaceEyebrow.textContent = 'LIVE AGENT';
    workspaceTitle.textContent = 'Natural language operations';
    workspaceSearch.placeholder = 'Ask about stock, bills, or khata...';
    workspaceAction.textContent = 'Run request';
    workspaceBody.innerHTML = `<div class="agent-workspace"><div class="agent-status"><span class="agent-orb">✦</span><div><b>Nebula operations agent</b><small>Connected to inventory, billing, khata, and invoice services.</small></div><span class="live-pill">ONLINE</span></div><div class="agent-suggestions"><button data-agent-command="How much Maggi left?">Check product stock</button><button data-agent-command="Create a draft bill">Create a bill</button><button data-agent-command="Khata balance Anita">Check customer khata</button><button data-agent-command="Receive 5 packets of Maggi at cost 14">Receive stock</button></div><div id="agent-result" class="agent-result"><span class="agent-result-label">AGENT READY</span><b>Choose an operation or type a request above.</b></div><p class="agent-hint">Every request is sent to the live store services.</p></div>`;
  } else if (activeTab === 'inventory') {
    workspaceEyebrow.textContent = 'LIVE INVENTORY';
    workspaceTitle.textContent = `${snapshot.products.length} products in catalogue`;
    workspaceSearch.placeholder = 'Search products or SKU...';
    workspaceAction.textContent = 'Receive stock';
    const products = snapshot.products.filter((item) => `${item.name} ${item.sku} ${item.brand}`.toLowerCase().includes(query));
    workspaceBody.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Product</th><th>SKU</th><th>Price</th><th>Stock</th><th>State</th><th></th></tr></thead><tbody>${products.map((item) => `<tr><td><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.brand)} · ${escapeHtml(item.category)}</small></td><td class="mono">${escapeHtml(item.sku)}</td><td class="mono">Rs ${item.selling_price.toFixed(2)}</td><td class="mono">${item.current_stock} ${escapeHtml(item.unit)}</td><td><span class="stock-chip ${item.stock_state}">${item.stock_state}</span></td><td><button class="row-action" data-command="How much ${escapeHtml(item.name)} left?">Ask agent</button></td></tr>`).join('')}</tbody></table></div>`;
  } else if (activeTab === 'billing') {
    workspaceEyebrow.textContent = 'BILLING WORKSPACE';
    workspaceTitle.textContent = `${snapshot.bills.length} recent bills`;
    workspaceSearch.placeholder = 'Search bill number...';
    workspaceAction.textContent = 'Create draft bill';
    const bills = snapshot.bills.filter((item) => item.bill_number.toLowerCase().includes(query));
    workspaceBody.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Bill</th><th>Status</th><th>Payment</th><th>Total</th><th></th></tr></thead><tbody>${bills.map((item) => `<tr><td><b>${escapeHtml(item.bill_number)}</b><small>Bill ID ${item.id}</small></td><td><span class="status-chip ${item.status.toLowerCase()}">${item.status}</span></td><td>${escapeHtml(item.payment_method)}</td><td class="mono">Rs ${item.grand_total.toFixed(2)}</td><td><button class="row-action" data-bill="${item.id}">View</button></td></tr>`).join('')}</tbody></table></div>`;
  } else {
    workspaceEyebrow.textContent = 'CUSTOMER KHATA';
    workspaceTitle.textContent = `${snapshot.customers.length} customers`;
    workspaceSearch.placeholder = 'Search customer...';
    workspaceAction.textContent = 'Add customer';
    const customers = snapshot.customers.filter((item) => `${item.name} ${item.phone || ''}`.toLowerCase().includes(query));
    workspaceBody.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Customer</th><th>Phone</th><th>Balance</th><th></th></tr></thead><tbody>${customers.map((item) => `<tr><td><b>${escapeHtml(item.name)}</b><small>Customer ID ${item.id}</small></td><td class="mono">${escapeHtml(item.phone || '—')}</td><td class="mono ${item.balance > 0 ? 'due' : 'credit'}">Rs ${item.balance.toFixed(2)}</td><td><button class="row-action" data-command="Khata balance ${escapeHtml(item.name)}">View khata</button></td></tr>`).join('')}</tbody></table></div>`;
  }
}

document.querySelectorAll('.workspace-tab').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.workspace-tab').forEach((item) => item.classList.remove('active'));
  tab.classList.add('active');
  activeTab = tab.dataset.tab;
  workspaceSearch.value = '';
  renderWorkspace();
}));
document.querySelectorAll('.chart-switch').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('.chart-switch').forEach((item) => item.classList.remove('active'));
  button.classList.add('active');
  activeChart = button.dataset.chart;
  renderCharts();
}));
workspaceSearch.addEventListener('input', renderWorkspace);
workspaceBody.addEventListener('click', (event) => {
  const commandButton = event.target.closest('[data-command]');
  const agentButton = event.target.closest('[data-agent-command]');
  const billButton = event.target.closest('[data-bill]');
  if (commandButton) runCommand(commandButton.dataset.command);
  if (agentButton) runCommand(agentButton.dataset.agentCommand);
  if (billButton) viewBill(billButton.dataset.bill);
});

async function viewBill(billId) {
  workspaceBody.innerHTML = '<p class="loading">LOADING BILL DETAIL...</p>';
  try {
    const response = await fetch(`/api/dashboard/bills/${billId}`);
    const bill = await response.json();
    if (!response.ok) throw new Error(bill.detail || 'Bill detail could not be loaded.');
    workspaceBody.innerHTML = `<div class="bill-detail"><div class="bill-detail-head"><div><p class="eyebrow">${escapeHtml(bill.bill_number)}</p><h3>${escapeHtml(bill.status)} · ${escapeHtml(bill.payment_method)}</h3></div><a class="toolbar-button invoice-link" href="/api/dashboard/bills/${bill.id}/invoice" target="_blank">Open invoice</a></div><div class="bill-items">${bill.items.length ? bill.items.map((item) => `<div class="bill-item"><span><b>${escapeHtml(item.product_name)}</b><small>${item.quantity} × Rs ${item.unit_price.toFixed(2)}</small></span><strong class="mono">Rs ${item.total.toFixed(2)}</strong></div>`).join('') : '<p class="empty-copy">This draft has no items yet.</p>'}</div><div class="bill-total"><span>Grand total</span><strong class="mono">Rs ${bill.grand_total.toFixed(2)}</strong></div></div>`;
  } catch (error) {
    workspaceBody.innerHTML = `<div class="workspace-error"><b>${escapeHtml(error.message)}</b></div>`;
  }
}
workspaceAction.addEventListener('click', () => {
  if (activeTab === 'agent') return runCommand(workspaceSearch.value.trim() || 'How much Maggi left?');
  runCommand(activeTab === 'inventory' ? 'Receive 10 packets of Maggi at cost 14' : activeTab === 'billing' ? 'Create a draft bill' : 'Create customer New Customer');
});
loadSnapshot();
loadTelegramStatus();

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (input.value.trim()) runCommand(input.value.trim());
});
document.querySelectorAll('[data-command]').forEach((button) => {
  button.addEventListener('click', () => runCommand(button.dataset.command));
});
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

const themeToggle = document.querySelector('#theme-toggle');
const savedTheme = localStorage.getItem('nebula-theme');
if (savedTheme === 'dark') document.documentElement.dataset.theme = 'dark';
function syncThemeToggle() {
  const dark = document.documentElement.dataset.theme === 'dark';
  themeToggle.setAttribute('aria-pressed', String(dark));
  themeToggle.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
  themeToggle.textContent = dark ? '☼' : '◐';
}
syncThemeToggle();
themeToggle.addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme === 'dark';
  document.documentElement.dataset.theme = dark ? 'light' : 'dark';
  localStorage.setItem('nebula-theme', dark ? 'light' : 'dark');
  syncThemeToggle();
});
