# MASTER PROMPT — Implement and Improve KafAI UPKK UI/UX

Act as a **Senior Product Designer, UI/UX Lead, Frontend UX Engineer, Design Systems Expert, and EdTech Startup Product Designer**.

Your task is to inspect the existing KafAI UPKK application and transform its frontend into a polished, production-quality, responsive EdTech web application using the supplied UI references in `/screens`.

## Scope

Focus on **UI/UX and frontend implementation**.

Do not rewrite the AI/RAG/scoring architecture unless a small non-breaking integration change is required for the frontend.

Preserve current business logic and data flow wherever possible.

## Design source of truth

Review every image in `/screens` before changing the interface.

Treat the images as the intended visual and UX direction:

1. Landing page
2. Student dashboard
3. Fiqh subject page
4. Lesson/topic page
5. Practice/question page
6. AI processing state
7. Assessment result/feedback
8. Progress/history
9. Teacher dashboard/AI review

Maintain consistency across screens.

## Product goal

Transform KafAI UPKK from:

> an FYP prototype that works

into:

> a polished EdTech startup product that could be confidently demonstrated to founders, investors, schools, teachers and real users.

## UX principle

**Simple for students. Powerful for teachers. Impressive for stakeholders.**

## Primary web-app priority

Desktop/web is the main experience.

Design and validate:
- 1440px+ desktop
- 1280px laptop
- 768–1024px tablet
- 390px mobile
- 360px small mobile

Do not simply shrink the desktop UI.

### Desktop
Use a clean left sidebar and top navigation where appropriate.

### Tablet
Use a collapsible navigation pattern and simplified grid.

### Mobile
Use stacked cards and bottom navigation where appropriate.

No horizontal overflow.

## Before implementation

1. Inspect the repository and identify current UI architecture.
2. Run the app.
3. Capture current screenshots.
4. Map all current pages/routes/components.
5. Identify what already works and should be preserved.
6. Review all supplied UI reference images.
7. Create a concise implementation plan.

Do not stop at recommendations.

After planning, actually implement the interface.

## Design system

Create or consolidate a reusable design system based on the references.

### Visual personality
- deep emerald primary
- warm cream / soft neutral background
- dark navy/charcoal text
- warm gold/amber accent
- subtle shadows
- generous spacing
- rounded surfaces
- restrained Islamic educational motifs

Avoid:
- excessive gradients
- purple AI glow
- heavy glassmorphism
- random decorative shapes
- inconsistent icons
- too many dashboard widgets

### Typography
Use one modern sans-serif family consistently, such as:
- Inter
- Manrope
- Plus Jakarta Sans
- Geist

Ensure excellent Malay and Jawi rendering.

### Reusable components
At minimum create/reuse consistent:
- AppShell
- Sidebar
- TopBar
- MobileNavigation
- Breadcrumb
- PageHeader
- Button variants
- Input
- Textarea
- Select
- Tabs
- Badge
- Card
- SubjectCard
- TopicCard
- ProgressCard
- RecommendationCard
- QuestionCard
- ScoreCard
- FeedbackSection
- SourceCard
- ProgressBar
- EmptyState
- ErrorState
- LoadingState
- Modal / Drawer
- Toast
- DataTable
- MobileCardList
- Skeleton

## Required interfaces

### 1. Landing page
Reference: `screens/01_landing_page_responsive.png`

Must clearly explain:
- what KafAI UPKK is,
- who it is for,
- the learning problem,
- how it works,
- benefits for students,
- benefits for teachers,
- Tajwid/Fiqh/Jawi support,
- KAFA/UPKK alignment,
- strong CTA.

Primary message:
**Learn from every answer.**

### 2. Student dashboard
Reference: `screens/02_student_dashboard_responsive.png`

The dashboard must answer:
> What should I learn today?

Include:
- greeting
- continue learning
- personalised recommendation
- Tajwid / Fiqh / Jawi subject progress
- recent activity
- progress trend
- weak topics

Do not overload students with analytics.

### 3. Subject page
Reference: `screens/03_subject_fiqh_responsive.png`

Include:
- subject title and progress
- topic overview
- topic mastery
- Start / Continue / Review states
- recommended topic
- weak topics
- completed topics

### 4. Lesson/topic page
Reference: `screens/04_lesson_syarat_sah_solat_responsive.png`

Include:
- breadcrumb
- concept overview
- key points
- example
- KAFA source/reference
- topic progress/mastery
- next lesson
- strong CTA: **Practice This Topic**

On mobile, use progressive disclosure / accordion sections if useful.

