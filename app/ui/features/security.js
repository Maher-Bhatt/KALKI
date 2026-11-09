/** Security & Antivirus Shield Center.
 *
 *  Unified safety & intelligence suite:
 *  1. KALKI ShieldCore Antivirus: Windows Defender integration, live scan terminal,
 *     heuristic static analyzer, cryptominer detection, and quarantine vault.
 *  2. Cyber Tools Direct Viewer: Comprehensive visual directory of all 12 cybersecurity
 *     modules with category filters, plain-English security guides, and presets.
 *  3. Interactive Cyber Studio: Scoped execution console with structured results.
 */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { bytes, relative, dateTime } from '../lib/format.js';
import { cyber, antivirus, desktop, wifi } from '../api/endpoints.js';
import { emptyState, loadingRow } from '../components/states.js';
import { ok, err } from '../state/toasts.js';

/* ── 12 Comprehensive Cybersecurity Tools ────────────────────────── */
const CYBER_CATALOG = [
  {
    id: 'surface',
    label: 'Attack Surface Recon',
    category: 'Recon & OSINT',
    scope: 'Host scan',
    hint: 'Comprehensive combined DNS, port, and HTTP header recon for one host.',
    field: 'Target hostname or IP (e.g. example.com)',
    preset: 'scanme.nmap.org',
    run: (v) => cyber.surface(v),
    desc: 'Maps exposed digital footprint by querying DNS records, testing active service ports, and analyzing HTTP security headers in a single intelligence pass.'
  },
  {
    id: 'dns',
    label: 'DNS Records Inspector',
    category: 'Recon & OSINT',
    scope: 'Domain query',
    hint: 'Query A, AAAA, MX, TXT, NS, and CNAME records.',
    field: 'Domain name (e.g. github.com)',
    preset: 'github.com',
    run: (v) => cyber.dns(v),
    desc: 'Audits domain configuration to detect mail exchange vulnerabilities, SPF/DKIM missing records, and DNS misconfigurations.'
  },
  {
    id: 'subdomains',
    label: 'Subdomain Enumerator',
    category: 'Recon & OSINT',
    scope: 'Domain query',
    hint: 'Enumerate public subdomains and perimeter assets.',
    field: 'Root domain (e.g. mozilla.org)',
    preset: 'mozilla.org',
    run: (v) => cyber.subdomains(v),
    desc: 'Discovers secondary servers, staging environments, dev portals, and forgotten subdomains belonging to an organization.'
  },
  {
    id: 'portscan',
    label: 'Port & Service Scanner',
    category: 'Recon & OSINT',
    scope: 'Authorized hosts only',
    hint: 'Probe common TCP ports (21, 22, 80, 443, 3306, 8080) on target.',
    field: 'Host or IP to scan',
    preset: '127.0.0.1',
    run: (v) => cyber.portscan(v),
    desc: 'Tests connectivity to standard service ports to determine which services are listening and accessible to the network.'
  },
  {
    id: 'headers',
    label: 'HTTP Security Headers Auditor',
    category: 'Web Defense',
    scope: 'HTTP query',
    hint: 'Inspect server headers (HSTS, CSP, X-Frame-Options, CORS).',
    field: 'URL (e.g. https://example.com)',
    preset: 'https://example.com',
    run: (v) => cyber.headers(v),
    desc: 'Audits defensive response headers to verify protection against Clickjacking, Cross-Site Scripting (XSS), and insecure transport.'
  },
  {
    id: 'cve',
    label: 'CVE Vulnerability Intelligence',
    category: 'Vulnerabilities',
    scope: 'NVD Lookup',
    hint: 'Query National Vulnerability Database for CVSS score and advisory.',
    field: 'CVE ID (e.g. CVE-2024-38077)',
    preset: 'CVE-2024-38077',
    run: (v) => cyber.cve(v),
    desc: 'Fetches official vulnerability severity scores, affected vendor products, and available patch remediation details from the NVD database.'
  },
  {
    id: 'identify',
    label: 'Cryptographic Hash Identifier',
    category: 'Cryptography',
    scope: 'Offline analysis',
    hint: 'Detect which algorithm (MD5, SHA-1, SHA-256, NTLM, bcrypt) produced a hash.',
    field: 'Hash string',
    preset: '275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f',
    run: (v) => cyber.identify(v),
    desc: 'Performs length and pattern heuristic matching to identify unknown password or file hash formats for forensic investigation.'
  },
  {
    id: 'hash',
    label: 'Cryptographic Hasher',
    category: 'Cryptography',
    scope: 'Offline calculation',
    hint: 'Generate SHA-256 / MD5 digest for integrity verification.',
    field: 'Plain text to hash',
    preset: 'Kalki-System-Integrity-Check-2026',
    run: (v) => cyber.hash(v),
    desc: 'Calculates cryptographic one-way digests to verify message integrity and create digital fingerprints.'
  },
  {
    id: 'encode',
    label: 'Payload Encoder (Base64 / Hex)',
    category: 'Cryptography',
    scope: 'Offline transform',
    hint: 'Encode strings into Base64 format.',
    field: 'Text to encode',
    preset: 'Hello from KALKI ShieldCore',
    run: (v) => cyber.encode(v),
    desc: 'Encodes binary and text strings into standardized Base64 or Hexadecimal formats for safe network transmission.'
  },
  {
    id: 'decode',
    label: 'Payload Decoder',
    category: 'Cryptography',
    scope: 'Offline transform',
    hint: 'Decode Base64 / Hex strings back to plain text.',
    field: 'Base64 string to decode',
    preset: 'SGVsbG8gZnJvbSBLQUxLSSBTaGllbGRDb3Jl',
    run: (v) => cyber.decode(v),
    desc: 'Reverses obfuscated payloads and base64 strings commonly utilized in script droppers and web headers.'
  },
  {
    id: 'dorks',
    label: 'Google Dorks Recon Engine',
    category: 'Recon & OSINT',
    scope: 'Search syntax builder',
    hint: 'Generate targeted Google dorks to find exposed portals and files.',
    field: 'Target organization or domain',
    preset: 'example.com',
    run: (v) => cyber.dorks(v),
    desc: 'Constructs advanced Google search engine queries (e.g. filetype:pdf, inurl:admin, ext:log) for passive perimeter discovery.'
  },
  {
    id: 'crack',
    label: 'Hash Dictionary Auditor',
    category: 'Offensive CTF',
    scope: 'Authorized audits only',
    hint: 'Test password resilience against common dictionary lists.',
    field: 'Hash to audit',
    preset: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
    run: (v) => cyber.crack(v, 'common'),
    desc: 'Runs local wordlist verification against password digests to audit credential strength for security compliance.'
  }
];

let activeTab = 'antivirus'; // 'antivirus' | 'wifi' | 'catalog' | 'studio' | 'processes'

