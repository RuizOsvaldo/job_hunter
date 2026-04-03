"""
Job Hunter — Streamlit Dashboard
Tabs:
  1. Dashboard    — stats + manual trigger
  2. Review Queue — pending high-score jobs (approve / reject before apply)
  3. All Jobs     — full table with filters
  4. Applied      — applied jobs with downloadable resume + cover letter
"""
import json
import time
import base64
from pathlib import Path

import streamlit as st
import pandas as pd

from src.database import (
    init_db, get_jobs, get_stats, set_status, get_job, get_pending_review
)
import config

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="Job Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: #f0f4ff;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .score-high { color: #27ae60; font-weight: bold; }
    .score-mid  { color: #e67e22; font-weight: bold; }
    .score-low  { color: #e74c3c; font-weight: bold; }
    .status-applied   { color: #27ae60; }
    .status-pending   { color: #e67e22; }
    .status-rejected  { color: #e74c3c; }
    div[data-testid="stTabs"] button { font-size: 15px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def score_color(score):
    if score is None:
        return "—"
    if score >= 7:
        return f'<span class="score-high">{score}/10</span>'
    if score >= 5:
        return f'<span class="score-mid">{score}/10</span>'
    return f'<span class="score-low">{score}/10</span>'


def status_badge(status):
    colors_map = {
        "applied":        "🟢",
        "pending_review": "🟡",
        "approved":       "🔵",
        "scored":         "⚪",
        "found":          "⚪",
        "rejected":       "🔴",
        "skipped":        "⚫",
        "apply_failed":   "❌",
    }
    return f"{colors_map.get(status, '⚪')} {status.replace('_', ' ').title()}"


def pdf_viewer_and_download(label: str, path: str):
    """Show a PDF download button + inline base64 embed viewer."""
    p = Path(path)
    if not p.exists():
        st.warning(f"{label} file not found.")
        return
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    st.download_button(
        label=f"⬇ Download {label}",
        data=data,
        file_name=p.name,
        mime="application/pdf",
        key=f"dl_{label}_{p.stem}_{int(time.time())}",
    )
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600px"></iframe>',
        unsafe_allow_html=True,
    )


def run_pipeline(run_now: bool = True):
    """Trigger scrape → score → notify."""
    from src.scraper import run_search
    from src.scorer import score_unscored_jobs
    from src.notifier import notify_pending_review, notify_daily_summary

    with st.spinner("Running job search pipeline..."):
        new = run_search()
        scored = score_unscored_jobs()

        pending = get_pending_review()
        for job in pending:
            if not job.get("resume_path"):
                try:
                    notify_pending_review(job)
                except Exception:
                    pass

        stats = get_stats()
        try:
            notify_daily_summary(stats, new)
        except Exception:
            pass

    st.success(f"Done! Found {new} new jobs, scored {scored}.")
    time.sleep(1)
    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🔍 Review Queue",
    "📋 All Jobs",
    "✅ Applied",
])


# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────
with tab1:
    st.title("🎯 Job Hunter")
    st.caption(f"Searching for Data Analyst, Business Analyst, and related roles in San Diego (hybrid/remote) | Min salary: $80K")

    stats = get_stats()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Jobs Found", stats.get("total") or 0)
    col2.metric("Applied", stats.get("applied") or 0)
    col3.metric("Pending Review", stats.get("pending_review") or 0)
    col4.metric("Approved", stats.get("approved") or 0)
    col5.metric("Rejected / Skipped",
        (stats.get("rejected") or 0) + (stats.get("skipped") or 0))

    st.divider()
    st.subheader("Manual Trigger")
    st.caption("The pipeline also runs automatically at 8:00 AM weekdays.")
    if st.button("🔎 Run Job Search Now", type="primary", width="stretch"):
        run_pipeline()

    st.divider()
    st.subheader("Search Configuration")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Search terms:**")
        for t in config.SEARCH_TERMS:
            st.write(f"  • {t}")
    with c2:
        st.write("**Locations:**")
        for loc in config.SEARCH_LOCATIONS:
            st.write(f"  • {loc}")
    st.write(f"**Auto-apply threshold:** Score ≥ {config.AUTO_APPLY_THRESHOLD}/10")
    st.write(f"**Minimum salary:** ${config.MIN_SALARY:,}/year")


# ── Tab 2: Review Queue ───────────────────────────────────────────────────────
with tab2:
    st.title("🔍 Review Queue")
    st.caption(
        "These jobs scored ≥ 7/10. Preview the tailored resume and cover letter, "
        "then **Approve** to submit the application or **Reject** to skip."
    )

    pending = get_pending_review() + get_jobs("approved")

    if not pending:
        st.info("No jobs pending review. Run the pipeline or wait for the scheduled run.")
    else:
        for job in pending:
            score = job.get("score")
            score_display = f"{score}/10" if score else "?"
            with st.expander(
                f"{'🟢' if score and score >= 7 else '🟡'} {job['title']} @ {job['company']}  —  "
                f"Score {score_display}  |  {job.get('location', '')}  |  {status_badge(job['status'])}",
                expanded=False,
            ):
                col_l, col_r = st.columns([2, 1])

                with col_r:
                    st.markdown("**Score Reasons:**")
                    try:
                        reasons = json.loads(job.get("score_reasons") or "[]")
                    except Exception:
                        reasons = []
                    for r in reasons:
                        st.markdown(f"• {r}")

                    sal = ""
                    if job.get("salary_min") and job.get("salary_max"):
                        sal = f"${job['salary_min']:,} – ${job['salary_max']:,}"
                    elif job.get("salary_min"):
                        sal = f"${job['salary_min']:,}+"
                    if sal:
                        st.markdown(f"**Salary:** {sal}")
                    st.markdown(f"**Source:** {job.get('source', '—')}")
                    st.markdown(f"**Found:** {job.get('date_found', '')[:10]}")
                    st.markdown(f"[View Posting ↗]({job.get('apply_url', '#')})")

                with col_l:
                    st.markdown("**Job Description (excerpt):**")
                    desc = job.get("description", "")
                    st.markdown(desc[:800] + ("..." if len(desc) > 800 else ""))

                st.divider()

                # Document preview
                doc_col1, doc_col2 = st.columns(2)
                resume_path = job.get("resume_path")
                cl_path = job.get("cover_letter_path")

                if not resume_path or not Path(resume_path).exists():
                    if job["status"] not in ("applied",):
                        if st.button("📄 Generate Documents", key=f"gen_{job['job_id']}"):
                            with st.spinner("Generating tailored resume and cover letter..."):
                                from src.applicator import generate_documents_only
                                resume_path, cl_path = generate_documents_only(job["job_id"])
                            st.success("Documents generated! Scroll down to preview.")
                            st.rerun()
                else:
                    with doc_col1:
                        st.markdown("**Resume**")
                        pdf_viewer_and_download("Resume", resume_path)
                    with doc_col2:
                        st.markdown("**Cover Letter**")
                        pdf_viewer_and_download("Cover Letter", cl_path)

                    if job["status"] == "pending_review":
                        st.divider()
                        approve_col, manual_col, reject_col, _ = st.columns([1, 1, 1, 2])
                        with approve_col:
                            if st.button("✅ Auto-Apply", key=f"approve_{job['job_id']}",
                                         type="primary"):
                                set_status(job["job_id"], "approved")
                                with st.spinner("Submitting application..."):
                                    from src.applicator import apply_job
                                    result = apply_job(job["job_id"])
                                if result:
                                    st.success("Application submitted!")
                                else:
                                    st.warning(
                                        "Easy Apply not available — marked as failed. "
                                        "Check Applied tab or apply manually."
                                    )
                                st.rerun()
                        with manual_col:
                            if st.button("🖊 Applied Manually", key=f"manual_{job['job_id']}"):
                                set_status(job["job_id"], "applied", "Applied manually by user")
                                st.success("Marked as applied!")
                                st.rerun()
                        with reject_col:
                            if st.button("❌ Reject", key=f"reject_{job['job_id']}"):
                                set_status(job["job_id"], "rejected")
                                st.rerun()

                    elif job["status"] == "approved":
                        st.info("Approved — application in progress or already submitted.")


# ── Tab 3: All Jobs ───────────────────────────────────────────────────────────
with tab3:
    st.title("📋 All Jobs")

    all_jobs = get_jobs()

    if not all_jobs:
        st.info("No jobs found yet. Run the pipeline from the Dashboard tab.")
    else:
        # ── Filters ───────────────────────────────────────────────────────────
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            status_filter = st.multiselect(
                "Filter by status",
                options=["found", "scored", "pending_review", "approved",
                         "applied", "rejected", "skipped", "apply_failed"],
                default=[],
            )
        with fcol2:
            min_score_filter = st.slider("Minimum score", 0.0, 10.0, 0.0, 0.5)
        with fcol3:
            source_filter = st.multiselect(
                "Source",
                options=list({j.get("source", "") for j in all_jobs}),
                default=[],
            )

        # ── Apply filters ─────────────────────────────────────────────────────
        filtered = all_jobs
        if status_filter:
            filtered = [j for j in filtered if j.get("status") in status_filter]
        if min_score_filter > 0:
            filtered = [j for j in filtered if (j.get("score") or 0) >= min_score_filter]
        if source_filter:
            filtered = [j for j in filtered if j.get("source") in source_filter]

        st.caption(f"Showing {len(filtered)} of {len(all_jobs)} jobs")

        # ── Build dataframe ───────────────────────────────────────────────────
        job_ids = [j["job_id"] for j in filtered]
        df = pd.DataFrame([{
            "Applied?":   False,
            "Score":      j.get("score"),
            "Title":      j.get("title"),
            "Company":    j.get("company"),
            "Work Type":  j.get("work_type") or "—",
            "City":       j.get("city") or "—",
            "State":      j.get("state") or "—",
            "Salary Min": f"${j['salary_min']:,}" if j.get("salary_min") else "—",
            "Status":     j.get("status", "").replace("_", " ").title(),
            "Source":     j.get("source"),
            "Found":      (j.get("date_found") or "")[:10],
            "URL":        j.get("apply_url"),
        } for j in filtered])

        # ── Submit button above table ─────────────────────────────────────────
        if st.button("🖊 Mark Checked as Applied Manually", type="primary"):
            edited = st.session_state.get("jobs_table")
            if edited is not None:
                checked = edited[edited["Applied?"] == True]
                if checked.empty:
                    st.warning("No jobs checked.")
                else:
                    for idx in checked.index:
                        set_status(job_ids[idx], "applied", "Applied manually by user")
                    st.success(f"Marked {len(checked)} job(s) as applied.")
                    st.rerun()

        # ── Editable table with checkbox column ───────────────────────────────
        edited_df = st.data_editor(
            df,
            key="jobs_table",
            width="stretch",
            hide_index=True,
            column_config={
                "Applied?":   st.column_config.CheckboxColumn("Applied?", default=False),
                "Score":      st.column_config.NumberColumn("Score", format="%.1f"),
                "URL":        st.column_config.LinkColumn("URL"),
            },
            disabled=["Score", "Title", "Company", "Work Type", "City", "State",
                      "Salary Min", "Status", "Source", "Found", "URL"],
        )


# ── Tab 4: Applied ────────────────────────────────────────────────────────────
with tab4:
    st.title("✅ Applied Jobs")
    st.caption("All submitted applications with downloadable documents.")

    applied = get_jobs("applied")
    failed = get_jobs("apply_failed")
    all_applied = applied + failed

    if not all_applied:
        st.info("No applications submitted yet.")
    else:
        for job in all_applied:
            icon = "✅" if job["status"] == "applied" else "❌"
            with st.expander(
                f"{icon} {job['title']} @ {job['company']}  |  "
                f"Score {job.get('score', '?')}/10  |  Applied: {(job.get('applied_at') or '')[:10]}",
                expanded=False,
            ):
                info_col, doc_col = st.columns([1, 2])

                with info_col:
                    st.markdown(f"**Company:** {job.get('company')}")
                    st.markdown(f"**Location:** {job.get('location')}")
                    st.markdown(f"**Status:** {status_badge(job['status'])}")
                    if job.get("applied_at"):
                        st.markdown(f"**Submitted:** {job['applied_at'][:19]}")
                    if job.get("error_message"):
                        st.error(f"Error: {job['error_message']}")
                    st.markdown(f"[View Original Posting ↗]({job.get('apply_url', '#')})")

                    st.markdown("**Score Reasons:**")
                    try:
                        reasons = json.loads(job.get("score_reasons") or "[]")
                    except Exception:
                        reasons = []
                    for r in reasons:
                        st.markdown(f"• {r}")

                with doc_col:
                    doc_tab1, doc_tab2 = st.tabs(["Resume", "Cover Letter"])
                    with doc_tab1:
                        if job.get("resume_path"):
                            pdf_viewer_and_download("Resume", job["resume_path"])
                        else:
                            st.warning("Resume not found.")
                    with doc_tab2:
                        if job.get("cover_letter_path"):
                            pdf_viewer_and_download("Cover Letter", job["cover_letter_path"])
                        else:
                            st.warning("Cover letter not found.")