### 5. Practice/question page
Reference: `screens/05_practice_question_responsive.png`

This screen must be distraction-free.

Include:
- back navigation
- subject/topic indicators
- question number
- total question progress
- marks
- question text
- answer textarea
- optional hint
- character count
- primary CTA: **Submit Answer**

### 6. AI processing/loading
Reference: `screens/06_ai_processing_loading_responsive.png`

Never show a frozen interface.

Use understandable status language such as:
- Reading your answer
- Checking your KAFA lesson
- Preparing your feedback

Do not expose technical model/RAG terminology.

Do not use fake progress if backend progress is unknown. Use a truthful indeterminate state where necessary.

### 7. Assessment result/feedback
Reference: `screens/07_assessment_feedback_responsive.png`

This is the highest-priority screen.

The information hierarchy must be:

**RESULT → EXPLANATION → ACTION**

Include:
- score
- status such as Partially Correct
- What you did well
- What needs improvement
- Why?
- Correct Understanding
- Based on your KAFA lesson
- Your Next Step
- Practice Again
- Review Lesson
- Next Question

Feedback must be concise and easy for Year 4/5 students.

Use progressive disclosure on small screens.

### 8. Progress & history
Reference: `screens/08_progress_history_responsive.png`

Include:
- overall progress
- Tajwid / Fiqh / Jawi mastery
- learning trend
- weak topics
- recommended next topic
- recent attempts / history

Every metric must help the learner decide what to do next.

### 9. Teacher dashboard + AI review
Reference: `screens/09_teacher_dashboard_ai_review_responsive.png`

Teacher UI should be more professional and information-dense than student UI.

Include:
- class overview
- students needing attention
- common weak topics
- recent activity
- student list
- assessment review panel
- student's answer
- AI score
- rubric summary
- source/criteria if available
- teacher controls:
  - Approve
  - Edit Feedback
  - Change Score

Teacher must retain final authority.

## Accessibility

Target WCAG 2.2 AA.

Validate:
- contrast
- keyboard navigation
- visible focus
- semantic heading order
- form labels
- touch targets
- zoom
- screen reader-friendly labels
- reduced motion

## Jawi / RTL

Explicitly test:
- Jawi input
- RTL alignment
- mixed Malay + Jawi
- wrapping
- punctuation
- compatible fonts

Do not allow Jawi to break layouts.

## UX writing

Use simple, supportive language.

Avoid technical text.

Examples:

Bad:
“Retrieval completed successfully.”

Good:
“Checked with your KAFA lesson.”

Bad:
“Incorrect response.”

Good:
“Almost there. Let’s fix one part.”

## Loading, empty and error states

Every important view must include:
- loading
- empty
- success
- error
- disabled state where relevant

Never expose raw stack traces or backend errors.

Example:

**We couldn’t check your answer.**  
Your answer is safe. Please try again.

## Interaction quality

Use subtle:
- hover states
- focus states
- card interactions
- progress transitions
- skeletons

Avoid excessive motion.

## Implementation rules

1. Reuse components instead of duplicating styles.
2. Keep layout consistent with the supplied mockups.
3. Preserve current functional flows.
4. Do not invent backend capabilities that do not exist.
5. If a mockup shows a feature not currently implemented, mark it clearly as:
   - UI-ready / backend pending
   rather than faking functionality.
6. Keep desktop as the primary target while ensuring tablet/mobile responsiveness.
7. Do not rebuild the entire app in a new framework unless the current framework makes the target UI genuinely impossible. If migration is necessary, explain the exact blocker first.

## Testing

After implementation:

1. Run the app.
2. Test every major route.
3. Test 1440px, 1280px, tablet, 390px, 360px.
4. Test empty/loading/error states.
5. Test keyboard navigation.
6. Test Jawi and Malay text rendering.
7. Capture final screenshots.
8. Compare them side-by-side with `/screens` references.
9. Fix visible inconsistencies.

## Required output files

Create/update:

`docs/uiux/UIUX_IMPROVEMENT_REPORT.md`

Include:
- original UI issues
- improvements made
- design-system decisions
- screen-by-screen changes
- responsive strategy
- accessibility notes
- remaining gaps
- features shown in UI but awaiting backend support
- files changed

Also provide a concise final summary with:
- interfaces completed
- reusable components created
- desktop/tablet/mobile status
- remaining blockers
- final UI/UX readiness score /100

## Final quality test

Before finishing, ask:

> If someone saw KafAI UPKK without knowing it was an FYP, would they believe it is a real EdTech startup product?

If the answer is no, continue improving the interface.
