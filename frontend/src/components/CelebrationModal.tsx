import { motion } from 'framer-motion'
import { BADGES } from '../i18n/strings'
import type { RankInfo } from '../lib/rank'
import Bi from './Bi'
import Confetti from './Confetti'
import Mascot from './Mascot'
import Modal from './Modal'
import T from './T'
import { Arrow } from './ui'

export interface Celebration {
  rank: RankInfo | null
  level: number | null
  badges: string[]
}

const item = (i: number) => ({
  initial: { opacity: 0, scale: 0.8 },
  animate: { opacity: 1, scale: 1 },
  transition: { delay: 0.3 + i * 0.15, type: 'spring' as const, stiffness: 260, damping: 16 },
})

/** "Hebat!" dialog for a new rank, an unlocked level or new badges. */
export default function CelebrationModal({ open, data, onClose }: { open: boolean; data: Celebration | null; onClose: () => void }) {
  let i = 0
  return (
    <Modal open={open && data !== null} onClose={onClose} labelledBy="celebrate-title" decor={<Confetti count={70} />}>
      {data && (
        <>
          <Mascot mood="celebrate" size={120} className="mx-auto" />
          <T k="wow" as="h2" id="celebrate-title" className="mt-1 text-4xl font-black text-primary-ink" />
          <ul className="mt-4 flex flex-col gap-3 text-start">
            {data.rank && (
              <motion.li {...item(i++)} className="flex items-center gap-3 rounded-2xl border border-accent/40 bg-accent-soft p-3 text-ink">
                <span aria-hidden="true" className="text-4xl">
                  {data.rank.emoji}
                </span>
                <span className="min-w-0">
                  <T k="newRank" className="block text-sm font-extrabold text-accent-ink" />
                  <Bi rumi={data.rank.rumi} jawi={data.rank.jawi} className="block text-xl font-black text-ink" />
                </span>
              </motion.li>
            )}
            {data.level !== null && (
              <motion.li {...item(i++)} className="flex items-center gap-3 rounded-2xl border border-primary/30 bg-primary-soft p-3 text-ink">
                <span aria-hidden="true" className="text-4xl">
                  🔓
                </span>
                <span className="min-w-0">
                  <T k="levelUnlocked" className="block text-sm font-extrabold text-primary-ink" />
                  <span className="block text-xl font-black text-ink">
                    <T k="level" /> {data.level}
                  </span>
                </span>
              </motion.li>
            )}
            {data.badges.map((b) => (
              <motion.li key={b} {...item(i++)} className="flex items-center gap-3 rounded-2xl border border-info-ink/30 bg-info-soft p-3 text-ink">
                <span aria-hidden="true" className="text-4xl">
                  {BADGES[b]?.emoji ?? '🏅'}
                </span>
                <span className="min-w-0">
                  <T k="newBadge" className="block text-sm font-extrabold text-info-ink" />
                  <Bi rumi={BADGES[b]?.rumi ?? b} jawi={BADGES[b]?.jawi} className="block text-xl font-black text-ink" />
                </span>
              </motion.li>
            ))}
          </ul>
          <button type="button" onClick={onClose} className="btn-primary mt-5 w-full">
            <T k="continue" /> <Arrow />
          </button>
        </>
      )}
    </Modal>
  )
}