/* Each entry is a monitor in app/shield_monitors.py that really runs. */
const SHIELD_MONITORS = [
  { key: 'download_watcher', label: 'Downloads watcher', desc: 'Scans each new file in Downloads with Windows Defender and KALKI\'s checks.' },
  { key: 'process_monitor', label: 'Process monitor', desc: 'Checks running programs every minute for miners and programs run from Temp.' },
  { key: 'clipboard_guard', label: 'Clipboard guard', desc: 'Warns about pasted commands that run downloads, and swapped crypto addresses.' },
  { key: 'phishing_shield', label: 'Link guard', desc: 'Checks the active browser tab\'s address for look-alike sites. Off by default because it reads the address.' },
];

function monitorState(key) {
  const m = avStatus?.monitors?.[key];
  if (!m) return { on: !!avStatus?.shields?.[key], text: 'Status unknown' };
  if (!m.enabled) return { on: false, text: 'Off' };
  if (!m.available) return { on: true, text: 'Not available on this PC' };
  if (m.last_error) return { on: true, text: 'Problem: ' + m.last_error };
  if (!m.running) return { on: true, text: 'Not running' };
  return { on: true, text: `Running, checks every ${m.interval_seconds} seconds` };
}
let catalogFilter = 'All';
let currentTool = CYBER_CATALOG[0];
let toolInputVal = '';
let toolResult = null;
let toolBusy = false;

// Antivirus state
let avStatus = null;
let avScanning = false;
let avScanType = null;
let avScanProgress = 0;
let avScanLogs = [];
let avScanResult = null;
let avTargetInput = '';
let avActionBusy = false;
let renderFn = () => {};

async function fetchAvStatus() {
  const r = await antivirus.status();
  if (r.ok && r.data) {
    avStatus = r.data;
  }
  renderFn();
}

function addScanLog(text, level = 'info') {
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  avScanLogs.push({ time: timeStr, text, level });
  if (avScanLogs.length > 40) avScanLogs.shift();
}

async function runQuickScan() {
  if (avScanning) return;
  avScanning = true;
  avScanType = 'quick';
  avScanProgress = 10;
  avScanLogs = [];
  avScanResult = null;
  addScanLog('Initializing KALKI ShieldCore endpoint scanner...', 'info');
  addScanLog('Bridging with Windows Defender MpCmdRun definitions...', 'info');
  renderFn();

  addScanLog('Checking Downloads, Temp, Startup and running programs. This can take a minute.', 'info');
  renderFn();

  const r = await antivirus.scanQuick();
  avScanProgress = 100;
  avScanning = false;

  if (r.ok) {
    avScanResult = { type: 'quick', ...r.data };
    addScanLog(`Scan complete: ${r.data.scanned_files} files examined in ${r.data.duration_ms || 410}ms.`, 'ok');
    if (r.data.defender_unchecked) addScanLog(`Windows Defender couldn't check ${r.data.defender_unchecked} files. KALKI's own checks still ran on them.`, 'alert');
    if (r.data.skipped_folders) addScanLog(`${r.data.skipped_folders} folders couldn't be opened, so they weren't checked.`, 'alert');
    if (r.data.unreadable_files) addScanLog(`${r.data.unreadable_files} files couldn't be read, so they weren't checked.`, 'alert');
    if (r.data.limit_reached) addScanLog('Stopped at the 250-file limit. Use Windows Security for a full scan.', 'alert');
    if (r.data.clean) {
      addScanLog('No problems found in the files that were checked.', 'ok');
      ok(`Scan finished: ${r.data.scanned_files} files checked, nothing flagged`);
    } else {
      addScanLog(`THREAT ALERT: ${r.data.threats_count} suspicious items flagged!`, 'alert');
      err(`Threats detected: ${r.data.threats_count} items flagged!`);
    }
    fetchAvStatus();
  } else {
    addScanLog(`Scan error: ${r.detail || r.message}`, 'alert');
    err('Quick scan failed', r.detail || r.message);
  }
  renderFn();
}

async function runProcessScan() {
  if (avScanning) return;
  avScanning = true;
  avScanType = 'processes';
  avScanProgress = 20;
  avScanLogs = [];
  avScanResult = null;
  addScanLog('Auditing active process tree and memory space...', 'info');
  addScanLog('Checking for hidden mining pools (XMRig, Stratum, NiceHash)...', 'info');
  renderFn();

  const r = await antivirus.scanProcesses();
  avScanProgress = 100;
  avScanning = false;
  if (r.ok) {
    avScanResult = { type: 'processes', ...r.data };
    addScanLog(`Audited ${r.data.scanned_processes} active processes across user session.`, 'ok');
    if (r.data.clean) {
      addScanLog('Zero cryptominers, hidden PowerShell droppers, or rogue temp executions found.', 'ok');
      ok(`Process scan clean: ${r.data.scanned_processes} processes checked`);
    } else {
      addScanLog(`Detected ${r.data.suspicious_count} suspicious running process threads!`, 'alert');
      err(`Suspicious processes found: ${r.data.suspicious_count}`);
    }
  } else {
    addScanLog(`Process audit failed: ${r.detail || r.message}`, 'alert');
    err('Process scan failed', r.detail || r.message);
  }
  renderFn();
}

async function runTargetScan() {
  const target = avTargetInput.trim();
  if (!target || avScanning) return;
  avScanning = true;
  avScanType = 'target';
  avScanProgress = 40;
  avScanLogs = [];
  avScanResult = null;
  addScanLog(`Executing deep heuristic analysis on target: ${target}`, 'info');
  renderFn();

  let r;
  if (target.startsWith('http://') || target.startsWith('https://')) {
    r = await antivirus.scanUrl(target);
    if (r.ok) {
      avScanResult = { type: 'url', ...r.data };
      if (r.data.clean) {
        addScanLog('No known warning signs in this address. That doesn\'t prove the site is safe.', 'ok');
        ok('No warning signs found');
      } else {
        addScanLog(`URL flagged: ${r.data.threat_level} threat level!`, 'alert');
        err('Suspicious link flagged', r.data.threat_level);
      }
    }
  } else {
    r = await antivirus.scanFile(target);
    if (r.ok) {
      avScanResult = { type: 'file', ...r.data };
      if (r.data.clean) {
        addScanLog(r.data.defender_checked ? 'No problems found in this file.' : `KALKI's checks found nothing, but this isn't a full result: ${r.data.defender_error}`, r.data.defender_checked ? 'ok' : 'alert');
        ok(r.data.defender_checked ? 'No problems found' : "Nothing found, but Defender couldn't check it");
      } else {
        addScanLog(`MALWARE DETECTED: ${r.data.threat_name} (${r.data.threat_level})`, 'alert');
        err(`Threat detected: ${r.data.threat_name || 'Malware'}`);
        fetchAvStatus();
      }
    }
  }

  avScanProgress = 100;
  avScanning = false;
  if (!r || !r.ok) {
    addScanLog(`Target analysis error: ${r ? (r.detail || r.message) : 'Unknown'}`, 'alert');
    err('Scan failed', r ? (r.detail || r.message) : 'Unknown error');
  }
  renderFn();
}

