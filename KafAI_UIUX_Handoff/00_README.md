# KafAI UPKK UI/UX — Claude Handoff Package

This folder contains the complete responsive UI/UX design direction for **KafAI UPKK**, an AI-powered KAFA learning assistant for Year 4 and Year 5 students preparing for UPKK.

## What is included

### Responsive interface references

1. `screens/01_landing_page_responsive.png`
   - Marketing / startup landing page
   - Desktop + tablet + mobile

2. `screens/02_student_dashboard_responsive.png`
   - Main student dashboard
   - Continue learning, recommendations, subjects, progress, weak topics

3. `screens/03_subject_fiqh_responsive.png`
   - Fiqh subject overview
   - Subject progress, topic cards, weak/completed/recommended topics

4. `screens/04_lesson_syarat_sah_solat_responsive.png`
   - Lesson / topic page
   - Concept overview, key points, source/KAFA note, progress, mastery, CTA

5. `screens/05_practice_question_responsive.png`
   - Focused assessment/question page
   - Question progress, marks, answer field, hint, submit

6. `screens/06_ai_processing_loading_responsive.png`
   - AI answer-processing state
   - Reading answer → checking KAFA lesson → preparing feedback

7. `screens/07_assessment_feedback_responsive.png`
   - Assessment result / feedback page
   - Score, strengths, improvements, why, correct understanding, source, next action

8. `screens/08_progress_history_responsive.png`
   - Student progress & learning history
   - Subject mastery, weak topics, recommendation, trend and past attempts

9. `screens/09_teacher_dashboard_ai_review_responsive.png`
   - Teacher dashboard + AI assessment review
   - Class insights, weak topics, student attention, rubric review, approve/edit/change score

## Visual direction

- Premium but friendly EdTech startup
- Deep emerald green as the primary brand colour
- Warm cream / soft neutral surfaces
- Gold/amber as secondary accent
- Modern rounded sans-serif typography
- Rounded cards and soft shadows
- Clean hierarchy and generous spacing
- Subtle Islamic/KAFA identity, not an event-poster aesthetic
- Student-friendly without becoming childish
- Strong web-app experience first, then tablet/mobile adaptation

## Product principle

**Simple for students. Powerful for teachers. Impressive for stakeholders.**

## Main product promise

**Learn from every answer.**

KafAI UPKK should help a student understand:
1. What was correct?
2. What was wrong?
3. Why was it wrong?
4. What is the correct understanding?
5. What should I do next?

## Use with Claude

Open this folder at the root of the project and give Claude the prompt in:

`02_MASTER_UIUX_IMPLEMENTATION_PROMPT.md`

Tell Claude the images in `/screens` are the design references and should be treated as the target visual direction.
