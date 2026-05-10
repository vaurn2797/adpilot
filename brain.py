import os
import requests
from groq import Groq
from flask import Flask

app = Flask(__name__)

META_ACCESS_TOKEN = os.environ.get("META_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_KEY", "")

def get_all_accounts():
    url = f"https://graph.facebook.com/v21.0/me/adaccounts?fields=name,id,amount_spent&access_token={META_ACCESS_TOKEN}"
    r = requests.get(url)
    return r.json().get('data', [])

def get_campaigns(account_id):
    url = f"https://graph.facebook.com/v21.0/{account_id}/campaigns?fields=name,status,objective,daily_budget,id&access_token={META_ACCESS_TOKEN}"
    r = requests.get(url)
    return r.json().get('data', [])

def get_campaign_insights(campaign_id):
    url = f"https://graph.facebook.com/v21.0/{campaign_id}/insights?fields=spend,impressions,clicks,ctr,cpc,cpm,reach,frequency,actions,cost_per_action_type,landing_page_views,cost_per_landing_page_view&date_preset=last_30d&access_token={META_ACCESS_TOKEN}"
    r = requests.get(url)
    data = r.json().get('data', [])
    return data[0] if data else {}

def get_ai_analysis(account, campaigns):
    client = Groq(api_key=GROQ_API_KEY)
    chat = client.chat.completions.create(
        messages=[{
            "role": "user",
            "content": f"""You are an expert Meta Ads analyst. Analyze this account and campaigns data and give exactly 3 specific recommendations.
Account: {account}
Campaigns: {campaigns}
Format each recommendation as: TITLE: short title | PROBLEM: one line problem | FIX: one line action
Be specific with numbers where possible."""
        }],
        model="llama-3.3-70b-versatile",
    )
    return chat.choices[0].message.content

def get_metric(ins, key):
    return ins.get(key, "—")

def get_action(ins, action_type):
    actions = ins.get('actions', [])
    for a in actions:
        if a.get('action_type') == action_type:
            return a.get('value', "—")
    return "—"

def get_cost_per_action(ins, action_type):
    costs = ins.get('cost_per_action_type', [])
    for a in costs:
        if a.get('action_type') == action_type:
            try:
                return f"₹{float(a.get('value', 0)):,.2f}"
            except:
                return "—"
    return "—"