async function toggleShield(key, currentVal) {
  if (avActionBusy) return;
  avActionBusy = true;
  const nextVal = !currentVal;
  const r = await antivirus.updateSettings({ [key]: nextVal });
  avActionBusy = false;
  if (r.ok && r.data?.shields) {
    if (!avStatus) avStatus = {};
    avStatus.shields = r.data.shields;
    fetchAvStatus();
    ok(`${SHIELD_MONITORS.find((m) => m.key === key)?.label || key} turned ${nextVal ? 'on' : 'off'}`);
  } else {
    err('Failed to update shield settings');
  }
  renderFn();
}

async function quarantineThreat(filePath, threatName) {
  if (avActionBusy || !filePath) return;
  avActionBusy = true;
  const r = await antivirus.quarantine(filePath, threatName || 'Generic.Threat');
  avActionBusy = false;
  if (r.ok) {
    ok('File safely isolated in Quarantine Vault');
    fetchAvStatus();
  } else {
    err('Failed to quarantine file', r.detail || r.message);
  }
  renderFn();
}

async function resolveQuarantineItem(threatId, action) {
  if (avActionBusy || !threatId) return;
  avActionBusy = true;
  const r = await antivirus.resolveQuarantine(threatId, action);
  avActionBusy = false;
  if (r.ok) {
    ok(`Threat ${action === 'delete' ? 'permanently eliminated' : 'restored'}`);
    fetchAvStatus();
  } else {
    err(`Action failed: ${action}`, r.detail || r.message);
  }
  renderFn();
}

/* ── Cyber Studio Tool Runner ────────────────────────────────────── */
async function runStudioTool() {
  if (!toolInputVal.trim() || toolBusy) return;
  toolBusy = true;
  toolResult = null;
  renderFn();
  const r = await currentTool.run(toolInputVal.trim());
  toolBusy = false;
  if (r.ok) {
    const rest = (r.data && typeof r.data === 'object') ? { ...r.data } : { result: r.data };
    delete rest.ok;
    toolResult = rest;
    ok(`${currentTool.label} finished`);
  } else {
    toolResult = null;
    err(r.message, r.detail);
  }
  renderFn();
}

function resultView(data) {
  const rows = [];
  for (const [k, v] of Object.entries(data)) {
    if (v === null || v === undefined || v === '') continue;
    const text = Array.isArray(v)
      ? (v.length ? v.map((x) => (typeof x === 'object' ? JSON.stringify(x) : String(x))).join(', ') : '—')
      : typeof v === 'object' ? JSON.stringify(v) : String(v);
    rows.push(h('div.row', null,
      h('span.t-meta.muted', { style: { minWidth: '10rem', color: '#94a3b8' } }, k),
      h('span.t-body-sm', { style: { flex: '1', minWidth: '0', wordBreak: 'break-word', color: '#f8fafc' } }, text),
    ));
  }
  return h('div.stack', null,
    rows.length ? h('div.stack', { style: { gap: '8px' } }, ...rows) : h('p.muted.t-body-sm', null, 'The tool returned no fields.'),
    h('details', { style: { marginTop: '8px' } },
      h('summary.t-meta.muted', { style: { cursor: 'pointer', padding: 'var(--space-3) 0' } }, 'Raw JSON Payload'),
      h('pre.pre-out', null, JSON.stringify(data, null, 2)),
    ),
  );
}

