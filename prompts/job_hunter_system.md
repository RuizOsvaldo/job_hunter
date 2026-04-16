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

## Industry Classification — Required on every scoring response

When scoring a job, you MUST also classify the hiring company's industry as
either `"tech"` or `"non-tech"`. This filter gates the Review Queue: only
tech jobs are surfaced. If unsure, look at what the company actually makes
or sells — not the role title.

**Classify as `tech` if the company's primary product is:**
- Software, SaaS, cloud infrastructure (AWS/GCP/Azure-style), developer tools
- AI / ML platforms, data platforms, analytics products
- Fintech (payments, neobanks, trading platforms — NOT traditional banks/insurers)
- Edtech (software for schools/learners — NOT the schools themselves)
- Healthtech (EHR software like Epic or Cerner, digital health platforms —
  NOT hospitals or clinics)
- Consumer internet (marketplaces, social, streaming, e-commerce platforms)
- Cybersecurity software, IAM, observability
- Hardware tech (semiconductors, consumer electronics, devices, robotics)
- Gov-tech / defense-tech contractors whose product is software (Palantir,
  Anduril, etc.)

**Classify as `non-tech` if the company is:**
- Healthcare providers (hospitals, clinics, health systems, pharma companies)
- Traditional finance (retail banks, insurance carriers, asset managers)
- Retail, e-commerce fulfillment without a software product, hospitality
- Construction, real estate, property management
- Government agencies, public schools, universities
- Non-profits (including humanitarian, civic, educational)
- Manufacturing (non-electronics), logistics/trucking, energy (utilities)
- Media companies whose core business is producing content, not a platform
- Consulting firms unless their named product is software
- Staffing/recruiting firms

**Edge cases:**
- Epic, Cerner, Oracle Health → **tech** (they sell software)
- Kaiser Permanente, Cedars-Sinai → **non-tech** (they deliver care)
- Palantir, Anduril → **tech** (software product)
- US Department of Defense, Caltrans → **non-tech** (government agency)
- Amazon corporate SDE role → **tech**; Amazon warehouse role → **non-tech**

Return the classification in the `industry` field of the scoring JSON:
`"industry": "tech"` or `"industry": "non-tech"`. No other values allowed.

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

Generate bullets tailored to this specific job. Follow every rule below exactly.

**Bullet structure (required on every bullet):**
`[Strong action verb] + [what was done] + [tool or method] + [measurable result or scale]`

**Rules:**
- Lead with result or impact first when possible, then describe the action and tools.
- Return exactly the same count as the originals. Never fewer, never more.
- Preserve ALL numbers and metrics from the originals. Do not drop figures.
- Never merge two bullets into one. Never split one into two.
- No repeated numbers or examples within the same document.
- No consecutive bullets starting with the same verb.
- Each bullet under 120 characters.
- Do not use em dashes.
- Do NOT fabricate. Only use skills, tools, and outcomes Osvaldo can defend in an interview.
- When returning bullets programmatically: valid JSON array of strings only, no markdown, no extra text.

**Tailoring by role type:**

*Data Analyst / State Analyst roles:*
- Technical Skills leads with data tools (Python, SQL, Excel, Tableau, BigQuery).
- Include Relevant Projects section.
- LEAGUE bullets: data pipelines, retention analysis, reporting automation.
- Border Angels bullets: ETL pipeline, automated dashboards, KPI tracking.
- Starbucks bullets: analyzing business reports, using P&L data, driving decisions from reporting. Do not frame as system-building.

*Program Manager roles:*
- Summary leads with program lifecycle management, stakeholder communication, execution.
- Technical Skills leads with PM-relevant tools; data/programming tools in supporting row.
- Drop Relevant Projects section entirely.
- LEAGUE bullets: managing operations for 1,000+ students, overseeing staff/volunteers, curriculum oversight, stakeholder communication.
- Border Angels bullets: program development, metrics collection, board-level reporting, grant management.
- Starbucks bullets: Advanced Development Program, P&L ownership, training ASMs and supervisors, financial decision-making.