@app.route('/')
@app.route('/account/<account_id>')
def dashboard(account_id=None):
    accounts = get_all_accounts()
    selected = accounts[0] if accounts else {}
    if account_id:
        for acc in accounts:
            if acc['id'] == account_id:
                selected = acc
                break

    campaigns = get_campaigns(selected.get('id', ''))
    
    for c in campaigns:
        c['ins'] = get_campaign_insights(c.get('id', ''))

    analysis_raw = get_ai_analysis(selected, campaigns)

    cards_html = ""
    icons = ["🎯", "💰", "📈"]
    colors = ["#4361ee", "#f72585", "#4cc9f0"]
    for i, line in enumerate(analysis_raw.strip().split('\n')):
        if '|' in line:
            parts = line.split('|')
            title = parts[0].replace('TITLE:', '').strip()
            problem = parts[1].replace('PROBLEM:', '').strip() if len(parts) > 1 else ''
            fix = parts[2].replace('FIX:', '').strip() if len(parts) > 2 else ''
            color = colors[i % 3]
            icon = icons[i % 3]
            cards_html += f"""
            <div class="rec-card">
                <div class="rec-icon" style="background:{color}20;color:{color}">{icon}</div>
                <div class="rec-body">
                    <div class="rec-title">{title}</div>
                    <div class="rec-problem">⚠️ {problem}</div>
                    <div class="rec-fix">✅ {fix}</div>
                </div>
            </div>"""

    campaigns_html = ""
    for c in campaigns:
        status = c.get('status', 'UNKNOWN')
        status_color = "#06d6a0" if status == "ACTIVE" else "#aaa"
        ins = c.get('ins', {})

        spend = get_metric(ins, 'spend')
        impressions = get_metric(ins, 'impressions')
        clicks = get_metric(ins, 'clicks')
        ctr = get_metric(ins, 'ctr')
        cpc = get_metric(ins, 'cpc')
        cpm = get_metric(ins, 'cpm')
        reach = get_metric(ins, 'reach')
        frequency = get_metric(ins, 'frequency')
        atc = get_action(ins, 'add_to_cart')
        purchases = get_action(ins, 'purchase')
        checkout = get_action(ins, 'initiate_checkout')
        lpv = get_metric(ins, 'landing_page_views')
        cost_atc = get_cost_per_action(ins, 'add_to_cart')
        cost_lpv = get_metric(ins, 'cost_per_landing_page_view')

        try:
            spend_fmt = f"₹{float(spend):,.0f}" if spend != "—" else "—"
            ctr_fmt = f"{float(ctr):.2f}%" if ctr != "—" else "—"
            freq_fmt = f"{float(frequency):.2f}" if frequency != "—" else "—"
            cpc_fmt = f"₹{float(cpc):,.2f}" if cpc != "—" else "—"
            cpm_fmt = f"₹{float(cpm):,.2f}" if cpm != "—" else "—"
            lpv_cost_fmt = f"₹{float(cost_lpv):,.2f}" if cost_lpv != "—" else "—"
        except:
            spend_fmt = spend
            ctr_fmt = ctr
            freq_fmt = frequency
            cpc_fmt = cpc
            cpm_fmt = cpm
            lpv_cost_fmt = cost_lpv

        campaigns_html += f"""
        <div class="camp-card">
            <div class="camp-header">
                <div class="camp-dot" style="background:{status_color}"></div>
                <div class="camp-name">{c.get('name','Unknown')}</div>
                <div class="camp-status" style="color:{status_color}">{status}</div>
            </div>
            <div class="metrics-grid">
                <div class="metric"><div class="m-label">Amount Spent</div><div class="m-value">{spend_fmt}</div></div>
                <div class="metric"><div class="m-label">Impressions</div><div class="m-value">{impressions}</div></div>
                <div class="metric"><div class="m-label">Reach</div><div class="m-value">{reach}</div></div>
                <div class="metric"><div class="m-label">Frequency</div><div class="m-value">{freq_fmt}</div></div>
                <div class="metric"><div class="m-label">Link Clicks</div><div class="m-value">{clicks}</div></div>
                <div class="metric"><div class="m-label">CTR (All)</div><div class="m-value">{ctr_fmt}</div></div>
                <div class="metric"><div class="m-label">CPC</div><div class="m-value">{cpc_fmt}</div></div>
                <div class="metric"><div class="m-label">CPM</div><div class="m-value">{cpm_fmt}</div></div>
                <div class="metric"><div class="m-label">Landing Page Views</div><div class="m-value">{lpv}</div></div>
                <div class="metric"><div class="m-label">Cost per LPV</div><div class="m-value">{lpv_cost_fmt}</div></div>
                <div class="metric"><div class="m-label">Add to Cart</div><div class="m-value">{atc}</div></div>
                <div class="metric"><div class="m-label">Cost per ATC</div><div class="m-value">{cost_atc}</div></div>
                <div class="metric"><div class="m-label">Initiate Checkout</div><div class="m-value">{checkout}</div></div>
                <div class="metric"><div class="m-label">Purchases</div><div class="m-value">{purchases}</div></div>
            </div>
        </div>"""

    sidebar_html = ""
    for acc in accounts:
        spent = int(acc.get('amount_spent', 0)) // 100
        is_active = acc['id'] == selected.get('id')
        active_class = "active" if is_active else ""
        sidebar_html += f"""
        <a href="/account/{acc['id']}" class="acc-item {active_class}">
            <div class="acc-avatar">{acc['name'][0].upper()}</div>
            <div class="acc-info">
                <div class="acc-item-name">{acc['name']}</div>
                <div class="acc-item-spend">₹{spent:,}</div>
            </div>
            {'<div class="active-dot"></div>' if is_active else ''}
        </a>"""

    selected_spend = int(selected.get('amount_spent', 0)) // 100
    active_count = sum(1 for c in campaigns if c.get('status') == 'ACTIVE')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AdPilot AI</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',sans-serif; background:#f0f2f7; display:flex; flex-direction:column; height:100vh; }}
  .topbar {{ background:#fff; padding:14px 24px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #e8e8e8; }}
  .logo {{ font-size:20px; font-weight:700; color:#4361ee; }}
  .logo span {{ background:#4361ee; color:white; padding:2px 10px; border-radius:20px; font-size:11px; margin-left:8px; }}
  .body-wrap {{ display:flex; flex:1; overflow:hidden; }}
  .sidebar {{ width:260px; background:#1a1a2e; color:white; display:flex; flex-direction:column; overflow-y:auto; }}
  .sidebar-header {{ padding:20px 16px 12px; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#888; }}
  .acc-item {{ display:flex; align-items:center; gap:10px; padding:12px 16px; cursor:pointer; text-decoration:none; color:white; border-left:3px solid transparent; }}
  .acc-item:hover {{ background:#ffffff15; }}
  .acc-item.active {{ background:#4361ee25; border-left:3px solid #4361ee; }}
  .acc-avatar {{ width:36px; height:36px; border-radius:10px; background:#4361ee; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px; flex-shrink:0; }}
  .acc-info {{ flex:1; overflow:hidden; }}
  .acc-item-name {{ font-size:13px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .acc-item-spend {{ font-size:11px; color:#888; margin-top:2px; }}
  .active-dot {{ width:8px; height:8px; background:#4cc9f0; border-radius:50%; flex-shrink:0; }}
  .main {{ flex:1; overflow-y:auto; padding:24px; }}
  .acc-header {{ margin-bottom:20px; }}
  .acc-header h2 {{ font-size:22px; font-weight:700; }}
  .acc-header p {{ font-size:13px; color:#888; margin-top:4px; }}
  .stats-row {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:22px; }}
  .stat-card {{ background:white; border-radius:12px; padding:18px; border-top:4px solid; }}
  .stat-card.blue {{ border-color:#4361ee; }}
  .stat-card.pink {{ border-color:#f72585; }}
  .stat-card.cyan {{ border-color:#4cc9f0; }}
  .stat-label {{ font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px; }}
  .stat-value {{ font-size:24px; font-weight:700; }}
  .stat-sub {{ font-size:11px; color:#aaa; margin-top:4px; }}
  .two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px; }}
  .section {{ background:white; border-radius:12px; padding:20px; }}
  .section-title {{ font-size:15px; font-weight:600; margin-bottom:16px; }}
  .rec-card {{ display:flex; gap:12px; padding:12px 0; border-bottom:1px solid #f5f5f5; }}
  .rec-card:last-child {{ border-bottom:none; }}
  .rec-icon {{ width:42px; height:42px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }}
  .rec-body {{ flex:1; }}
  .rec-title {{ font-size:14px; font-weight:600; margin-bottom:4px; }}
  .rec-problem {{ font-size:12px; color:#e63946; margin-bottom:3px; }}
  .rec-fix {{ font-size:12px; color:#2a9d8f; }}
  .camp-card {{ background:white; border-radius:12px; padding:18px; margin-bottom:14px; }}
  .camp-header {{ display:flex; align-items:center; gap:10px; margin-bottom:14px; }}
  .camp-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
  .camp-name {{ flex:1; font-size:14px; font-weight:600; }}
  .camp-status {{ font-size:11px; font-weight:700; }}
  .metrics-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
  .metric {{ background:#f8f9fa; border-radius:8px; padding:10px; }}
  .m-label {{ font-size:10px; color:#888; margin-bottom:4px; text-transform:uppercase; }}
  .m-value {{ font-size:14px; font-weight:700; color:#1a1a2e; }}
</style>
</head>
<body>
<div class="topbar">
  <div class="logo">AdPilot AI <span>LIVE</span></div>
  <div style="font-size:13px;color:#666">Meta Ads Connected ✅</div>
</div>
<div class="body-wrap">
  <div class="sidebar">
    <div class="sidebar-header">Your Accounts</div>
    {sidebar_html}
  </div>
  <div class="main">
    <div class="acc-header">
      <h2>{selected.get('name', 'Account')}</h2>
      <p>AI Analysis — Generated just now</p>
    </div>
    <div class="stats-row">
      <div class="stat-card blue">
        <div class="stat-label">Total Spend</div>
        <div class="stat-value">₹{selected_spend:,}</div>
        <div class="stat-sub">This account</div>
      </div>
      <div class="stat-card pink">
        <div class="stat-label">Total Campaigns</div>
        <div class="stat-value">{len(campaigns)}</div>
        <div class="stat-sub">All campaigns</div>
      </div>
      <div class="stat-card cyan">
        <div class="stat-label">Active Campaigns</div>
        <div class="stat-value">{active_count}</div>
        <div class="stat-sub">Currently running</div>
      </div>
    </div>
    <div class="two-col">
      <div class="section">
        <div class="section-title">🤖 AI Recommendations</div>
        {cards_html}
      </div>
      <div class="section">
        <div class="section-title">📊 Account Overview</div>
        <p style="font-size:13px;color:#666">Campaigns with metrics shown below</p>
      </div>
    </div>
    <div class="section-title" style="margin-bottom:14px">📋 Campaigns & Metrics</div>
    {campaigns_html}
  </div>
</div>
</body>
</html>"""

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)