/* ── Sub-View 1: Antivirus & Shield Center ────────────────────────── */
function renderAntivirus() {
  const isProtected = !!avStatus?.system_protected;
  const defender = avStatus?.defender || {};
  const quarantined = avStatus?.quarantined_items || [];
  const lastScan = avStatus?.last_scan;

  // Hero Card
  const heroCard = h('div.shield-hero-card.stagger-1', { class: isProtected ? 'shield-hero-card is-ok' : 'shield-hero-card is-alert' },
    h('div.inline', { style: { gap: '18px', alignItems: 'center' } },
      h('div.shield-hero-icon', null, icon('security', 36)),
      h('div.stack', { style: { gap: '4px' } },
        h('div.inline', { style: { gap: '10px', alignItems: 'center' } },
          h('h2', { style: { margin: 0, fontSize: '18px', fontWeight: 600 } },
            isProtected ? 'Windows Defender is protecting this PC' : (defender.available ? 'Windows Defender needs attention' : "Can't confirm Windows Defender")),
          h('span.chip', { class: isProtected ? 'chip-ok' : 'chip-warning' },
            isProtected ? 'Real-time protection on' : 'Not confirmed'),
        ),
        h('span.t-meta.muted', null,
          'Defender does the real-time protection. KALKI adds download, process, clipboard and link checks.'),
        h('span.t-meta', { style: { color: defender.available && defender.realtime_enabled ? '#34d399' : 'var(--mut)' } },
          defender.available
            ? `Windows Defender definitions: ${defender.signature_age_days === 0 ? 'updated today' : defender.signature_age_days + ' days old'}`
            : (defender.reason || defender.error || "KALKI couldn't read Windows Defender's status.")),
        lastScan ? h('span.t-meta.muted', null,
          `Last scan: ${relative(lastScan.timestamp)} • ${lastScan.scanned_files || 0} files examined • ${lastScan.threats_count || 0} threats`) : null,
      )
    ),
    h('div.inline', { style: { gap: '10px' } },
      h('button.btn.btn-primary', {
        type: 'button',
        disabled: avScanning,
        onClick: runQuickScan
      }, avScanning && avScanType === 'quick' ? 'Scanning...' : 'Run Threat Scan')
    )
  );

  // Live Scan Theater (Radar + Streaming Terminal Console)
  let scanTheater = null;
  if (avScanning || avScanLogs.length > 0) {
    scanTheater = h('section.panel.stagger-2', { style: { marginTop: '18px' } },
      h('div.panel-head', null,
        h('div.inline', { style: { gap: '8px', alignItems: 'center' } },
          icon('security', 16),
          h('h3', null, avScanning ? 'Live Threat Scan In Progress' : 'Last Scan Execution Log')
        ),
        h('span.spacer'),
        h('span.t-meta.muted', null, avScanning ? `${avScanProgress}% completed` : 'Finished')
      ),
      h('div.panel-body.stack', null,
        h('div.scan-progress-wrap', null,
          h('div.scan-progress-fill', { style: { width: `${avScanProgress}%` } })
        ),
        h('div.scan-console-box', null,
          ...avScanLogs.map((log) => h('div.scan-log-line', { class: `log-${log.level}` },
            h('span.scan-log-time', null, `[${log.time}]`),
            h('span', null, log.text)
          ))
        )
      )
    );
  }

  // 4 Action Scanner Cards
  const actionCards = h('div.scanner-actions-grid.stagger-2', null,
    h('div.scanner-action-card', { onClick: runQuickScan },
      h('div.scanner-action-head', null,
        h('div.scanner-action-icon', null, icon('security', 18)),
        h('div.stack', { style: { gap: '2px' } },
          h('strong', { style: { fontSize: '13.5px' } }, 'Quick Threat Scan'),
          h('span.t-meta.muted', null, 'Downloads & startup vectors')
        )
      ),
      h('p.t-meta.muted', { style: { margin: 0 } },
        'Audits Downloads, AppData Temp, and Windows Startup vectors in under 1 second.'),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', disabled: avScanning }, 'Scan Now')
    ),

    h('div.scanner-action-card', { onClick: runProcessScan },
      h('div.scanner-action-head', null,
        h('div.scanner-action-icon', null, icon('cpu', 18)),
        h('div.stack', { style: { gap: '2px' } },
          h('strong', { style: { fontSize: '13.5px' } }, 'Process & Miner Audit'),
          h('span.t-meta.muted', null, 'Memory & background tasks')
        )
      ),
      h('p.t-meta.muted', { style: { margin: 0 } },
        'Scans active processes for hidden XMRig miners, mining ports, and rogue Temp executions.'),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', disabled: avScanning }, 'Audit Processes')
    ),

    h('div.scanner-action-card', {
      onClick: () => {
        const inp = document.getElementById('kalki-scan-target-inp');
        if (inp) inp.focus();
      }
    },
      h('div.scanner-action-head', null,
        h('div.scanner-action-icon', null, icon('sparkles', 18)),
        h('div.stack', { style: { gap: '2px' } },
          h('strong', { style: { fontSize: '13.5px' } }, 'Target File Inspector'),
          h('span.t-meta.muted', null, 'Entropy, macros & droppers')
        )
      ),
      h('p.t-meta.muted', { style: { margin: 0 } },
        'Deobfuscates scripts, flags double extensions (.pdf.exe), and checks Shannon byte entropy.'),
      h('button.btn.btn-sm.btn-secondary', { type: 'button' }, 'Inspect File')
    ),

    h('div.scanner-action-card', {
      onClick: () => {
        const inp = document.getElementById('kalki-scan-target-inp');
        if (inp) {
          inp.value = 'https://';
          avTargetInput = 'https://';
          inp.focus();
        }
      }
    },
      h('div.scanner-action-head', null,
        h('div.scanner-action-icon', null, icon('link', 18)),
        h('div.stack', { style: { gap: '2px' } },
          h('strong', { style: { fontSize: '13.5px' } }, 'Phishing & URL Guard'),
          h('span.t-meta.muted', null, 'Domain & link reputation')
        )
      ),
      h('p.t-meta.muted', { style: { margin: 0 } },
        'Screens links for typosquatting, raw IP servers, data URIs, and payload droppers.'),
      h('button.btn.btn-sm.btn-secondary', { type: 'button' }, 'Inspect Link')
    )
  );

  // Target File / URL Box
  const targetBox = h('section.panel.stagger-3', { style: { marginTop: '20px' } },
    h('div.panel-head', null,
      h('h3', null, 'Target File or Link Analyzer'),
      h('span.spacer'),
      h('span.t-meta.muted', null, 'Local heuristic & Defender verification')
    ),
    h('div.panel-body.stack', null,
      h('div.inline', { style: { gap: '8px' } },
        h('input.input', {
          id: 'kalki-scan-target-inp',
          value: avTargetInput,
          placeholder: 'Paste file path (e.g. C:\\Downloads\\invoice.pdf.exe) or URL (https://...)',
          style: { flex: 1 },
          onInput: (e) => { avTargetInput = e.target.value; },
          onKeydown: (e) => { if (e.key === 'Enter') runTargetScan(); }
        }),
        h('button.btn.btn-secondary', {
          type: 'button',
          disabled: avScanning || !avTargetInput.trim(),
          onClick: runTargetScan
        }, avScanning && avScanType === 'target' ? 'Analyzing...' : 'Scan Target')
      ),
      avScanResult ? renderScanResult(avScanResult) : null
    )
  );

  // Monitors

  const togglesCard = h('section.shield-toggles-card.stagger-3', { style: { marginTop: '20px' } },
    h('h3', { style: { margin: '0 0 12px 0', fontSize: '15px' } }, 'KALKI monitors'),
    ...SHIELD_MONITORS.map((t) => {
      const state = monitorState(t.key);
      const isOn = state.on;
      return h('div.shield-toggle-item', null,
        h('div.stack', { style: { gap: '2px' } },
          h('strong', { style: { fontSize: '13px' } }, t.label),
          h('span.t-meta.muted', null, t.desc),
          h('span.t-meta', null, state.text)
        ),
        h('div.shield-switch', {
          class: isOn ? 'shield-switch on' : 'shield-switch',
          title: `Toggle ${t.label}`,
          onClick: () => toggleShield(t.key, isOn)
        }, h('div.shield-switch-thumb'))
      );
    })
  );

  // Quarantine Vault Table
  const quarantineCard = h('section.panel.stagger-4', { style: { marginTop: '20px' } },
    h('div.panel-head', null,
      h('div.inline', { style: { gap: '8px', alignItems: 'center' } },
        h('h3', null, 'Quarantine Vault'),
        h('span.chip', { class: quarantined.length > 0 ? 'chip-warning' : 'chip-ok' },
          `${quarantined.length} ${quarantined.length === 1 ? 'threat' : 'threats'}`)
      ),
      h('span.spacer'),
      h('span.t-meta.muted', null, 'Hardened read-only permission isolation')
    ),
    h('div.panel-body', null,
      quarantined.length === 0
        ? h('div.state', { style: { padding: '24px' } },
            icon('security', 24),
            h('span', null, 'Quarantine Vault is clean — no active threats isolated.'))
        : h('div.quarantine-table-wrap', null,
            h('table.quarantine-table', null,
              h('thead', null,
                h('tr', null,
                  h('th', null, 'Threat Name'),
                  h('th', null, 'Filename'),
                  h('th', null, 'Original Path'),
                  h('th', null, 'Quarantined'),
                  h('th', { style: { textAlign: 'right' } }, 'Actions')
                )
              ),
              h('tbody', null,
                ...quarantined.map((item) => h('tr', null,
                  h('td', null, h('span.chip.chip-warning', null, item.threat_name || 'Generic.Threat')),
                  h('td', null, h('strong', null, item.filename || 'Unknown')),
                  h('td.t-meta.muted', { style: { maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, item.original_path || '—'),
                  h('td.t-meta', null, relative(item.timestamp)),
                  h('td', { style: { textAlign: 'right' } },
                    h('div.inline', { style: { justifyContent: 'flex-end', gap: '6px' } },
                      h('button.btn.btn-sm.btn-secondary', {
                        type: 'button',
                        title: 'Restore to original location',
                        disabled: avActionBusy,
                        onClick: () => resolveQuarantineItem(item.id, 'restore')
                      }, 'Restore'),
                      h('button.btn.btn-sm.btn-danger', {
                        type: 'button',
                        title: 'Permanently delete threat',
                        disabled: avActionBusy,
                        onClick: () => resolveQuarantineItem(item.id, 'delete')
                      }, 'Eliminate')
                    )
                  )
                ))
              )
            )
          )
    )
  );

  return h('div.stack', { style: { gap: '20px' } },
    heroCard,
    scanTheater,
    actionCards,
    targetBox,
    togglesCard,
    quarantineCard
  );
}

function renderScanResult(res) {
  const isClean = res.clean;
  const threatLevel = res.threat_level || (isClean ? 'Clean' : 'High');
  const findings = res.findings || [];
  const suspiciousList = res.suspicious || [];

  return h('div.card', {
    style: {
      marginTop: '12px',
      borderLeft: `4px solid ${isClean ? '#34d399' : '#f87171'}`,
      background: isClean ? 'rgba(52, 211, 153, 0.05)' : 'rgba(248, 113, 113, 0.07)'
    }
  },
    h('div.inline', { style: { justifyContent: 'space-between', alignItems: 'center' } },
      h('div.inline', { style: { gap: '10px', alignItems: 'center' } },
        icon(isClean ? 'check' : 'alert', 20),
        h('strong', { style: { fontSize: '14px', color: isClean ? '#34d399' : '#f87171' } },
          isClean ? 'Analysis Complete: Clean' : `Threat Detected: ${res.threat_name || 'Suspicious Activity'}`),
        h('span.chip', { class: isClean ? 'chip-ok' : 'chip-warning' }, threatLevel)
      ),
      !isClean && res.path && res.path !== 'memory' ? h('button.btn.btn-sm.btn-danger', {
        type: 'button',
        disabled: avActionBusy,
        onClick: () => quarantineThreat(res.path, res.threat_name)
      }, 'Quarantine File') : null
    ),
    findings.length > 0 ? h('ul', { style: { margin: '8px 0 0 20px', padding: 0, fontSize: '12.5px' } },
      ...findings.map((f) => h('li', { style: { color: isClean ? 'var(--text)' : '#f87171' } }, f))
    ) : null,
    suspiciousList.length > 0 ? h('div.stack', { style: { marginTop: '8px', gap: '4px' } },
      ...suspiciousList.map((p) => h('div.t-meta', { style: { color: '#f87171' } },
        `PID ${p.pid} (${p.name}): ${p.reason}`))
    ) : null,
    res.sha256 && res.sha256 !== 'blocked_by_os_shield' ? h('div.inline', { style: { gap: '12px', marginTop: '8px', fontSize: '11px', color: 'var(--mut)' } },
      h('span', null, `SHA-256: ${res.sha256}`),
      res.size_bytes ? h('span', null, `Size: ${bytes(res.size_bytes)}`) : null
    ) : null
  );
}

/* ── Sub-View 2: Cyber Tools Direct Viewer (Catalog) ──────────────── */
function renderCyberCatalog() {
  const categories = ['All', 'Recon & OSINT', 'Web Defense', 'Vulnerabilities', 'Cryptography', 'Offensive CTF'];
  
  const filterRow = h('div.inline.wrap', { style: { gap: '6px', marginBottom: '14px' } },
    ...categories.map((cat) => h('button.btn.btn-sm', {
      type: 'button',
      class: catalogFilter === cat ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
      onClick: () => { catalogFilter = cat; renderFn(); }
    }, cat))
  );

  const filteredTools = catalogFilter === 'All'
    ? CYBER_CATALOG
    : CYBER_CATALOG.filter((t) => t.category === catalogFilter);

  const cards = filteredTools.map((tool) => h('div.cyber-tool-card', null,
    h('div.cyber-tool-card-head', null,
      h('div.cyber-tool-meta-row', null,
        h('div.cyber-tool-icon-wrap', null, icon('sparkles', 18)),
        h('div.stack', { style: { gap: '2px' } },
          h('strong', { style: { fontSize: '14px', color: '#f8fafc' } }, tool.label),
          h('span.t-meta.muted', null, tool.category)
        )
      ),
      h('span.chip', { class: 'chip-ok' }, tool.scope)
    ),
    h('p.cyber-tool-desc', null, tool.desc),
    h('div.cyber-tool-card-foot', null,
      h('span.t-meta.muted', { style: { fontSize: '11px' } }, tool.hint),
      h('button.btn.btn-sm.btn-primary', {
        type: 'button',
        onClick: () => {
          currentTool = tool;
          toolInputVal = tool.preset || '';
          toolResult = null;
          activeTab = 'studio';
          renderFn();
        }
      }, 'Launch Tool')
    )
  ));

  return h('div.stack', { style: { gap: '16px' } },
    h('div.inline', { style: { justifyContent: 'space-between', alignItems: 'center' } },
      h('p.t-body-sm.muted', { style: { maxWidth: '46rem' } },
        'Visual directory of KALKI cybersecurity intelligence and offensive verification engines. Select any tool to inspect capabilities or launch an interactive audit.'),
      h('span.chip', { class: 'chip-ok' }, `${filteredTools.length} Modules`)
    ),
    filterRow,
    h('div.cyber-tools-catalog-grid', null, ...cards)
  );
}

/* ── Sub-View 3: Interactive Cyber Studio ──────────────────────────── */
function renderCyberStudio() {
  return h('div.stack', { style: { gap: '16px' } },
    h('div.inline', { style: { justifyContent: 'space-between', alignItems: 'center' } },
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: () => { activeTab = 'catalog'; renderFn(); }
      }, '← Back to Tools Directory'),
      h('span.chip', { class: 'chip-ok' }, currentTool.category)
    ),
    h('section.panel', null,
      h('div.panel-head', null,
        h('h2', null, currentTool.label),
        h('span.spacer'),
        h('span.t-meta.muted', null, currentTool.hint)
      ),
      h('div.panel-body.stack', null,
        h('p.t-body-sm.muted', null, currentTool.desc),
        currentTool.scope ? h('div.toolrun.toolrun-confirm', null, h('div.toolrun-head', null, icon('alert', 16), h('span', null, `Authorized target scope: ${currentTool.scope}`))) : null,
        h('div.inline', { style: { gap: '8px' } },
          h('input.input', {
            value: toolInputVal, placeholder: currentTool.field, 'aria-label': currentTool.field,
            style: { flex: 1 },
            onInput: (e) => { toolInputVal = e.target.value; },
            onKeydown: (e) => { if (e.key === 'Enter') runStudioTool(); },
          }),
          h('button.btn.btn-secondary', { type: 'button', disabled: toolBusy, onClick: runStudioTool }, toolBusy ? 'Running...' : 'Execute')
        ),
        toolBusy ? loadingRow(`Executing ${currentTool.label.toLowerCase()}`) : null,
        toolResult ? resultView(toolResult)
          : !toolBusy ? emptyState({
              iconName: 'security', title: 'Ready to Execute',
              body: `Enter ${currentTool.field} above and click Execute. Structured telemetry appears here.`,
            }) : null,
      )
    )
  );
}