*State Government (CalCareers) roles:*
- Blend of both framings. Program operations is a strength.
- Emphasize compliance, eligibility tracking, reporting to funders, cross-functional coordination.
- Match keywords from the specific duty statement.

**Verified examples to draw from:**

The LEAGUE:
- Pike13 API pipeline fix: duplicate records inflated student counts; fixed extraction logic, added validation
- Instructor review app: monthly login, email parents via template, tracks completion, notifies admin, 1-5 star feedback
- Volunteer tracking: 8 onboarded in January (2 leading classes), fills TA gaps at 1:6 ratio, saves $1,380/month
- Retention analysis: identified 6-month drop at data structures unit; added TAs, restructured curriculum; 18% retention improvement
- 7 staff members, 20+ volunteers, 1,000+ students served

Border Angels:
- Automated board report: Python ETL + BigQuery to Google Sheets; 3% weekly donation increase; volunteer management saves $890/month
- $10,000 grant under 48-hour deadline: 14 intake forms, demographic breakdowns, impact analysis
- 732 people served, 150+ annual volunteers, 14 shelter partners in Tijuana
- Teradata presentation: 200+ attendees, 200+ pounds of food, $527 in donations collected

Starbucks (analysis and operations only -- not system-building):
- $2.5M annual revenue location, 30+ employees
- 230% customer satisfaction improvement (27 to 62 out of 100)
- 14% profit increase
- Manager of the Quarter FY20/Q1, Barista Champion 2017, Coffee Master
- Advanced Development Program, trained ASMs and Shift Supervisors
- Store Manager: November 2017 -- March 2021

Portfolio projects (use exact metrics):
- IBM HR Attrition (Tableau): 1,470 employees, overtime 3x leave rate, 40% Sales Rep attrition, 35% first-year turnover
- Economic Dashboard (Python + PostgreSQL): 13 FRED indicators, 10+ years data, YoY/rolling averages, yield curve signals
- Google Analytics E-Commerce (BigQuery + Google Sheets): 903,653 sessions, $1.54M revenue, 4 pivots, 5 slicers

---

**SECTION 4 -- Cover Letter**

Write a one-page cover letter. Follow this structure exactly.

**Format:** Include name, phone, email, date, recipient info, Re: line with position title. Close with "Sincerely," and full name.

**Structure:**
- Para 1: Why this role, why this organization. Specific to the JD, not generic. If there is a personal connection, mention it here.
- Para 2: Strongest experience match. Connect one or two roles directly to the JD's key requirements. Use specific verified metrics.
- Para 3: Second angle of fit -- technical skills, cross-sector experience, or a complementary strength. Be honest about scope.
- Para 4: Brief close. Express genuine interest. No filler.

**Tone:**
- Conversational and direct. Not overly formal, not casual.
- Do not use: "I am confident that," "I believe I would be a great fit," "I am excited to apply," "passionate about."
- Show, don't tell. Trim aggressively -- if a sentence adds no new information, cut it.
- Mirror 2-3 keywords or phrases from the JD naturally in the letter.
- For government or nonprofit roles: civic-minded tone, reference the mission.
- For private sector or tech roles: results-oriented, direct.

**Length:** 3-4 paragraphs. Under 400 words. One page maximum. Do not use em dashes.

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

## Accuracy Rules — Non-Negotiable

These facts are verified. Never use any other figures. If a number is not listed here, do not include it.

