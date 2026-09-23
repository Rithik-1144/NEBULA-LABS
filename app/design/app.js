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
const customerDialog = document.querySelector('#customer-dialog');
const customerForm = document.querySelector('#customer-form');
const customerName = document.querySelector('#customer-name');
const customerFormStatus = document.querySelector('#customer-form-status');

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

let chatUser = 'web-operator';
let chatSessionId = null;

async function runCommand(command) {
  input.value = command;
  body.innerHTML = '<p class="loading">PROCESSING COMMAND...</p>';
  status.textContent = 'RUNNING';
  status.className = 'status-badge';
  try {
    const response = await fetch('/telegram/message', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: command, user_id: chatUser || 'web-operator'})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'The command could not be completed.');
    const assistantLine = payload.assistant_reply ? `<p class="agent-chat-bubble"><strong>Assistant:</strong> ${escapeHtml(payload.assistant_reply)}</p>` : '';
    const memoryLine = payload.session_context && Object.keys(payload.session_context).length ? `<p class="agent-chat-bubble subtle"><strong>Memory:</strong> ${escapeHtml(JSON.stringify(payload.session_context))}</p>` : '';
    showResult({ ...payload, summary: payload.summary + (payload.assistant_reply ? ` ${payload.assistant_reply}` : '') });
    const panel = document.getElementById('result-body');
    if (panel) {
      panel.innerHTML = `<div class="result-card-content"><strong>${escapeHtml(payload.summary || 'Operation completed.')}</strong>${assistantLine}${memoryLine}<dl>${Object.entries(payload).filter(([key]) => !['summary', 'invoice_pdf', 'assistant_reply'].includes(key)).map(([key, value]) => `<div><dt>${escapeHtml(key.replaceAll('_', ' '))}</dt><dd>${formatValue(value)}</dd></div>`).join('')}</dl></div>`;
    }
    await loadChatSessions(chatUser);
  } catch (error) {
    title.textContent = 'Request failed';
    status.textContent = 'ERROR';
    status.className = 'status-badge error';
    body.innerHTML = `<div class="result-card-content"><strong>${escapeHtml(error.message)}</strong><p>Check that the API is running and try again.</p></div>`;
  }
}

async function loadChatSessions(userId = chatUser) {
  const panel = document.getElementById('chat-session-list');
  if (!panel) return;
  try {
    const response = await fetch(`/api/dashboard/chat/sessions?user_id=${encodeURIComponent(userId || 'web-operator')}`);
    const payload = await response.json();
    const sessions = payload.sessions || [];
    if (!sessions.length) {
      panel.innerHTML = '<div class="chat-empty">No saved sessions yet</div>';
      chatSessionId = null;
      return;
    }
    if (!chatSessionId || !sessions.some((session) => session.id === chatSessionId)) {
      chatSessionId = sessions[0].id;
    }
    panel.innerHTML = sessions.map((session) => `<button class="chat-session ${session.id === chatSessionId ? 'active' : ''}" data-session-id="${session.id}"><span>${escapeHtml(session.last_message || 'New conversation')}</span><small>Updated ${new Date(session.updated_at || Date.now()).toLocaleString()}</small></button>`).join('');
    await loadChatHistory(userId, chatSessionId);
  } catch (error) {
    panel.innerHTML = `<div class="chat-empty">Unable to load chat history</div>`;
  }
}

async function loadChatHistory(userId = chatUser, sessionId = chatSessionId) {
  const container = document.getElementById('chat-history');
  if (!container) return;
  try {
    const response = await fetch(`/api/dashboard/chat/history?user_id=${encodeURIComponent(userId || 'web-operator')}&session_id=${sessionId || ''}`);
    const payload = await response.json();
    const messages = payload.messages || [];
    if (!messages.length) {
      container.innerHTML = '<div class="chat-empty">Start the first conversation for this user.</div>';
      return;
    }
    container.innerHTML = messages.map((message) => `<div class="chat-message ${message.role === 'user' ? 'user' : 'assistant'}"><span class="label">${message.role === 'user' ? 'You' : 'Nebula'}</span><p>${escapeHtml(message.content)}</p></div>`).join('');
    container.scrollTop = container.scrollHeight;
  } catch (error) {
    container.innerHTML = '<div class="chat-empty">Unable to load the selected conversation.</div>';
  }
}

