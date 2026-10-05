// UI strings in Rumi and Jawi. Add new keys here; both scripts are required.
export type Script = 'rumi' | 'jawi'

export const APP_NAME = 'Intelligent KAFA UPKK Learning Assistant'

export const STRINGS = {
  // brand (a proper name: kept in English in both scripts)
  appName: { rumi: APP_NAME, jawi: APP_NAME },
  appLine1: { rumi: 'Intelligent KAFA UPKK', jawi: 'Intelligent KAFA UPKK' },
  appLine2: { rumi: 'Learning Assistant', jawi: 'Learning Assistant' },
  tagline: { rumi: 'Kawan belajar Ibadah, Jawi & Tajwid untuk UPKK', jawi: 'كاون بلاجر عبادة، جاوي & تجويد اونتوق UPKK' },
  mascotName: { rumi: 'Bulan', jawi: 'بولن' },

  chooseSubject: { rumi: 'Pilih subjek', jawi: 'ڤيليه سوبجيك' },
  ibadahDesc: { rumi: 'Solat sunat & puasa', jawi: 'صلاة سنة & ڤواسا' },
  jawiDesc: { rumi: 'Imbuhan, kata pinjaman & akronim', jawi: 'ايمبوهن، كات ڤينجمن & اكرونيم' },
  tajwidDesc: { rumi: "Mad, waqaf & ibtida'", jawi: 'مد، وقف & إبتداء' },
  switchScript: { rumi: 'Tukar ke Jawi', jawi: 'توكر ك رومي' },
  serverOnline: { rumi: 'Sedia', jawi: 'سديا' },
  serverOffline: { rumi: 'Pelayan belum dihidupkan', jawi: 'ڤلاين بلوم دهيدوڤكن' },
  serverWarming: { rumi: 'AI sedang bersedia…', jawi: 'AI سدڠ برسديا…' },

  // nav
  navMap: { rumi: 'Peta', jawi: 'ڤتا' },
  navProgress: { rumi: 'Kemajuan Saya', jawi: 'كماجوان ساي' },
  logout: { rumi: 'Keluar', jawi: 'كلوار' },
  back: { rumi: 'Kembali', jawi: 'كمبالي' },
  sound: { rumi: 'Bunyi', jawi: 'بوڽي' },
  soundOn: { rumi: 'Bunyi hidup', jawi: 'بوڽي هيدوڤ' },
  soundOff: { rumi: 'Bunyi dimatikan', jawi: 'بوڽي دماتيكن' },
  close: { rumi: 'Tutup', jawi: 'توتوڤ' },
  mainMenu: { rumi: 'Menu utama', jawi: 'مينو اوتام' },
  skipToContent: { rumi: 'Langkau ke kandungan', jawi: 'لڠكاو ك كندوڠن' },
  days: { rumi: 'hari', jawi: 'هاري' },

  // login
  loginBubble: {
    rumi: 'Assalamualaikum! Saya Bulan, kawan belajar kamu. Siapa nama kamu?',
    jawi: 'السلام عليكم! ساي بولن، كاون بلاجر كامو. سياڤ نام كامو؟',
  },
  welcome: { rumi: 'Assalamualaikum! Siapa nama kamu?', jawi: 'السلام عليكم! سياڤ نام كامو؟' },
  name: { rumi: 'Nama', jawi: 'نام' },
  kelas: { rumi: 'Kelas', jawi: 'كلس' },
  kelasHint: { rumi: 'Contoh: 5 Bestari', jawi: 'چونتوه: 5 بستاري' },
  chooseAvatar: { rumi: 'Pilih watak kamu', jawi: 'ڤيليه وتق كامو' },
  start: { rumi: 'Mula!', jawi: 'مولا!' },
  loginNote: {
    rumi: 'Prototaip: nama dan kelas sahaja, tiada kata laluan.',
    jawi: 'ڤروتوتاءيڤ: نام دان كلس سهاج، تياد كات لالوان.',
  },

  // home
  homeGreeting: { rumi: 'Assalamualaikum', jawi: 'السلام عليكم' },
  homeCheer: {
    rumi: 'Jom kumpul bintang hari ini! Pilih satu subjek untuk mula.',
    jawi: 'جوم كومڤول بينتڠ هاري اين! ڤيليه ساتو سوبجيك اونتوق مولا.',
  },
  continueLearning: { rumi: 'Sambung belajar', jawi: 'سمبوڠ بلاجر' },
  continueBtn: { rumi: 'Sambung', jawi: 'سمبوڠ' },
  letsGo: { rumi: 'Jom!', jawi: 'جوم!' },
  rank: { rumi: 'Peringkat', jawi: 'ڤريڠكت' },
  xpToNext: { rumi: 'XP lagi ke peringkat seterusnya', jawi: 'XP لاݢي ك ڤريڠكت ستروسڽ' },
  topRank: { rumi: 'Peringkat tertinggi! Hebat!', jawi: 'ڤريڠكت ترتيڠݢي! هيبت!' },
  newRank: { rumi: 'Peringkat baharu!', jawi: 'ڤريڠكت بهارو!' },
  subjectNotFound: { rumi: 'Subjek tidak dijumpai.', jawi: 'سوبجيك تيدق دجومڤاي.' },

  // map / topics
  hello: { rumi: 'Hai', jawi: 'هاي' },
  topics: { rumi: 'topik', jawi: 'توڤيق' },
  mastery: { rumi: 'Penguasaan', jawi: 'ڤڠواساءن' },
  bab: { rumi: 'Bab', jawi: 'باب' },
  readOnly: { rumi: 'Bacaan', jawi: 'باچاءن' },
  startHere: { rumi: 'Mula di sini!', jawi: 'مولا دسيني!' },
  subjectTip: {
    rumi: 'Pilih satu topik. Cuba kumpul 3 bintang untuk setiap topik!',
    jawi: 'ڤيليه ساتو توڤيق. چوبا كومڤول 3 بينتڠ اونتوق ستياڤ توڤيق!',
  },
  topicTip: {
    rumi: 'Tip: baca nota dulu, kemudian cuba latihan. Kamu pasti boleh!',
    jawi: 'تيڤ: باچ نوتا دولو، كمودين چوبا لاتيهن. كامو ڤستي بوليه!',
  },
  level: { rumi: 'Tahap', jawi: 'تاهڤ' },
  locked: { rumi: 'Berkunci', jawi: 'بركونچي' },
  lockedHint: {
    rumi: 'Dapatkan purata 70% dalam 3 cubaan terakhir untuk membuka tahap ini.',
    jawi: 'داڤتكن ڤوراتا 70% دالم 3 چوباءن تراخير اونتوق ممبوك تاهڤ اين.',
  },
  level1: { rumi: 'Jawapan pendek', jawi: 'جواڤن ڤنديق' },
  level2: { rumi: 'Jawapan berstruktur', jawi: 'جواڤن برستروكتور' },
  level3: { rumi: 'Jawapan esei', jawi: 'جواڤن ايسي' },
  readNote: { rumi: 'Baca Nota', jawi: 'باچ نوتا' },
  startPractice: { rumi: 'Mula Latihan', jawi: 'مولا لاتيهن' },
  questionsCount: { rumi: 'soalan', jawi: 'سوءالن' },
  notVerified: {
    rumi: 'Nota ini belum disemak oleh guru.',
    jawi: 'نوتا اين بلوم دسمق اوليه ݢورو.',
  },
  source: { rumi: 'Sumber', jawi: 'سومبر' },

  // practice
  question: { rumi: 'Soalan', jawi: 'سوءالن' },
  marks: { rumi: 'markah', jawi: 'مركه' },
  yourAnswer: { rumi: 'Jawapan kamu', jawi: 'جواڤن كامو' },
  typeHere: { rumi: 'Taip jawapan di sini…', jawi: 'تاءيڤ جواڤن دسيني…' },
  showKeyboard: { rumi: 'Papan kekunci Jawi', jawi: 'ڤاڤن ككونچي جاوي' },
  hideKeyboard: { rumi: 'Sorok papan kekunci', jawi: 'سوروق ڤاڤن ككونچي' },
  checkAnswer: { rumi: 'Semak Jawapan', jawi: 'سمق جواڤن' },
  pressEnter: { rumi: 'Tekan Enter untuk semak', jawi: 'تكن Enter اونتوق سمق' },
  thinking: { rumi: 'Bulan sedang memeriksa jawapan kamu…', jawi: 'بولن سدڠ مميريقسا جواڤن كامو…' },
  thinkingSlow: {
    rumi: 'Soalan panjang mengambil masa sedikit. Tunggu ya!',
    jawi: 'سوءالن ڤنجڠ مڠمبيل ماس سديكيت. توڠݢو يا!',
  },
  showQuestionIn: { rumi: 'Lihat dalam Jawi', jawi: 'ليهت دالم رومي' },
  listen: { rumi: 'Dengar soalan', jawi: 'دڠر سوءالن' },
  hintPointsBefore: { rumi: 'Petunjuk: sebut', jawi: 'ڤتونجوق: سبوت' },
  hintPointsAfter: { rumi: 'perkara penting.', jawi: 'ڤركارا ڤنتيڠ.' },
  hintJawi: {
    rumi: 'Petunjuk: tulis dalam huruf Jawi. Guna papan kekunci di bawah.',
    jawi: 'ڤتونجوق: توليس دالم حروف جاوي. ݢوناكن ڤاڤن ككونچي دباوه.',
  },
  chooseOne: { rumi: 'Pilih jawapan:', jawi: 'ڤيليه جواڤن:' },
  tapWords: { rumi: 'Tekan perkataan untuk menjawab:', jawi: 'تكن ڤركاتاءن اونتوق منجواب:' },
  clearChoice: { rumi: 'Padam pilihan', jawi: 'ڤادم ڤيليهن' },
  betul: { rumi: 'Betul', jawi: 'بتول' },
  salah: { rumi: 'Salah', jawi: 'ساله' },
  stopRound: { rumi: 'Berhenti', jawi: 'برهنتي' },
  loadError: { rumi: 'Alamak, ada masalah.', jawi: 'الامق، اد مسئله.' },
  tryAgain: { rumi: 'Cuba lagi', jawi: 'چوبا لاݢي' },
  loading: { rumi: 'Memuatkan…', jawi: 'ممواتكن…' },

  // result
  result: { rumi: 'Keputusan', jawi: 'كڤوتوسن' },
  whatToImprove: { rumi: 'Apa yang perlu dibaiki', jawi: 'اڤ يڠ ڤرلو دباءيقي' },
  allCorrect: { rumi: 'Semua perkara penting sudah disebut!', jawi: 'سموا ڤركارا ڤنتيڠ سوده دسبوت!' },
  correctAnswer: { rumi: 'Jawapan betul', jawi: 'جواڤن بتول' },
  nextStep: { rumi: 'Cadangan', jawi: 'چادڠن' },
  continue: { rumi: 'Teruskan', jawi: 'تروسكن' },
  seeRoundResult: { rumi: 'Lihat keputusan pusingan', jawi: 'ليهت كڤوتوسن ڤوسيڠن' },
  goNextLevel: { rumi: 'Ke tahap seterusnya', jawi: 'ك تاهڤ ستروسڽ' },
  howAiThinks: { rumi: 'Bagaimana AI berfikir', jawi: 'باݢايمان AI برفيكير' },
  newBadge: { rumi: 'Lencana baharu!', jawi: 'لنچان بهارو!' },
  levelUnlocked: { rumi: 'Tahap baharu dibuka!', jawi: 'تاهڤ بهارو دبوك!' },
  wow: { rumi: 'Hebat!', jawi: 'هيبت!' },
  stars: { rumi: 'bintang', jawi: 'بينتڠ' },

  // round summary
  roundDone: { rumi: 'Tahniah! Pusingan selesai!', jawi: 'تهنية! ڤوسيڠن سلساي!' },
  roundKeepGoing: { rumi: 'Bagus! Teruskan berlatih, kamu makin pandai!', jawi: 'باݢوس! تروسكن برلاتيه، كامو ماكين ڤنداي!' },
  roundStars: { rumi: 'Bintang dikumpul', jawi: 'بينتڠ دكومڤول' },
  roundPerfect: { rumi: 'Jawapan tepat', jawi: 'جواڤن تڤت' },
  roundXp: { rumi: 'XP diperoleh', jawi: 'XP دڤراوليه' },
  playAgain: { rumi: 'Main lagi', jawi: 'ماءين لاݢي' },
  chooseOtherTopic: { rumi: 'Pilih topik lain', jawi: 'ڤيليه توڤيق لاءين' },

  // progress
  xp: { rumi: 'Mata XP', jawi: 'مات XP' },
  streak: { rumi: 'Hari berturut-turut', jawi: 'هاري برتوروت٢' },
  badges: { rumi: 'Lencana', jawi: 'لنچان' },
  trophyShelf: { rumi: 'Rak Lencana', jawi: 'رق لنچان' },
  noBadges: { rumi: 'Jawab soalan untuk dapat lencana pertama!', jawi: 'جواب سوءالن اونتوق داڤت لنچان ڤرتام!' },
  earned: { rumi: 'Sudah diperoleh', jawi: 'سوده دڤراوليه' },
  notEarned: { rumi: 'Belum diperoleh', jawi: 'بلوم دڤراوليه' },
  topicsTried: { rumi: 'Topik dicuba', jawi: 'توڤيق دچوبا' },
  recent: { rumi: 'Cubaan terkini', jawi: 'چوباءن تركيني' },
  noRecent: { rumi: 'Belum ada cubaan.', jawi: 'بلوم اد چوباءن.' },
  attempts: { rumi: 'cubaan', jawi: 'چوباءن' },

  // chat assistant
  chatTitle: { rumi: 'Tanya Bulan', jawi: 'تاڽ بولن' },
  chatSubtitle: {
    rumi: 'Tanya apa-apa tentang Ibadah, Jawi atau Tajwid sebelum latihan!',
    jawi: 'تاڽ اڤ٢ تنتڠ عبادة، جاوي اتاو تجويد سبلوم لاتيهن!',
  },
  chatPlaceholder: { rumi: 'Taip soalan kamu di sini…', jawi: 'تايڤ سوءالن كامو دسيني…' },
  chatSend: { rumi: 'Hantar', jawi: 'هنتر' },
  chatThinking: { rumi: 'Bulan sedang berfikir…', jawi: 'بولن سدڠ برفيكر…' },
  chatSources: { rumi: 'Sumber:', jawi: 'سومبر:' },
  chatPage: { rumi: 'ms.', jawi: 'مس.' },
  chatLimit: {
    rumi: 'Kamu telah menggunakan 10 soalan untuk sesi ini. Log masuk semula untuk lebih banyak.',
    jawi: 'كامو تله مڠگونكن 10 سوءالن اونتوق سسي اين. لوݢ مسوق سمولا اونتوق لبيه بڽق.',
  },
  chatOpen: { rumi: 'Tanya AI', jawi: 'تاڽ AI' },
  chatClose: { rumi: 'Tutup', jawi: 'توتوڤ' },
  chatError: { rumi: 'Maaf, berlaku ralat. Cuba lagi.', jawi: 'ماعف، برلاكو رالت. چوبا لاݢي.' },
} satisfies Record<string, Record<Script, string>>

export type StringKey = keyof typeof STRINGS

export const BADGES: Record<string, { emoji: string; rumi: string; jawi: string }> = {
  langkah_pertama: { emoji: '👣', rumi: 'Langkah Pertama', jawi: 'لڠكه ڤرتام' },
  tiga_bintang: { emoji: '🌟', rumi: 'Tiga Bintang', jawi: 'تيݢ بينتڠ' },
  tahap_2: { emoji: '🥈', rumi: 'Buka Tahap 2', jawi: 'بوك تاهڤ 2' },
  tahap_3: { emoji: '🥇', rumi: 'Buka Tahap 3', jawi: 'بوك تاهڤ 3' },
  rajin_3_hari: { emoji: '🔥', rumi: 'Rajin 3 Hari', jawi: 'راجين 3 هاري' },
}