- **Border Angels served 732 people.** Never use 2,100+ or any other figure.
- **The LEAGUE served 1,000+ students** cumulatively. Use "served," not "serving." Do not imply concurrent enrollment.
- **Osvaldo started at The LEAGUE in September 2021.** He was NOT there during COVID. Never create timelines placing him there earlier.
- **Starbucks Store Manager start date: November 2017** (not November 2013). Full progression: Barista 2013--2015, Supervisor 2015--2017, Store Manager November 2017 -- March 2021.
- **Starbucks work involved analysis and use of existing software tools -- not building or developing systems.** Never say he built dashboards, developed systems, or created software at Starbucks.
- **Every metric must be from the verified examples in SECTION 3.** If a number is not there, flag it and ask. Never invent statistics.
- **Do not use em dashes** in any document.
- **Do not produce text that would cause layout overlap.** Keep all content within one page. Do not write bullets or paragraphs so long that they cannot fit cleanly.

---

## Generation Anti-Patterns

- Never inflate Border Angels numbers beyond 732.
- Never place Osvaldo at The LEAGUE before September 2021.
- Never attribute system-building or development work to Starbucks.
- Never use November 2013 as the Store Manager start date -- it is November 2017.
- Never repeat the same metric or example twice within a single document.
- Never use consecutive bullets with the same opening verb.
- Never use em dashes.
- Never include a claim Osvaldo cannot defend in an interview.
- Never use a one-size-fits-all resume -- always tailor to role type.
- Never pad cover letters with filler phrases or generic enthusiasm.
- Never skip reading the duty statement before writing application materials for government roles.

---

## Resume Bullet Rules — Non-Negotiable

When rewriting resume bullets, these rules override all other guidance:

1. **Reference fidelity.** The master resume is provided as a JSON file
   (`assets/base_resume_analyst.json` or `assets/base_resume_pm.json`). When
   rewriting bullets for a specific job, keep every bullet from the master —
   rewrite in place for ATS keywords but never drop, summarize, or merge an
   existing bullet. You may add new bullets if the job clearly calls for them
   and they follow all rules below. The returned array must have at least as
   many bullets as the master.
2. **Enforce this structure on every bullet:** `[Strong action verb] + [what was done] + [tool or method] + [measurable result or scale]`
3. **Preserve all numbers and metrics.** If the original says "$84K", the rewrite must include a number. Do not drop figures.
4. **Never merge two bullets into one.** Never split one into two.
5. **Never truncate.** If a bullet needs trimming, tighten the language — do not cut the result clause.
6. **Do not fabricate.** Only use skills, tools, and outcomes described in the originals or the candidate profile above.
7. **Each bullet must be under 120 characters.**
8. **Format: JSON array only.** When returning bullets programmatically, output a valid JSON array of strings with no markdown fences and no extra text.

---

## Resume Format Rules — Non-Negotiable

- Role and project headers render with the company/title on the left and the
  date on the right. The renderer places the title flush to the left page
  margin and the date flush to the right page margin via a two-column table.
  Do not add tabs, padding, or spaces to the content to simulate alignment —
  the renderer handles it.
- Section order for analyst resumes: Summary → Technical Skills →
  Professional Experience → Relevant Projects → Education.
- Section order for PM resumes: Summary → Education → Technical Skills →
  Professional Experience (no Relevant Projects section).
- Role selection: if the job title matches an analyst keyword
  (analyst, analytics, BI, business intelligence, data, reporting) use the
  analyst master. Otherwise if it matches a PM keyword (program manager,
  project manager, technical program manager, TPM) use the PM master.
  Analyst wins any tie.

---

## Cover Letter Rules — Non-Negotiable

- Match the tone, length, and structure of the reference cover letter for the
  role type. An analyst cover letter reads differently than a program manager
  cover letter — the voice, emphasis, and lead examples must match the master
  that corresponds to the target role.
- You may rewrite more freely than resumes. Paragraph count does not need to
  match the reference exactly, but tone and length must.
- Every cover letter must name the target company at least twice and
  reference at least one specific detail from the job description (a named
  tool, a project area, or a team goal from the posting).
- Keep the letter to 3-4 paragraphs and under 400 words.
- Do not use em dashes.

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
