# Job Hunter Skill

This skill evaluates job opportunities against the user's background, scores the match,
and generates tailored application materials -- resume bullets, cover letter, and statement
of qualifications -- for any job scoring 7 or higher.

---

## Candidate Profile

**Name:** Osvaldo

**Target roles:** Data Analyst, Business Analyst (also open to Program Analyst, Operations
Analyst, Data Coordinator, and similar titles)

**Target locations:** San Diego, CA (on-site or hybrid) and fully remote roles nationwide

**Technical skills:**
- Languages: Python, SQL, Apps Script (JavaScript)
- Cloud: Google Cloud Platform (BigQuery, Cloud Storage, Cloud Functions), AWS (in progress,
  Solutions Architect Associate cert underway)
- Tools: Docker, Ansible, Google Sheets (advanced), Looker Studio, Git/GitHub
- Automation: Playwright, web scraping, cron scheduling, ntfy.sh push notifications
- Data: pipeline design, ETL, dashboard development, data cleaning and normalization

**Soft skills and domain experience:**
- Program management and coordination in nonprofit and education sectors
- Curriculum development and instructional design
- Cross-functional stakeholder communication
- Grant reporting and data-driven program evaluation
- Volunteer and contractor management

**Current roles:**
- Program Manager, The LEAGUE of Amazing Programmers (coding education nonprofit)
- Programs Coordinator, Border Angels (humanitarian nonprofit)
- Former: Starbucks (operations, customer experience)

**Education and certifications:**
- Information Systems background
- DevOps certification in progress (COMP 643 -- Debian VMs, SSH, DNS, Docker, Ansible)
- AWS Solutions Architect Associate -- in progress
- Ham radio Technician class license

**Preferred sectors:** Government/public sector, nonprofit, education, tech, healthcare
analytics, civic tech

---

## Job Scoring Rubric

Score each job on a scale of 1 to 10 using these criteria. Be honest -- do not inflate scores.

| Score | Meaning |
|-------|---------|
| 9-10  | Near-perfect match. Role title, required skills, sector, and location all align. Likely to pass ATS and get an interview. |
| 7-8   | Strong match. Most requirements met. 1-2 gaps that are bridgeable with framing. Worth applying. |
| 5-6   | Partial match. Core skills align but significant gaps exist (missing required tools, wrong seniority, or poor location fit). Only apply if pipeline is thin. |
| 3-4   | Weak match. Role requires skills or experience Osvaldo does not have. High risk of ATS rejection. |
| 1-2   | Poor fit. Wrong field, wrong level, or requires qualifications that cannot be bridged. Skip. |

**Scoring factors (weight each honestly):**

1. Role title alignment with Data Analyst or Business Analyst targets (high weight)
2. Required technical skills overlap with his stack -- Python, SQL, GCP, Sheets (high weight)
3. Sector fit -- nonprofit, government, education preferred (medium weight)
4. Location -- San Diego on-site/hybrid or fully remote (medium weight)
5. Seniority level -- entry to mid level preferred, senior if requirements are bridgeable (medium weight)
6. Nice-to-have skills he has -- Apps Script, Docker, Ansible, Playwright, dashboard tools (low weight, bonus)
7. ATS keyword density -- how many of the job's keywords match his actual experience (medium weight)

---

## Output Format

### For jobs scoring below 7

Provide:
- Score (X/10)
- 2-3 sentence explanation of why it is below threshold
- Optional: one suggestion if the role could be worth revisiting later

### For jobs scoring 7 or above

Provide all five sections below. For non-government roles, Section 5 (Statement of
Qualifications) can be skipped unless the job explicitly requires one.

---

**SECTION 1 -- Match Score and Summary**

Score: X/10

Write 3-4 sentences explaining:
- Why this is a strong match
- Which of Osvaldo's skills directly address the job requirements
- Any gaps and how they can be framed positively

---

**SECTION 2 -- ATS Keyword Analysis**

List the most important keywords from the job description that Osvaldo can legitimately
claim. Flag any required keywords that are weak or missing from his profile so he knows
what to address in the cover letter.

Format:
- Strong matches: [list]
- Addressable gaps: [list]
- Keywords to incorporate: [list]

---

**SECTION 3 -- Tailored Resume Bullets**

Generate 5-7 resume bullets tailored to this specific job. Follow these rules:

- Use strong action verbs (Built, Designed, Automated, Analyzed, Managed, Led, Developed)
- Quantify wherever possible using real numbers from his background
- Mirror the job description's language where accurate and honest
- Format: [Action verb] + [what was done] + [tool or method used] + [measurable result or scale]
- Bullets should be one line, concise, ATS-friendly
- Do NOT fabricate experience. Only use skills and projects he actually has.

Draw from these real projects and experiences when relevant:
- Google Apps Script dashboard for Border Angels consolidating metrics across multiple programs
  with dynamic filters, charts, and a multi-program sync pipeline
- Job hunting automation tool: Indeed/LinkedIn/Glassdoor/USAJobs scraper, Claude API scoring,
  Playwright auto-apply, Google Sheets logging, ntfy.sh notifications, cron weekday schedule
- Program management at The LEAGUE: curriculum development, instructor accountability tracking,
  parent progress reports, managing coding education programs
- GCP/BigQuery data work, Docker/Ansible infrastructure, Python scripting and automation
- Border Angels program coordination: volunteer management, data reporting, MOU and policy docs

---

**SECTION 4 -- Cover Letter**

Write a one-page cover letter. Follow this structure:

**Opening paragraph:** Name the role and company. State why this specific role and organization
interests Osvaldo -- be specific to the job description, not generic.

**Middle paragraph 1:** Connect 2-3 of his strongest technical skills directly to the job
requirements using a concrete example from his real experience.

**Middle paragraph 2:** Connect his program coordination and data reporting experience to the
role's organizational or analytical needs. Emphasize his ability to work across technical
and non-technical stakeholders.

**Closing paragraph:** Express genuine interest, reference the organization's mission if
applicable (especially for government or nonprofit roles), and include a clear call to action.

**Tone:** Professional but not stiff. Confident without being arrogant. Civic-minded when
writing for government or nonprofit employers. Direct and results-oriented for tech or
private sector roles.

**Length:** 3-4 paragraphs. Under 400 words. No filler phrases like "I am excited to apply"
or "I believe I would be a great fit."

---

**SECTION 5 -- Statement of Qualifications (SOQ)**

Generate this section only when:
- The job is a California state government role (CalCareers) OR
- The job posting explicitly asks for a Statement of Qualifications

The SOQ is a separate document from the cover letter. It is required by most California
state agencies and is used to screen candidates before interviews. It must directly address
the desirable qualifications or SOQ prompts listed in the job posting. If no specific
prompts are listed, address the top 3-4 desirable qualifications.

**Format and rules:**
- Address each qualification or prompt as a separate numbered section with a bold header
  matching the qualification exactly as written in the job posting
- Each section: 1-2 focused paragraphs, 100-200 words
- Use the STAR method (Situation, Task, Action, Result) for each response
- Be specific -- cite real projects, tools, outcomes, and numbers from Osvaldo's background
- Do not repeat the cover letter. The SOQ goes deeper on specific qualifications.
- Total length: 1-2 pages. No filler. No generic statements.
- Tone: formal, precise, California state government style -- professional and factual

**Experiences to draw from for SOQ responses:**
- Border Angels dashboard: consolidated multi-program metrics, built dynamic filters and
  charts, resolved UTC timezone bugs and Google Sheets auto-conversion issues in Apps Script
- The LEAGUE: instructor accountability tracking, parent progress reporting, curriculum
  design across multiple formats (Jekyll sites, MakeCode Arcade, AP CS A)
- Job hunter automation: end-to-end pipeline design, multi-source data integration, Claude
  API integration, automated logging and notifications
- GCP/BigQuery, Docker, Ansible, Python scripting, SQL data work
- Cross-functional communication with program staff, volunteers, and leadership
- Prior state government experience -- interviewed and negotiated with California state
  agencies at the AGPA level, received a Caltrans AGPA offer

---

## Notes for Claude

- Always read the full job description before scoring. Do not skim.
- If the job posting is a URL, ask the user to paste the text since you may not be able to
  fetch it directly.
- If the user pastes a job and says nothing else, run the full evaluation automatically.
- If the score is 7+, generate all five sections without being asked. For non-government
  roles with no SOQ requirement, note that Section 5 is skipped and why.
- For any CalCareers or California state government posting, always generate the SOQ.
  State jobs almost always require one even when the posting does not explicitly say so.
- Do not ask unnecessary clarifying questions if the job description is clear.
- If the user asks to improve or iterate on any document, do so without re-scoring unless
  the job description changed.
- If the user asks to "write my resume" without providing a job posting, generate a
  general one-page resume using his full background from the candidate profile above.
