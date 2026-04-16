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
    init_db, get_jobs, get_stats, set_status, get_job, get_pending_review, set_documents
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
    """Show an inline base64 PDF embed viewer + download button below."""
    p = Path(path)
    if not p.exists():
        st.warning(f"{label} file not found.")
        return
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600px"></iframe>',
        unsafe_allow_html=True,
    )
    st.download_button(
        label=f"⬇ Download {label}",
        data=data,
        file_name=p.name,
        mime="application/pdf",
        key=f"dl_{label}_{p.stem}_{int(time.time())}",
    )


def run_pipeline(run_now: bool = True):
    """Trigger scrape → score → notify."""
    from src.scraper import run_search
    from src.scorer import score_unscored_jobs
    from src.notifier import notify_pending_review, notify_daily_summary
    from src.scheduler import _run_gov_scrapers

    with st.spinner("Running job search pipeline..."):
        new = run_search()
        gov_new = _run_gov_scrapers()
        new += gov_new

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

    st.success(f"Done! Found {new} new jobs ({gov_new} from government sources), scored {scored}.")
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
        # ── Batch Actions ─────────────────────────────────────────────────────
        st.subheader("Batch Actions")
        st.caption(
            "Select rows below, then Auto-Apply or Remove. Auto-Apply runs the "
            "full pipeline (tailor resume if needed → fresh cover letter → Easy "
            "Apply) on each selected job sequentially. Failures are marked "
            "`apply_failed` and the batch continues."
        )

        from src.resume_builder import resume_match_score

        def _role_label(rt: str) -> str:
            return "Program Manager" if rt == "pm" else "Analyst"

        def _match_cell(j: dict) -> str:
            try:
                return f"{resume_match_score(j)}%"
            except Exception:
                return "—"

        batch_job_ids = [j["job_id"] for j in pending]
        batch_df = pd.DataFrame([{
            "Select":   False,
            "Score":    j.get("score"),
            "Title":    j.get("title"),
            "Company":  j.get("company"),
            "Role":     _role_label(j.get("role_type") or "analyst"),
            "Match":    _match_cell(j),
            "Industry": (j.get("industry") or "tech").title(),
        } for j in pending])

        _batch_state = st.session_state.get("batch_table", {})
        _edited_rows = _batch_state.get("edited_rows", {}) if isinstance(_batch_state, dict) else {}
        _any_checked = any(row.get("Select") for row in _edited_rows.values())

        b_apply_col, b_remove_col, _b_spacer = st.columns([1, 1, 4])
        with b_apply_col:
            batch_apply_clicked = st.button(
                "✅ Auto-Apply Selected",
                type="primary",
                key="batch_apply_btn",
                disabled=not _any_checked,
            )
        with b_remove_col:
            batch_remove_clicked = st.button(
                "❌ Remove Selected",
                key="batch_remove_btn",
                disabled=not _any_checked,
            )

        edited_batch = st.data_editor(
            batch_df,
            key="batch_table",
            width="stretch",
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=False),
                "Score":  st.column_config.NumberColumn("Score", format="%.1f"),
            },
            disabled=["Score", "Title", "Company", "Role", "Match", "Industry"],
        )

        if batch_apply_clicked:
            checked_idx = [i for i, v in enumerate(edited_batch["Select"].tolist()) if v]
            if not checked_idx:
                st.warning("No rows selected.")
            else:
                from src.applicator import apply_job
                success = 0
                failure = 0
                total = len(checked_idx)
                for i in checked_idx:
                    jid = batch_job_ids[i]
                    row = pending[i]
                    label = f"Applying to {row['title']} @ {row['company']}"
                    with st.status(label, expanded=False) as status:
                        try:
                            result = apply_job(jid)
                            if result:
                                success += 1
                                status.update(
                                    label=f"✅ {row['title']} @ {row['company']}",
                                    state="complete",
                                )
                            else:
                                failure += 1
                                status.update(
                                    label=f"❌ {row['title']} @ {row['company']} — Easy Apply unavailable",
                                    state="error",
                                )
                        except Exception as e:
                            failure += 1
                            status.update(
                                label=f"❌ {row['title']} @ {row['company']} — {e}",
                                state="error",
                            )
                st.success(
                    f"Applied to {success} of {total} jobs — "
                    f"{failure} failed and marked apply_failed"
                )
                st.rerun()

        if batch_remove_clicked:
            checked_idx = [i for i, v in enumerate(edited_batch["Select"].tolist()) if v]
            if not checked_idx:
                st.warning("No rows selected.")
            else:
                removed = 0
                for i in checked_idx:
                    try:
                        set_status(batch_job_ids[i], "rejected")
                        removed += 1
                    except Exception as e:
                        print(f"[batch_remove] failed {batch_job_ids[i]}: {e}")
                st.success(f"Removed {removed} jobs from the queue")
                st.rerun()

        st.divider()

        for job in pending:
            score = job.get("score")
            score_display = f"{score}/10" if score else "?"
            industry_label = (job.get("industry") or "tech").title()
            with st.expander(
                f"{'🟢' if score and score >= 7 else '🟡'} {job['title']} @ {job['company']}  —  "
                f"Score {score_display}  |  {job.get('location', '')}  |  "
                f"{status_badge(job['status'])}  |  🏷 {industry_label}",
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

                # ── Original-resume-suffices banner ──────────────────────────
                if job["status"] != "applied":
                    try:
                        from src.resume_builder import resume_match_score
                        match_pct = resume_match_score(job)
                        role_label = (job.get("role_type") or "analyst").replace("pm", "program manager")
                        if match_pct >= 80:
                            st.info(
                                f"Your original {role_label} resume already matches this job "
                                f"at {match_pct}% — tailoring may not be needed. You can still "
                                "generate a tailored version below."
                            )
                    except Exception as e:
                        st.warning(f"Could not compute match score: {e}")

                if not resume_path or not Path(resume_path).exists():
                    if job["status"] not in ("applied",):
                        if st.button("📄 Generate Documents", key=f"gen_{job['job_id']}"):
                            with st.spinner("Generating tailored resume and cover letter..."):
                                from src.applicator import generate_documents_only
                                resume_path, cl_path = generate_documents_only(job["job_id"])
                            st.success("Documents generated! Scroll down to preview.")
                            st.rerun()
                else:
                    # ── Regenerate controls (above docs) ─────────────────────
                    if job["status"] != "applied":
                        regen_feedback = st.text_area(
                            "Feedback (optional)",
                            placeholder="e.g. 'Make the cover letter less formal' or 'Emphasize SQL more in resume'",
                            key=f"regen_feedback_{job['job_id']}",
                            height=80,
                            label_visibility="collapsed",
                        )
                        rb_col, rcl_col, both_col, _ = st.columns([1, 1, 1, 3])
                        with rb_col:
                            if st.button("🔄 Resume", key=f"regen_resume_{job['job_id']}"):
                                try:
                                    with st.spinner("Regenerating resume..."):
                                        from src.resume_builder import build_resume
                                        new_path = build_resume(get_job(job["job_id"]), feedback=regen_feedback)
                                        set_documents(job["job_id"], new_path, cl_path)
                                        if job["status"] == "approved":
                                            set_status(job["job_id"], "pending_review")
                                    st.success("Resume regenerated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed: {e}")
                        with rcl_col:
                            if st.button("🔄 Cover Letter", key=f"regen_cl_{job['job_id']}"):
                                try:
                                    with st.spinner("Regenerating cover letter..."):
                                        from src.cover_letter import build_cover_letter
                                        new_cl = build_cover_letter(get_job(job["job_id"]), feedback=regen_feedback)
                                        set_documents(job["job_id"], resume_path, new_cl)
                                        if job["status"] == "approved":
                                            set_status(job["job_id"], "pending_review")
                                    st.success("Cover letter regenerated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed: {e}")
                        with both_col:
                            if st.button("🔄 Both", key=f"regen_both_{job['job_id']}"):
                                try:
                                    with st.spinner("Regenerating both documents..."):
                                        from src.applicator import generate_documents_only
                                        generate_documents_only(
                                            job["job_id"],
                                            resume_feedback=regen_feedback,
                                            cover_letter_feedback=regen_feedback,
                                        )
                                        if job["status"] == "approved":
                                            set_status(job["job_id"], "pending_review")
                                    st.success("Both documents regenerated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed: {e}")

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
            "Industry":   (j.get("industry") or "tech").title(),
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
                      "Salary Min", "Status", "Industry", "Source", "Found", "URL"],
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