async function sendChatMessage() {
  const inputEl = document.getElementById('chat-input');
  if (!inputEl) return;
  const text = inputEl.value.trim();
  if (!text) return;
  try {
    const response = await fetch('/api/dashboard/chat/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({user_id: chatUser || 'web-operator', message: text, session_id: chatSessionId})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Unable to post the message.');
    inputEl.value = '';
    chatSessionId = payload.response.conversation_id || chatSessionId;
    await loadChatSessions(chatUser);
    await loadChatHistory(chatUser, chatSessionId);
  } catch (error) {
    console.error(error);
  }
}

function openCustomerDialog() {
  if (!customerDialog) return;
  customerDialog.hidden = false;
  customerForm?.reset();
  customerFormStatus.textContent = '';
  customerName?.focus();
}

function closeCustomerDialog() {
  if (customerDialog) customerDialog.hidden = true;
}

async function saveCustomer(event) {
  event.preventDefault();
  const formData = new FormData(customerForm);
  const name = String(formData.get('name') || '').trim();
  const phone = String(formData.get('phone') || '').trim();
  if (!name) return;
  customerFormStatus.textContent = 'Saving customer...';
  try {
    const response = await fetch('/api/dashboard/customers', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, phone: phone || null})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Customer could not be saved.');
    closeCustomerDialog();
    activeTab = 'khata';
    document.querySelectorAll('.workspace-tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === 'khata'));
    await loadSnapshot();
    renderWorkspace();
    showResult({action: 'customer_created', summary: `${payload.name} was added to customer khata.`, ...payload});
  } catch (error) {
    customerFormStatus.textContent = error.message;
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
    workspaceBody.innerHTML = `
      <div class="agent-workspace">
        <div class="agent-status"><span class="agent-orb">✦</span><div><b>Nebula operations agent</b><small>Ask about stock, bills, invoices, or customer khata in plain language.</small></div><span class="live-pill">ONLINE</span></div>
        <div class="agent-suggestions"><span class="agent-suggestions-label">Try an action</span><button data-agent-command="How much Maggi left?">Check stock</button><button data-agent-command="Create a draft bill">Start a bill</button><button data-agent-command="Khata balance Anita">Review khata</button><button data-agent-command="Receive 5 packets of Maggi at cost 14">Receive stock</button></div>
        <div class="assistant-chat-shell">
          <aside class="chat-sidebar"><div class="chat-sidebar-heading"><b>Conversations</b><small>Saved by operator</small></div>
            <div class="chat-user-bar">
              <input id="chat-user-input" value="${escapeHtml(chatUser || 'web-operator')}" aria-label="User id" />
              <button id="chat-user-load" type="button">Open</button>
            </div>
            <div id="chat-session-list" class="chat-session-list"></div>
          </aside>
          <div class="chat-main">
            <div id="chat-history" class="chat-history"></div>
            <div class="chat-composer">
              <textarea id="chat-input" placeholder="Ask Nebula anything about today’s store operations..."></textarea>
              <button id="chat-send" class="chat-send" type="button">Send message ↗</button>
            </div>
          </div>
        </div>
        <div id="agent-result" class="agent-result"><span class="agent-result-label">AGENT READY</span><b>Choose an operation or type a request above.</b></div>
        <p class="agent-hint">Every request is sent to the live store services and saved to the user session history.</p>
      </div>
    `;
    loadChatSessions(chatUser);
    const userInput = document.getElementById('chat-user-input');
    const userButton = document.getElementById('chat-user-load');
    const sendButton = document.getElementById('chat-send');
    if (userButton) userButton.addEventListener('click', () => { chatUser = (userInput ? userInput.value : chatUser).trim() || 'web-operator'; loadChatSessions(chatUser); });
    if (sendButton) sendButton.addEventListener('click', sendChatMessage);
    document.getElementById('chat-session-list')?.addEventListener('click', async (event) => {
      const sessionButton = event.target.closest('[data-session-id]');
      if (!sessionButton) return;
      chatSessionId = Number(sessionButton.dataset.sessionId);
      await loadChatHistory(chatUser, chatSessionId);
      document.querySelectorAll('.chat-session').forEach((button) => button.classList.toggle('active', Number(button.dataset.sessionId) === chatSessionId));
    });
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
  if (activeTab === 'khata') return openCustomerDialog();
  runCommand(activeTab === 'inventory' ? 'Receive 10 packets of Maggi at cost 14' : 'Create a draft bill');
});
loadSnapshot();
loadTelegramStatus();

document.querySelectorAll('[data-open-customer]').forEach((button) => button.addEventListener('click', openCustomerDialog));
document.querySelectorAll('[data-close-customer]').forEach((button) => button.addEventListener('click', closeCustomerDialog));
customerForm?.addEventListener('submit', saveCustomer);

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
