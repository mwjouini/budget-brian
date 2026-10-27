# Vivid Healthcare Job Watcher (24/7 Cloud Automated Portal)

An automated, serverless intelligence portal running 24/7 on GitHub Actions and GitHub Pages. It continuously monitors public job boards for **Registered Manager** positions related to **Vivid Healthcare Limited / Vivid Healthcare Search Limited**, primarily across **Northern Ireland / Belfast (with RQIA compliance awareness)**.

🌐 **Live Dashboard**: [https://mwjouini.github.io/budget-brian/](https://mwjouini.github.io/budget-brian/)  
🔐 **Default Access Passcode**: `vivid2026` *(changeable anytime in dashboard settings)*

---

## ⚡ How It Works (100% Serverless Cloud Operation)

1. **Hourly GitHub Actions Cloud Worker**:
   - Runs automatically **every 1 hour** via `.github/workflows/watcher.yml` (`cron: '0 * * * *'`).
   - Requires **no local server**, **no laptop running**, and **zero maintenance**.
   - Can also be triggered manually anytime via the **Actions Tab** (`workflow_dispatch`).

2. **10 Monitored Public Recruitment Sources**:
   - 🏢 **Reed.co.uk**: Vivid Healthcare Search Limited Recruiter Profile (`p45258`).
   - 🌐 **Vivid Healthcare Official Website**: Contact, careers, and services portals (`vivid-healthcare.co.uk`).
   - 💼 **LinkedIn Jobs**: Public Guest Search API for Vivid Healthcare mandates in Northern Ireland.
   - 🔍 **Indeed UK**: Search query API targeting Vivid Healthcare in Northern Ireland.
   - 🍀 **NIJobs.com**: Northern Ireland's regional recruitment portal.
   - 📋 **Totaljobs.com**: Belfast & Northern Ireland registered manager search.
   - 📑 **CV-Library**: Active agency mandates in Belfast.
   - 🏢 **Glassdoor UK**: Regional listings.
   - 🏥 **NHS Jobs**: Jobs.nhs.uk Belfast trusts & intermediate care oversight.
   - 🌐 **Search Engine Index**: Automated query scanning for newly indexed vacancy links.

3. **Strict Zero-Noise Relevance Scoring (0–100)**:
   - Configured via `config/keywords.yml`.
   - **Strong Match (≥ 85)**: Core role (*Registered Manager*) + organisation (*Vivid Healthcare*) or regulator (*RQIA*) in Northern Ireland / Belfast.
   - **Negative Keyword Disqualification**: Automatically disqualifies unrelated occupations (*Cook*, *Chef*, *Retail*, *Veterinary*, etc.).
   - Discards any third-party company (*Lovisa, Iceland, Autism Initiatives, etc.*) to guarantee **zero false positives**.
   - Only 100% working, verified URLs are recorded.

4. **Executive Web Dashboard**:
   - Password-protected with client-side SHA-256 session management.
   - Real-time search, filters by source and relevance score.
   - Direct, verified links to original job postings (`target="_blank"`).
   - Hourly scan runs inspection log with per-source health status.
   - One-click export to **CSV** and **JSON**.
