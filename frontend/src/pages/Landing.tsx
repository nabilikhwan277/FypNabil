import { motion } from 'framer-motion'
import {
  ArrowRight,
  BookOpen,
  BookOpenCheck,
  CircleCheck,
  Lightbulb,
  Play,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Logo'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import ScriptToggle from '../components/ScriptToggle'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_ORDER, SUBJECT_STYLE } from '../components/subjects'
import Bi from '../components/Bi'
import T from '../components/T'
import ThemeToggle from '../components/ThemeToggle'
import type { StringKey } from '../i18n/strings'

const SUBJECT_NAMES = {
  fiqh: { rumi: 'Ibadah', jawi: 'عبادة' },
  jawi: { rumi: 'Jawi', jawi: 'جاوي' },
  tajwid: { rumi: 'Tajwid', jawi: 'تجويد' },
} as const

const STEPS: { icon: LucideIcon; title: StringKey; desc: StringKey }[] = [
  { icon: BookOpen, title: 'howLearn', desc: 'howLearnDesc' },
  { icon: Target, title: 'howPractice', desc: 'howPracticeDesc' },
  { icon: Lightbulb, title: 'howUnderstand', desc: 'howUnderstandDesc' },
  { icon: TrendingUp, title: 'howImprove', desc: 'howImproveDesc' },
]

const FOR_PUPILS: StringKey[] = ['benefitS1', 'benefitS2', 'benefitS3', 'benefitS4']
const FOR_TEACHERS: StringKey[] = ['benefitT1', 'benefitT2', 'benefitT3']

const NAV: { href: string; label: StringKey }[] = [
  { href: '#masalah', label: 'navFeatures' },
  { href: '#cara', label: 'navHow' },
  { href: '#subjek', label: 'navSubjects' },
  { href: '#guru', label: 'forTeachers' },
]

/** Public introduction page (no sign-in needed): what KafAI is, who it is for and how it works. */
export default function Landing() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/85 backdrop-blur-md">
        <div className="mx-auto flex h-18 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <Link to="/landing" className="rounded-xl">
            <Brand size={40} />
          </Link>
          <nav aria-label="KafAI" className="ms-6 hidden items-center gap-1 lg:flex">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} className="rounded-full px-3 py-2 text-sm font-semibold text-ink-2 transition hover:bg-surface-2 hover:text-ink">
                <T k={n.label} />
              </a>
            ))}
          </nav>
          <div className="ms-auto flex items-center gap-2">
            <ScriptToggle compact className="max-sm:hidden" />
            <ThemeToggle className="max-sm:hidden" />
            <Link to="/login" className="btn-primary min-h-11 rounded-full px-5 text-sm whitespace-nowrap">
              <T k="landingStart" /> <ArrowRight aria-hidden="true" className="h-4 w-4 rtl:-scale-x-100" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-10 pb-16 sm:px-6 md:grid-cols-[1.05fr_1fr] md:pt-16">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-4xl leading-[1.08] font-extrabold tracking-tight text-ink sm:text-[3.4rem]">
              <T k="heroTitle1" /> <span className="relative inline-block whitespace-nowrap">
                <T k="heroTitle2" />
                <svg aria-hidden="true" viewBox="0 0 200 12" preserveAspectRatio="none" className="absolute -bottom-2 start-0 h-3 w-full text-gold">
                  <path d="M3 9 C 50 3, 150 3, 197 8" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
                </svg>
              </span>
            </h1>
            <T k="heroSub" as="p" className="mt-6 max-w-xl text-lg text-ink-2" />
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/login" className="btn-primary min-h-13 rounded-full px-7 text-base">
                <T k="landingStart" /> <ArrowRight aria-hidden="true" className="h-4.5 w-4.5 rtl:-scale-x-100" />
              </Link>
              <a href="#cara" className="btn-secondary min-h-13 rounded-full px-6 text-base">
                <Play aria-hidden="true" className="h-4 w-4 fill-current text-primary-ink" /> <T k="seeHow" />
              </a>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-ink-2">
              {(
                [
                  [CircleCheck, 'chipKafa'],
                  [BookOpenCheck, 'chipUpkk'],
                  [Sparkles, 'chipPowered'],
                ] as const
              ).map(([Icon, k]) => (
                <li key={k} className="flex items-center gap-2">
                  <Icon aria-hidden="true" className="h-4.5 w-4.5 text-primary-ink" /> <T k={k} />
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.15 }} className="relative">
            <div className="relative overflow-hidden rounded-[2rem] bg-linear-to-br from-brand-2 to-brand p-3 shadow-lg">
              <MosqueScene className="absolute inset-x-0 bottom-0 w-full text-white/10" />
              <img src="/hero_children.jpg" alt="" className="relative aspect-[4/3] w-full rounded-[1.5rem] bg-white object-contain" />
            </div>
            {/* Illustration of the feedback a pupil gets (sample, not real data) */}
            <div aria-hidden="true" className="absolute -bottom-8 -start-3 w-60 rounded-2xl border border-line bg-surface p-4 shadow-lg sm:-start-8">
              <p className="flex items-center gap-2 text-xs font-bold text-ink-3">
                <Sparkles className="h-4 w-4 text-gold-ink" /> <T k="yourScore" />
              </p>
              <p className="mt-1 flex items-center gap-2">
                <span className="text-2xl font-extrabold text-ink">4 / 5</span>
                <span className="rounded-full bg-gold px-2.5 py-0.5 text-xs font-bold text-on-gold">
                  <T k="resultTitle2" />
                </span>
              </p>
              <p className="mt-2 flex items-start gap-1.5 text-xs text-ink-2">
                <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" /> <T k="howUnderstandDesc" />
              </p>
            </div>
            <div aria-hidden="true" className="absolute -top-8 -end-2 flex items-end gap-1 sm:-end-6">
              <p className="mb-10 rounded-2xl border border-line bg-surface px-3 py-1.5 text-sm font-bold text-ink shadow-md">
                <T k="homeGreeting" />!
              </p>
              <Mascot mood="wave" size={92} className="drop-shadow-xl" />
            </div>
          </motion.div>
        </section>

        {/* Problem and solution */}
        <section id="masalah" aria-label="KafAI" className="mx-auto grid max-w-6xl scroll-mt-24 gap-5 px-4 sm:px-6 md:grid-cols-2">
          <div className="card flex gap-4 bg-surface-2">
            <span aria-hidden="true" className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-danger-soft text-danger-ink">
              <Target className="h-6 w-6" />
            </span>
            <div>
              <T k="problemTitle" as="h2" className="text-xl font-extrabold text-ink" />
              <T k="problemText" as="p" className="mt-1 text-ink-2" />
            </div>
          </div>
          <div className="card-brand flex gap-4">
            <MosqueScene className="pointer-events-none absolute -end-4 bottom-0 w-56 text-white/[0.08]" />
            <span aria-hidden="true" className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gold text-on-gold">
              <Lightbulb className="h-6 w-6" />
            </span>
            <div className="relative">
              <T k="solutionTitle" as="h2" className="text-xl font-extrabold" />
              <T k="solutionText" as="p" className="mt-1 text-on-brand-2" />
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="cara" aria-labelledby="landing-how" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-16 sm:px-6">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <T k="howTitle" as="h2" id="landing-how" className="text-3xl font-extrabold text-ink" />
            <T k="howSub" as="p" className="text-ink-3" />
          </div>
          <ol className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="card relative flex flex-col gap-3">
                <span className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-extrabold text-on-primary">{i + 1}</span>
                  <s.icon aria-hidden="true" className="h-7 w-7 text-gold-ink" />
                </span>
                <T k={s.title} as="h3" className="text-lg font-extrabold text-ink" />
                <T k={s.desc} as="p" className="text-sm text-ink-2" />
              </li>
            ))}
          </ol>
        </section>

        {/* Benefits */}
        <section id="guru" aria-label="KafAI" className="mx-auto grid max-w-6xl scroll-mt-24 gap-5 px-4 sm:px-6 md:grid-cols-2">
          <div className="card flex flex-col gap-4 sm:flex-row sm:items-start">
            <Mascot mood="happy" size={88} className="shrink-0 drop-shadow-md" />
            <div>
              <T k="forPupils" as="h2" className="text-xl font-extrabold text-ink" />
              <ul className="mt-3 flex flex-col gap-2">
                {FOR_PUPILS.map((k) => (
                  <li key={k} className="flex items-start gap-2 text-ink-2">
                    <CircleCheck aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-primary" /> <T k={k} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="card flex flex-col gap-4 sm:flex-row sm:items-start">
            <span aria-hidden="true" className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-gold-soft text-5xl">
              🧕
            </span>
            <div>
              <T k="forTeachers" as="h2" className="text-xl font-extrabold text-ink" />
              <ul className="mt-3 flex flex-col gap-2">
                {FOR_TEACHERS.map((k) => (
                  <li key={k} className="flex items-start gap-2 text-ink-2">
                    <CircleCheck aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-gold-ink" /> <T k={k} />
                  </li>
                ))}
                <li className="flex items-start gap-2 text-ink-3">
                  <Sparkles aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
                  <span>
                    <T k="benefitT4" /> <span className="chip ms-1 py-0 text-xs">
                      <T k="comingSoon" />
                    </span>
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* Subjects and alignment */}
        <section id="subjek" aria-labelledby="landing-subjects" className="mx-auto grid max-w-6xl scroll-mt-24 gap-5 px-4 py-16 sm:px-6 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <T k="chooseSubject" as="h2" id="landing-subjects" className="text-3xl font-extrabold text-ink" />
            <ul className="mt-6 grid gap-4 sm:grid-cols-3">
              {SUBJECT_ORDER.map((id) => (
                <li key={id} className="card flex flex-col gap-3 p-5">
                  <SubjectIcon id={id} size="lg" />
                  <Bi rumi={SUBJECT_NAMES[id].rumi} jawi={SUBJECT_NAMES[id].jawi} as="h3" className="text-lg font-extrabold text-ink" />
                  <T k={SUBJECT_STYLE[id].desc} as="p" className="text-sm text-ink-2" />
                </li>
              ))}
            </ul>
          </div>
          <div className="card flex flex-col justify-center gap-4 self-end bg-surface-2">
            <span aria-hidden="true" className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-soft text-primary-ink">
              <ShieldCheck className="h-6 w-6" />
            </span>
            <T k="alignedTitle" as="h2" className="text-xl font-extrabold text-ink" />
            <T k="alignedSub" as="p" className="-mt-2 text-ink-2" />
            <ul className="flex flex-wrap gap-2">
              {(['chipTextbook', 'chipSyllabus', 'chipScript'] as const).map((k) => (
                <li key={k} className="chip bg-surface">
                  <CircleCheck aria-hidden="true" className="h-4 w-4 text-primary" /> <T k={k} />
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Call to action */}
        <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
          <div className="card-brand flex flex-col items-center gap-5 px-6 py-10 text-center sm:flex-row sm:text-start">
            <MosqueScene className="pointer-events-none absolute inset-x-0 bottom-0 w-full text-white/[0.07]" />
            <Mascot mood="celebrate" size={96} className="relative shrink-0" />
            <div className="relative flex-1">
              <T k="ctaTitle" as="p" className="text-2xl font-extrabold" />
              <T k="ctaSub" as="p" className="mt-1 text-on-brand-2" />
            </div>
            <Link to="/login" className="btn-gold relative min-h-13 rounded-full px-7">
              <T k="landingStart" /> <ArrowRight aria-hidden="true" className="h-4.5 w-4.5 rtl:-scale-x-100" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 px-4 text-center text-sm text-ink-3 sm:flex-row sm:justify-between sm:px-6 sm:text-start">
          <Brand size={32} tagline={false} />
          <T k="landingFooter" />
        </div>
      </footer>
    </div>
  )
}
