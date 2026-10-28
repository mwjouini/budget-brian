# Vivid Healthcare Job Watcher • Budget Brian Intelligence Suite

An automated, serverless intelligence portal running 24/7 on GitHub Actions and GitHub Pages. It continuously monitors public recruitment boards for **Registered Manager** positions related to **Vivid Healthcare Limited / Vivid Healthcare Search Limited**, primarily across **Northern Ireland / Belfast (RQIA compliance framework)**.

🌐 **Live Dashboard**: [https://mwjouini.github.io/budget-brian/](https://mwjouini.github.io/budget-brian/)  
🔐 **Security**: Cryptographically gated with client-side SHA-256 session authorization. Passcode is customizable inside dashboard settings.

---

## ⚡ Architecture & Cloud Operation (100% Serverless)

1. **Hourly Cloud Worker (GitHub Actions)**:
   - Executes automatically **every 1 hour** via `.github/workflows/watcher.yml` (`cron: '0 * * * *'`).
   - Completely serverless: no local hardware, zero background laptop load.
   - Can also be triggered in-page from the web dashboard.

2. **9 Public Recruitment Sources Monitored**:
   - 🏢 **Reed.co.uk**: Vivid Healthcare Search Limited Recruiter Profile (`p45258`).
   - 🌐 **Vivid Healthcare Official Website**: Careers and service vacancy announcements (`vivid-healthcare.co.uk`).
   - 💼 **LinkedIn Jobs**: Public Guest Search API for Vivid Healthcare mandates in Northern Ireland.
   - 🔍 **Indeed UK**: Direct query endpoint targeting Vivid Healthcare in Northern Ireland.
   - 🍀 **NIJobs.com**: Northern Ireland regional recruitment portal.
   - 📋 **Totaljobs.com**: Belfast & Northern Ireland registered manager search.
   - 📑 **CV-Library**: Active agency mandates in Belfast.
   - 🏢 **Glassdoor UK**: Regional listings.
   - 🏥 **NHS Jobs**: Belfast HSC trusts & intermediate care oversight (`jobs.nhs.uk`).

3. **Strict Zero-Noise Match Protocol (0–100 Scoring)**:
   - Rules specified in `config/keywords.yml`.
   - **High Match (≥ 85)**: Core role (*Registered Manager*) + organisation (*Vivid Healthcare*) or regulator (*RQIA*) in Northern Ireland / Belfast.
   - **Negative Keyword Filter**: Automatically rejects unrelated roles (*Cook*, *Chef*, *Retail*, *Veterinary*, etc.).
   - Discards non-target companies to prevent false positives.
   - Every candidate URL is verified via live HTTP probe before storage.

4. **Executive Web Dashboard**:
   - Gated with SHA-256 client authentication.
   - Real-time search, filters by source and relevance score.
   - Direct, verified links to original job postings (`target="_blank"`).
   - In-page live data refresh & remote cloud dispatch with zero page redirect.
   - Hourly audit log with per-source health status.
