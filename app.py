"""
AgentRank MVP — Web Application
Flask server that connects the audit engine to a web interface.

To run locally:
    pip install flask
    python app.py

Then visit: http://localhost:5000

To deploy (options):
    1. Railway.app — free tier, push to GitHub, auto-deploys
    2. Render.com — free tier, connects to GitHub
    3. Replit — quick prototyping
    4. Any VPS with Python
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
from audit_engine import AgentRankAuditor
import json
import os
import traceback

app = Flask(__name__, static_folder='static')

# Store audit results in memory (use Redis/DB in production)
audit_cache = {}

# The complete HTML for the landing page + results
LANDING_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentRank — Is Your Store Visible to AI Shopping Agents?</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --primary: #6C3AED; --primary-dark: #5B21B6; --primary-light: #8B5CF6;
    --accent: #F59E0B; --danger: #EF4444; --success: #10B981; --warning: #F59E0B;
    --bg: #0F0F1A; --bg-card: #1A1A2E; --text: #F8FAFC; --text-muted: #94A3B8; --border: #2D2D4A;
  }
  body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

  .hero {
    min-height: 100vh; display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center; padding: 2rem;
    background: radial-gradient(ellipse at top, #1a1040 0%, var(--bg) 70%);
  }
  .badge {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: rgba(108,58,237,0.15); border: 1px solid rgba(108,58,237,0.3);
    border-radius: 999px; padding: 0.4rem 1rem; font-size: 0.8rem;
    font-weight: 500; color: var(--primary-light); margin-bottom: 1.5rem;
  }
  .badge .dot { width: 6px; height: 6px; background: var(--success); border-radius: 50%; animation: blink 2s infinite; }
  @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

  h1 { font-size: clamp(2.5rem, 6vw, 4rem); font-weight: 900; line-height: 1.1; margin-bottom: 1.5rem; }
  h1 .gradient { background: linear-gradient(135deg, var(--primary-light), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .subtitle { font-size: 1.1rem; color: var(--text-muted); max-width: 580px; margin-bottom: 2.5rem; }

  .audit-box {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px;
    padding: 2rem; width: 100%; max-width: 560px;
  }
  .input-row { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
  .input-row input {
    flex: 1; padding: 0.9rem 1.2rem; background: var(--bg); border: 1px solid var(--border);
    border-radius: 10px; color: var(--text); font-size: 1rem; font-family: 'Inter', sans-serif; outline: none;
  }
  .input-row input:focus { border-color: var(--primary); }
  .input-row input::placeholder { color: #555; }
  .btn-primary {
    padding: 0.9rem 2rem; background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    border: none; border-radius: 10px; color: white; font-size: 1rem; font-weight: 600;
    cursor: pointer; font-family: 'Inter', sans-serif; white-space: nowrap;
  }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(108,58,237,0.3); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .trust-line { font-size: 0.8rem; color: #555; text-align: center; }
  .error-msg { color: var(--danger); font-size: 0.85rem; margin-top: 0.5rem; display: none; }

  .stats-bar { display: flex; gap: 2rem; justify-content: center; margin-top: 3rem; }
  .stat-num { font-size: 1.5rem; font-weight: 800; color: var(--accent); }
  .stat-label { font-size: 0.75rem; color: var(--text-muted); }

  /* Loading */
  #loadingSection { display: none; text-align: center; padding: 4rem 2rem; min-height: 60vh; }
  .spinner { width: 48px; height: 48px; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .steps { list-style: none; max-width: 400px; margin: 1.5rem auto; text-align: left; }
  .steps li { padding: 0.5rem 0; color: var(--text-muted); font-size: 0.9rem; }
  .steps li.done { color: var(--success); }
  .steps li.active { color: var(--text); font-weight: 500; }

  /* Results */
  #resultsSection { display: none; max-width: 900px; margin: 0 auto; padding: 2rem; }

  .score-hero {
    text-align: center; padding: 3rem 2rem; background: var(--bg-card);
    border-radius: 20px; border: 1px solid var(--border); margin-bottom: 2rem;
  }
  .score-circle {
    width: 170px; height: 170px; border-radius: 50%; display: flex; flex-direction: column;
    align-items: center; justify-content: center; margin: 0 auto 1.5rem;
  }
  .score-circle.low { background: radial-gradient(circle, rgba(239,68,68,0.15), transparent 70%); border: 3px solid var(--danger); }
  .score-circle.medium { background: radial-gradient(circle, rgba(245,158,11,0.15), transparent 70%); border: 3px solid var(--warning); }
  .score-circle.high { background: radial-gradient(circle, rgba(16,185,129,0.15), transparent 70%); border: 3px solid var(--success); }
  .score-number { font-size: 3.5rem; font-weight: 900; line-height: 1; }
  .score-circle.low .score-number { color: var(--danger); }
  .score-circle.medium .score-number { color: var(--warning); }
  .score-circle.high .score-number { color: var(--success); }
  .score-label { font-size: 0.85rem; color: var(--text-muted); }

  .breakdown { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
  @media (max-width: 640px) { .breakdown { grid-template-columns: 1fr; } .input-row { flex-direction: column; } }
  .check-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; }
  .check-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }
  .check-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1rem; }
  .check-icon.pass { background: rgba(16,185,129,0.15); color: var(--success); }
  .check-icon.fail { background: rgba(239,68,68,0.15); color: var(--danger); }
  .check-icon.warn { background: rgba(245,158,11,0.15); color: var(--warning); }
  .check-title { font-weight: 600; font-size: 0.95rem; }
  .check-score { font-size: 0.8rem; color: var(--text-muted); }
  .check-detail { font-size: 0.85rem; color: var(--text-muted); line-height: 1.5; }

  .recs { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; margin-bottom: 2rem; }
  .rec-item { padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
  .rec-item:last-child { border: none; }
  .rec-priority { font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
  .rec-priority.HIGH { background: rgba(239,68,68,0.2); color: var(--danger); }
  .rec-priority.MEDIUM { background: rgba(245,158,11,0.2); color: var(--warning); }

  .revenue-box {
    background: linear-gradient(135deg, rgba(108,58,237,0.1), rgba(245,158,11,0.1));
    border: 1px solid rgba(108,58,237,0.3); border-radius: 14px; padding: 2rem;
    text-align: center; margin-bottom: 2rem;
  }
  .revenue-number { font-size: 2.2rem; font-weight: 900; color: var(--accent); }

  .cta-section {
    text-align: center; padding: 2.5rem; background: var(--bg-card);
    border-radius: 14px; border: 1px solid var(--border);
  }
  .btn-cta {
    padding: 1rem 3rem; background: linear-gradient(135deg, var(--accent), #D97706);
    border: none; border-radius: 12px; color: #000; font-size: 1.1rem;
    font-weight: 700; cursor: pointer; font-family: 'Inter', sans-serif;
  }
</style>
</head>
<body>

<!-- HERO -->
<section id="heroSection" class="hero">
  <div class="badge"><span class="dot"></span> Free AI Visibility Audit</div>
  <h1>Is your store <span class="gradient">invisible</span><br>to AI shopping agents?</h1>
  <p class="subtitle">91% of online stores can't be found by ChatGPT, Gemini, or Perplexity when customers ask them to shop. Check yours in 60 seconds.</p>
  <div class="audit-box">
    <form id="auditForm" onsubmit="startAudit(event)">
      <div class="input-row">
        <input type="text" id="storeUrl" placeholder="Enter your store URL (e.g. mystore.com)" required>
        <button class="btn-primary" type="submit" id="auditBtn">Audit My Store</button>
      </div>
    </form>
    <div class="error-msg" id="errorMsg"></div>
    <div class="trust-line">Free forever. No credit card. No login required.</div>
  </div>
  <div class="stats-bar">
    <div><div class="stat-num">91%</div><div class="stat-label">stores invisible<br>to AI agents</div></div>
    <div><div class="stat-num">6.7x</div><div class="stat-label">visibility gap</div></div>
    <div><div class="stat-num">$20.9B</div><div class="stat-label">AI retail spend<br>in 2026</div></div>
  </div>
</section>

<!-- LOADING -->
<section id="loadingSection">
  <div class="spinner"></div>
  <h2>Scanning your store...</h2>
  <p style="color:var(--text-muted); margin-bottom:1.5rem;">This takes 30-90 seconds. We're scanning real product data.</p>
  <ul class="steps" id="steps">
    <li class="active" id="step0">Detecting platform and fetching products...</li>
    <li id="step1">Checking Schema.org markup...</li>
    <li id="step2">Measuring attribute completeness...</li>
    <li id="step3">Checking GTIN/UPC codes...</li>
    <li id="step4">Testing UCP endpoint...</li>
    <li id="step5">Evaluating descriptions and reviews...</li>
    <li id="step6">Calculating your AgentRank score...</li>
  </ul>
</section>

<!-- RESULTS -->
<section id="resultsSection"></section>

<script>
async function startAudit(e) {
  e.preventDefault();
  const url = document.getElementById('storeUrl').value.trim();
  if (!url) return;

  document.getElementById('heroSection').style.display = 'none';
  document.getElementById('loadingSection').style.display = 'block';
  document.getElementById('errorMsg').style.display = 'none';

  // Animate steps
  let step = 0;
  const stepInterval = setInterval(() => {
    if (step > 0) {
      document.getElementById('step' + (step-1)).classList.remove('active');
      document.getElementById('step' + (step-1)).classList.add('done');
      document.getElementById('step' + (step-1)).textContent = '✓ ' + document.getElementById('step' + (step-1)).textContent;
    }
    if (step <= 6) {
      document.getElementById('step' + step).classList.add('active');
      step++;
    }
  }, 4000);

  try {
    const resp = await fetch('/api/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });

    clearInterval(stepInterval);

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || 'Audit failed');
    }

    const data = await resp.json();
    showResults(data);
  } catch (err) {
    clearInterval(stepInterval);
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('heroSection').style.display = 'flex';
    document.getElementById('errorMsg').textContent = 'Error: ' + err.message + '. Please check the URL and try again.';
    document.getElementById('errorMsg').style.display = 'block';
  }
}

function showResults(data) {
  document.getElementById('loadingSection').style.display = 'none';
  const section = document.getElementById('resultsSection');
  section.style.display = 'block';

  const score = data.score;
  const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
  const verdict = score >= 70 ? 'Your store has good AI agent visibility'
    : score >= 40 ? 'Your store has partial visibility — agents miss most of your products'
    : 'Your store is mostly invisible to AI shopping agents';

  let checksHTML = '';
  for (const [key, check] of Object.entries(data.checks)) {
    const icon = check.status === 'pass' ? '✓' : check.status === 'warn' ? '!' : '✗';
    checksHTML += `
      <div class="check-card">
        <div class="check-header">
          <div class="check-icon ${check.status}">${icon}</div>
          <div>
            <div class="check-title">${check.name}</div>
            <div class="check-score">Score: ${check.score}</div>
          </div>
        </div>
        <div class="check-detail">${check.summary}</div>
      </div>`;
  }

  let recsHTML = '';
  for (const rec of data.recommendations) {
    recsHTML += `
      <div class="rec-item">
        <span class="rec-priority ${rec.priority}">${rec.priority}</span>
        <strong style="margin-left:0.5rem">${rec.action}</strong>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.25rem">${rec.impact}</div>
      </div>`;
  }

  const rev = data.revenue_impact;

  section.innerHTML = `
    <div class="score-hero">
      <div class="score-circle ${scoreClass}">
        <div class="score-number">${score}</div>
        <div class="score-label">out of 100</div>
      </div>
      <h2 style="margin-bottom:0.5rem">${verdict}</h2>
      <p style="color:var(--text-muted); max-width:500px; margin:0 auto; font-size:0.95rem">
        ${data.domain} | ${data.platform} | ${data.product_count} products found | Grade: ${data.grade}
      </p>
    </div>

    <h2 style="font-size:1.2rem; margin-bottom:1rem">Detailed Breakdown</h2>
    <div class="breakdown">${checksHTML}</div>

    ${recsHTML ? `<div class="recs"><h3 style="margin-bottom:1rem">What To Fix (Priority Order)</h3>${recsHTML}</div>` : ''}

    <div class="revenue-box">
      <div style="color:var(--text-muted); margin-bottom:0.5rem">Estimated Annual Revenue You're Missing</div>
      <div class="revenue-number">${rev.estimated_missed_revenue_low || 'N/A'} — ${rev.estimated_missed_revenue_high || 'N/A'}</div>
      <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.5rem">${rev.basis || ''}</div>
    </div>

    <div class="cta-section">
      <h2 style="margin-bottom:0.5rem">Want us to fix this?</h2>
      <p style="color:var(--text-muted); margin-bottom:1.5rem; max-width:450px; margin-left:auto; margin-right:auto">
        We optimize your store for AI agents at zero upfront cost. You only pay when agent-driven sales increase.
      </p>
      <div style="max-width:400px; margin:0 auto 1rem">
        <div class="input-row">
          <input type="email" id="contactEmail" placeholder="Enter your email" style="flex:1;padding:0.9rem 1.2rem;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:1rem;font-family:'Inter',sans-serif;outline:none">
        </div>
      </div>
      <button class="btn-cta" onclick="submitLead()">Get My Free Optimization Plan</button>
      <p style="font-size:0.75rem; color:#555; margin-top:1rem">Zero cost. Zero risk. We only earn when you earn.</p>
    </div>
  `;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function submitLead() {
  const email = document.getElementById('contactEmail').value.trim();
  if (!email || !email.includes('@')) return;
  try {
    await fetch('/api/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, url: document.getElementById('storeUrl')?.value || '' })
    });
  } catch(e) {}
  const btn = document.querySelector('.btn-cta');
  btn.textContent = 'Sent! We\\'ll be in touch within 24 hours.';
  btn.style.background = 'linear-gradient(135deg, #10B981, #059669)';
  btn.style.color = 'white';
}
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return LANDING_PAGE

@app.route('/api/audit', methods=['POST'])
def audit():
    """Run audit on a store URL and return JSON results."""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'error': 'Please enter a store URL'}), 400

        # Normalize
        if not url.startswith('http'):
            url = 'https://' + url

        # Check cache
        if url in audit_cache:
            return jsonify(audit_cache[url])

        # Run audit
        auditor = AgentRankAuditor(url)
        results = auditor.run_full_audit()

        # Cache results
        audit_cache[url] = results

        return jsonify(results)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Audit failed: {str(e)}'}), 500

@app.route('/api/lead', methods=['POST'])
def capture_lead():
    """Capture email lead for follow-up."""
    data = request.get_json()
    email = data.get('email', '')
    url = data.get('url', '')

    # In production: save to DB, send to CRM, trigger email sequence
    # For MVP: save to a JSON file
    leads_file = 'leads.json'
    leads = []
    if os.path.exists(leads_file):
        with open(leads_file) as f:
            leads = json.load(f)

    leads.append({
        'email': email,
        'store_url': url,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
    })

    with open(leads_file, 'w') as f:
        json.dump(leads, f, indent=2)

    print(f"[LEAD CAPTURED] {email} — {url}")
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  AgentRank MVP is running!")
    print("  Open: http://localhost:5000")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