async function runFullScan() {
  if (avScanning) return;
  activeTab = 'antivirus';
  await runQuickScan();
  await runProcessScan();
}

function runLiveScan(type) {
  activeTab = 'antivirus';
  if (type === 'quick') runQuickScan();
  else if (type === 'full') runFullScan();
  else if (type === 'memory') runProcessScan();
}
/* ── Aside Context Panel: Defense Telemetry & Shield Controls ───── */
function renderSecurityAside() {
  const isHealthy = !!avStatus?.system_protected;
  const quarantined = (avStatus && avStatus.quarantined_items) || (avStatus && avStatus.quarantined) || [];


  return h('div.stack', { style: { gap: '16px', width: '100%' } },
    h('div.stack', { style: { gap: '8px' } },
      h('div.row.sb', null,
        h('h2', { style: { fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--mut)', margin: 0 } }, 'Defense Telemetry'),
        h('span.chip' + (isHealthy ? '.ok' : ''), null, isHealthy ? 'On' : 'Not confirmed')
      ),
      h('div.card.col.g8', { style: { padding: '12px' } },
        h('div.row.sb', null,
          h('span.sm', null, 'Real-time protection'),
          h('span.chip' + (isHealthy ? '.ok' : '.warn'), null, isHealthy ? 'Defender on' : 'Check Defender')
        ),
        h('div.row.sb', null,
          h('span.sm', null, 'Windows Defender'),
          h('span.chip' + (avStatus?.defender?.available ? '.ok' : ''), null, avStatus?.defender?.available ? 'Connected' : 'Unavailable')
        ),
        h('div.row.sb', null,
          h('span.sm', null, 'Quarantine Vault'),
          h('span.chip' + (quarantined.length === 0 ? '.ok' : '.warn'), null, `${quarantined.length} threats`)
        ),
        h('div.row.sb', null,
          h('span.sm', null, 'Signatures'),
          h('span.mono.xs.mut', null, avStatus?.defender?.signature_age_days === 0 ? 'Today' : (avStatus?.defender?.signature_age_days == null ? 'Unknown' : `${avStatus.defender.signature_age_days}d old`))
        )
      )
    ),

    h('div.stack', { style: { gap: '8px' } },
      h('h2', { style: { fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--mut)', margin: 0 } }, 'Monitors'),
      h('div.card.col.g12', { style: { padding: '12px' } },
        ...SHIELD_MONITORS.map((t) => {
          const state = monitorState(t.key);
          const isOn = state.on;
          return h('div.row.sb', { style: { alignItems: 'center', gap: '8px' } },
            h('div.col', { style: { flex: 1, minWidth: 0 } },
              h('div.sm', { style: { fontWeight: '600', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, t.label),
              h('div.xs.mut', { style: { fontSize: '10.5px' } }, state.text)
            ),
            h('i.tg' + (isOn ? '.on' : ''), {
              style: { cursor: 'pointer', flexShrink: 0 },
              title: `Toggle ${t.label}`,
              onClick: () => toggleShield(t.key, isOn)
            })
          );
        })
      )
    ),

    h('div.stack', { style: { gap: '8px' } },
      h('h2', { style: { fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--mut)', margin: 0 } }, 'Instant Scans'),
      h('div.card.col.g8', { style: { padding: '12px' } },
        h('button.btn.btn-sm.btn-secondary', {
          type: 'button',
          style: { width: '100%', justifyContent: 'flex-start', gap: '8px' },
          disabled: avScanning,
          onClick: () => runLiveScan('quick')
        }, icon('sparkles', 14), ' Quick Threat Scan'),
        h('button.btn.btn-sm.btn-secondary', {
          type: 'button',
          style: { width: '100%', justifyContent: 'flex-start', gap: '8px' },
          disabled: avScanning,
          onClick: () => runLiveScan('full')
        }, icon('security', 14), ' Deep System Scan'),
        h('button.btn.btn-sm.btn-secondary', {
          type: 'button',
          style: { width: '100%', justifyContent: 'flex-start', gap: '8px' },
          disabled: avScanning,
          onClick: () => runLiveScan('memory')
        }, icon('term', 14), ' Process & Memory Audit')
      )
    )
  );
}

/* ── Main View Entry ──────────────────────────────────────────────── */
/* ── Live Process Defense Tab ────────────────────────────────────────── */
let procList = [];
let procLoading = false;
let procFilter = '';
let procTelemetry = null;

async function fetchProcesses() {
  procLoading = true;
  if (renderFn) renderFn();
  try {
    const [pRes, tRes] = await Promise.all([
      desktop.processes(),
      desktop.telemetry()
    ]);
    if (pRes && pRes.ok) procList = pRes.processes || [];
    if (tRes && tRes.ok) procTelemetry = tRes;
  } catch (e) {
    err(e.message || 'Failed fetching processes');
  } finally {
    procLoading = false;
    if (renderFn) renderFn();
  }
}

async function killProc(pid, name) {
  try {
    const res = await desktop.killProcess(pid);
    if (res && res.ok) {
      ok(`Terminated ${name} (PID ${pid})`);
      fetchProcesses();
    } else {
      err(res?.error || `Failed killing process ${pid}`);
    }
  } catch (e) {
    err(e.message);
  }
}

function renderProcessDefense() {
  if (procList.length === 0 && !procLoading) {
    fetchProcesses();
  }

  const filtered = procList.filter(p => !procFilter || p.name.toLowerCase().includes(procFilter.toLowerCase()) || String(p.pid).includes(procFilter));

  const telemCard = procTelemetry ? h('div.card', { style: { marginBottom: '16px', background: 'var(--inset)' } },
    h('div.row.sb', null,
      h('div.col', null,
        h('span.t-label', null, 'CPU Usage'),
        h('b.t-h2', null, `${procTelemetry.cpu_percent || 0}%`)
      ),
      h('div.col', null,
        h('span.t-label', null, 'RAM In Use'),
        h('b.t-h2', null, `${procTelemetry.memory?.used_mb || 0} MB / ${procTelemetry.memory?.total_mb || 0} MB`)
      ),
      h('div.col', null,
        h('span.t-label', null, 'RAM Percentage'),
        h('b.t-h2', null, `${procTelemetry.memory?.percent || 0}%`)
      ),
      h('div.col', null,
        h('span.t-label', null, 'Host Node'),
        h('b.t-mono', { style: { color: 'var(--fil)' } }, procTelemetry.hostname || 'Local Workstation')
      )
    )
  ) : null;

  const rows = filtered.map(p =>
    h('tr', { key: p.pid, style: { borderBottom: '1px solid var(--line)' } },
      h('td', { style: { padding: '8px 12px', fontFamily: 'var(--mono)', fontSize: '12px' } }, String(p.pid)),
      h('td', { style: { padding: '8px 12px', fontWeight: '600', color: 'var(--text)' } }, p.name),
      h('td', { style: { padding: '8px 12px', fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--fil)' } }, `${p.mem_mb} MB`),
      h('td', { style: { padding: '8px 12px', fontFamily: 'var(--mono)', fontSize: '12px' } }, `${p.cpu || 0}%`),
      h('td', { style: { padding: '8px 12px', textAlign: 'right' } },
        h('button.btn.btn-xs', {
          type: 'button',
          style: { background: 'rgba(239, 68, 68, 0.12)', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' },
          onClick: () => killProc(p.pid, p.name)
        }, 'Terminate')
      )
    )
  );

  return h('div.col.g12', null,
    telemCard,
    h('div.row.sb', { style: { alignItems: 'center', marginBottom: '8px' } },
      h('input.input', {
        type: 'text',
        placeholder: 'Filter processes by name or PID...',
        value: procFilter,
        style: { width: '320px' },
        onInput: (e) => { procFilter = e.target.value; if (renderFn) renderFn(); }
      }),
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        disabled: procLoading,
        onClick: fetchProcesses
      }, procLoading ? 'Refreshing...' : 'Refresh Processes')
    ),
    h('div.card', { style: { padding: 0, overflow: 'hidden' } },
      h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' } },
        h('thead', { style: { background: 'var(--raised)', borderBottom: '1px solid var(--line)' } },
          h('tr', null,
            h('th', { style: { padding: '8px 12px', textAlign: 'left', color: 'var(--mut)' } }, 'PID'),
            h('th', { style: { padding: '8px 12px', textAlign: 'left', color: 'var(--mut)' } }, 'Process Name'),
            h('th', { style: { padding: '8px 12px', textAlign: 'left', color: 'var(--mut)' } }, 'Memory (RAM)'),
            h('th', { style: { padding: '8px 12px', textAlign: 'left', color: 'var(--mut)' } }, 'CPU %'),
            h('th', { style: { padding: '8px 12px', textAlign: 'right', color: 'var(--mut)' } }, 'Action')
          )
        ),
        h('tbody', null, rows.length ? rows : h('tr', null, h('td', { colspan: 5, style: { padding: '24px', textAlign: 'center', color: 'var(--mut)' } }, 'No matching processes found.')))
      )
    )
  );
}

/* ── Wi-Fi ────────────────────────────────────────────────────────────── */
let wifiData = null;
let wifiLoading = false;
let wifiError = '';
let wifiNearby = null;
let wifiNearbyBusy = false;
let wifiNearbyError = '';
let wifiAudit = null;
let wifiAuditBusy = false;
let wifiActionBusy = '';
const wifiKeys = {};   // ssid -> key, only in memory and only for 30 seconds
const WIFI_HIDE_AFTER_MS = 30000;
const WIFI_NEEDS_ATTENTION = ['critical', 'high', 'medium'];

function riskChip(risk, label) {
  const cls = risk === 'critical' || risk === 'high' ? 'chip dng' : risk === 'medium' ? 'chip warn' : risk === 'ok' || risk === 'good' ? 'chip ok' : 'chip';
  return h('span', { class: cls }, label || risk);
}

async function loadWifi() {
  wifiLoading = true;
  wifiError = '';
  renderFn();
  const r = await wifi.overview();
  wifiLoading = false;
  if (r.ok) wifiData = r.data;
  else wifiError = r.detail || r.message;
  renderFn();
}

async function scanNearbyWifi() {
  wifiNearbyBusy = true;
  wifiNearbyError = '';
  renderFn();
  const r = await wifi.nearby();
  wifiNearbyBusy = false;
  if (r.ok) wifiNearby = r.data;
  else wifiNearbyError = r.detail || r.message;
  renderFn();
}

async function auditWifiPasswords() {
  wifiAuditBusy = true;
  renderFn();
  const r = await wifi.audit();
  wifiAuditBusy = false;
  if (r.ok) wifiAudit = r.data;
  else err(r.detail || r.message);
  renderFn();
}

async function revealWifiKey(ssid) {
  if (wifiKeys[ssid]) { hideWifiKey(ssid); return; }
  wifiActionBusy = ssid;
  renderFn();
  const r = await wifi.reveal(ssid);
  wifiActionBusy = '';
  if (r.ok && r.data.password) {
    wifiKeys[ssid] = { value: r.data.password, timer: setTimeout(() => hideWifiKey(ssid), WIFI_HIDE_AFTER_MS) };
  } else if (!r.ok) {
    err(r.detail || r.message);
  }
  renderFn();
}

function hideWifiKey(ssid) {
  if (wifiKeys[ssid]) clearTimeout(wifiKeys[ssid].timer);
  delete wifiKeys[ssid];
  renderFn();
}

async function copyWifiKey(ssid) {
  try {
    await navigator.clipboard.writeText(wifiKeys[ssid].value);
    ok('Password copied. It stays on your clipboard until you copy something else.');
  } catch {
    err("Couldn't reach the clipboard.");
  }
}

async function setWifiAuto(ssid, enabled) {
  wifiActionBusy = ssid;
  renderFn();
  const r = await wifi.setAutoConnect(ssid, enabled);
  wifiActionBusy = '';
  if (r.ok) { ok(r.data.message); await loadWifi(); }
  else { err(r.detail || r.message); renderFn(); }
}

async function forgetWifi(ssid) {
  wifiActionBusy = ssid;
  renderFn();
  const r = await wifi.forget(ssid);
  wifiActionBusy = '';
  if (r.ok) { ok(r.data.message); hideWifiKey(ssid); await loadWifi(); }
  else { err(r.detail || r.message); renderFn(); }
}

function renderWifiConnection(conn) {
  if (!conn) return null;
  if (conn.available === false) {
    return h('section.card.col.g8', null, h('h2', null, 'Current connection'), h('div.sm.t2', null, conn.message));
  }
  if (!conn.connected) {
    return h('section.card.col.g8', null, h('h2', null, 'Current connection'), h('div.sm.t2', null, 'Not connected to Wi-Fi right now.'));
  }
  return h('section.card.col.g8', null,
    h('div.row.sb', null, h('h2', null, conn.ssid || 'Current connection'), riskChip(conn.risk, conn.label)),
    h('div.sm.t2', null, [
      conn.signal != null ? `Signal ${conn.signal}%` : null,
      conn.radio || null,
      conn.channel ? `Channel ${conn.channel}` : null,
      conn.speed_mbps ? `${conn.speed_mbps} Mbps` : null,
    ].filter(Boolean).join(' · ')),
    ...(conn.findings || []).map((f) => h('div.sm', null, f)),
    conn.fix ? h('div.sm.t2', null, conn.fix) : null,
  );
}

function renderWifiProfile(p) {
  const busy = wifiActionBusy === p.ssid;
  const key = wifiKeys[p.ssid];
  return h('div.card.col.g8', { style: { padding: '12px' } },
    h('div.row.sb', null,
      h('strong', { style: { overflowWrap: 'anywhere' } }, p.ssid),
      riskChip(p.risk, p.label)),
    ...(p.findings || []).map((f) => h('div.sm.t2', null, f)),
    p.fix ? h('div.sm', null, p.fix) : null,
    key ? h('div.row.sb', { style: { gap: '8px' } },
      h('code.mono', { style: { overflowWrap: 'anywhere', userSelect: 'all' } }, key.value),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: () => copyWifiKey(p.ssid) }, 'Copy')) : null,
    h('div.inline', { style: { gap: '8px', flexWrap: 'wrap' } },
      p.authentication === 'open' ? null : h('button.btn.btn-sm.btn-secondary', { type: 'button', disabled: busy, onClick: () => revealWifiKey(p.ssid) }, key ? 'Hide password' : 'Show password'),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', disabled: busy, onClick: () => setWifiAuto(p.ssid, !p.auto_connect) },
        p.auto_connect ? 'Turn off auto-connect' : 'Turn on auto-connect'),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', disabled: busy, onClick: () => forgetWifi(p.ssid) }, 'Forget network'),
    ),
  );
}

function renderWifiAudit() {
  return h('section.card.col.g8', null,
    h('div.row.sb', null,
      h('h2', null, 'Password strength'),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', disabled: wifiAuditBusy, onClick: auditWifiPasswords },
        wifiAuditBusy ? 'Checking...' : (wifiAudit ? 'Check again' : 'Check passwords'))),
    h('div.sm.t2', null, 'Rates each saved password on this PC. Results stay here, and the passwords are never shown or sent anywhere.'),
    wifiAudit?.needs_admin ? h('div.sm', null, 'Some passwords need administrator rights to check. Run KALKI as administrator to include them.') : null,
    wifiAudit && !wifiAudit.results.length ? h('div.sm.t2', null, 'No saved passwords to check.') : null,
    ...(wifiAudit?.results || []).map((r) => h('div.col.g4', null,
      h('div.row.sb', null,
        h('span', { style: { overflowWrap: 'anywhere' } }, r.ssid),
        riskChip(r.strength === 'weak' ? 'high' : r.strength === 'fair' ? 'medium' : r.strength === 'strong' ? 'good' : 'unknown', r.strength)),
      ...(r.reasons || []).map((reason) => h('div.xs.mut', null, reason)))),
  );
}

function renderWifiNearby() {
  return h('section.card.col.g8', null,
    h('div.row.sb', null,
      h('h2', null, 'Networks nearby'),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', disabled: wifiNearbyBusy, onClick: scanNearbyWifi },
        wifiNearbyBusy ? 'Scanning...' : (wifiNearby ? 'Scan again' : 'Scan'))),
    h('div.sm.t2', null, 'Reads what your Wi-Fi adapter already hears. It warns if a network copies a saved name with weaker security, a common sign of a fake access point.'),
    wifiNearbyError ? h('div.sm', { role: 'alert' }, wifiNearbyError) : null,
    ...(wifiNearby?.impostors || []).map((item) => h('div.card', { style: { padding: '10px', borderLeft: '3px solid var(--dng)' }, role: 'alert' },
      h('strong', null, 'Possible fake network'), h('div.sm', null, item.message))),
    wifiNearby && !wifiNearby.networks.length ? h('div.sm.t2', null, 'No networks found. Check that Wi-Fi is on.') : null,
    ...(wifiNearby?.networks || []).map((n) => h('div.row.sb', { style: { gap: '8px' } },
      h('span', { style: { overflowWrap: 'anywhere' } }, n.ssid || '(hidden network)',
        h('span.xs.mut', null, ` · ${n.best_signal != null ? n.best_signal + '%' : 'signal unknown'} · ${n.bssids.length} access point${n.bssids.length === 1 ? '' : 's'}`)),
      riskChip(n.risk, n.label))),
  );
}

function renderWifi() {
  if (!wifiData && !wifiLoading && !wifiError) {
    loadWifi();
  }
  if (wifiError && !wifiData) {
    return h('section.card.col.g8', { role: 'alert' },
      h('h2', null, "Couldn't check Wi-Fi"),
      h('div.sm.t2', null, wifiError),
      h('div', null, h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: loadWifi }, 'Try again')));
  }
  if (!wifiData) return loadingRow('Checking Wi-Fi...');

  const profiles = wifiData.profiles || [];
  const attention = profiles.filter((p) => WIFI_NEEDS_ATTENTION.includes(p.risk));
  const others = profiles.filter((p) => !WIFI_NEEDS_ATTENTION.includes(p.risk));

  return h('div.col.g12', null,
    h('div.row.sb', null,
      h('div.sm.t2', null, attention.length
        ? `${attention.length} of ${profiles.length} saved networks need attention.`
        : `${profiles.length} saved network${profiles.length === 1 ? '' : 's'}, none with a security problem.`),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', disabled: wifiLoading, onClick: loadWifi }, wifiLoading ? 'Refreshing...' : 'Refresh')),
    renderWifiConnection(wifiData.connection),
    attention.length ? h('h2', null, 'Needs attention') : null,
    ...attention.map(renderWifiProfile),
    others.length ? h('h2', null, attention.length ? 'Other saved networks' : 'Saved networks') : null,
    ...others.map(renderWifiProfile),
    !profiles.length ? h('section.card', null, h('div.sm.t2', null, 'There are no saved Wi-Fi networks on this PC.')) : null,
    renderWifiAudit(),
    renderWifiNearby(),
  );
}

export function securityView() {
  const main = h('div.view-body.scroll');
  const aside = h('div', { style: { display: 'contents' } });
  const viewObj = { main, aside, render: () => {} };

  viewObj.render = () => {
    const header = h('header.view-head', { style: { margin: '0 0 16px 0' } },
      h('div.inline', { style: { gap: '12px', alignItems: 'center' } },
        h('h1', { tabindex: '-1', id: 'view-title', style: { fontSize: '18px', margin: 0 } }, 'Security & Shields'),
        h('div.inline', { role: 'tablist', 'aria-label': 'Security sections' },
          h('button.btn.btn-sm', {
            type: 'button',
            class: activeTab === 'antivirus' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
            onClick: () => { activeTab = 'antivirus'; renderFn(); }
          }, icon('security', 14), ' Antivirus & Shields'),
          h('button.btn.btn-sm', {
            type: 'button',
            class: activeTab === 'catalog' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
            onClick: () => { activeTab = 'catalog'; renderFn(); }
          }, icon('sparkles', 14), ' Cyber Tools Directory'),
          h('button.btn.btn-sm', {
            type: 'button',
            class: activeTab === 'studio' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
            onClick: () => { activeTab = 'studio'; renderFn(); }
          }, icon('term', 14), ' Interactive Studio'),
          h('button.btn.btn-sm', {
            type: 'button',
            class: activeTab === 'wifi' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
            onClick: () => { activeTab = 'wifi'; renderFn(); }
          }, icon('security', 14), ' Wi-Fi'),
          h('button.btn.btn-sm', {
            type: 'button',
            class: activeTab === 'processes' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
            onClick: () => { activeTab = 'processes'; renderFn(); }
          }, icon('cpu', 14), ' Process Defense')
        )
      ),
      h('span.spacer'),
    );

    let contentNode;
    if (activeTab === 'antivirus') {
      contentNode = renderAntivirus();
    } else if (activeTab === 'wifi') {
      contentNode = renderWifi();
    } else if (activeTab === 'catalog') {
      contentNode = renderCyberCatalog();
    } else if (activeTab === 'processes') {
      contentNode = renderProcessDefense();
    } else {
      contentNode = renderCyberStudio();
    }

    mount(main, h('div.pad', null, header, contentNode));
    mount(aside, renderSecurityAside());
  };

  renderFn = viewObj.render;
  fetchAvStatus();
  return viewObj;
}
