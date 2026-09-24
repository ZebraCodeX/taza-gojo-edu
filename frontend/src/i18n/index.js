// i18n/index.js — dependency-free localisation.
//
// Kept tiny on purpose: on a 2G link every KB counts, and the app must work
// fully offline, so translations ship with the bundle rather than being fetched.
// Ethiopia-first: Amharic (am) and Afaan Oromo (om) lead, with Tigrinya (ti),
// Somali (so), then continental languages French/Swahili/Arabic (RTL).

import { useSyncExternalStore } from "react";

export const LANGUAGES = [
  { code: "en", label: "English", dir: "ltr" },
  { code: "am", label: "አማርኛ", dir: "ltr" },
  { code: "om", label: "Afaan Oromoo", dir: "ltr" },
  { code: "ti", label: "ትግርኛ", dir: "ltr" },
  { code: "so", label: "Soomaali", dir: "ltr" },
  { code: "fr", label: "Français", dir: "ltr" },
  { code: "sw", label: "Kiswahili", dir: "ltr" },
  { code: "ar", label: "العربية", dir: "rtl" },
];

const STRINGS = {
  en: {
    learn: "Learn", library: "Library", tutors: "Tutors", profile: "Profile",
    home: "Home", assessments: "Assessments", labs: "Labs", live: "Live",
    progress: "Progress", certificates: "Certificates", admin: "Admin",
    start: "Start", submit: "Submit", next: "Next", finish: "Finish",
    correct: "Correct", tryAgain: "Try again", score: "Score", question: "Question",
    of: "of", results: "Results", passed: "Passed", failed: "Not yet",
    yourAnswer: "Your answer", run: "Run", check: "Check", testsPassed: "tests passed",
    subjects: "Subjects", physics: "Physics", electricity: "Electricity",
    math: "Mathematics", science: "Science", computing: "Computing", english: "English",
    liveClasses: "Live classes", join: "Join", scheduled: "Scheduled", end: "End",
    certificate: "Certificate", verify: "Verify", issued: "Issued",
    savedOffline: "Saved offline — will sync", online: "Online", offline: "Offline",
    loading: "Loading…", signOut: "Sign out", back: "Back",
  },
  am: {
    learn: "ተማር", library: "ቤተ መጻሕፍት", tutors: "አስተማሪዎች", profile: "መገለጫ",
    home: "መነሻ", assessments: "ፈተናዎች", labs: "ላቦራቶሪዎች", live: "ቀጥታ",
    progress: "እድገት", certificates: "ሰርተፍኬቶች", admin: "አስተዳደር",
    start: "ጀምር", submit: "አስገባ", next: "ቀጣይ", finish: "ጨርስ",
    correct: "ትክክል", tryAgain: "እንደገና ሞክር", score: "ነጥብ", question: "ጥያቄ",
    of: "ከ", results: "ውጤቶች", passed: "አልፈሃል", failed: "ገና አልተሳካም",
    yourAnswer: "የአንተ መልስ", run: "አሂድ", check: "ፈትሽ", testsPassed: "ፈተናዎች አልፈዋል",
    subjects: "ትምህርቶች", physics: "ፊዚክስ", electricity: "ኤሌክትሪክ",
    math: "ሒሳብ", science: "ሳይንስ", computing: "ኮምፒውተር", english: "እንግሊዝኛ",
    liveClasses: "ቀጥታ ክፍሎች", join: "ተቀላቀል", scheduled: "ተያዘ", end: "አቁም",
    certificate: "ሰርተፍኬት", verify: "አረጋግጥ", issued: "የተሰጠ",
    savedOffline: "በኦፍላይን ተቀምጧል — ይሰናኝ", online: "በመስመር ላይ", offline: "ከመስመር ውጭ",
    loading: "በመጫን ላይ…", signOut: "ውጣ", back: "ተመለስ",
  },
  om: {
    learn: "Baradhu", library: "Mana Kitaabaa", tutors: "Barsiisoota", profile: "Profaayilii",
    home: "Fuula Duraa", assessments: "Qormaata", labs: "Laaboraatoorii", live: "Kallattii",
    progress: "Adeemsa", certificates: "Waraqaa Ragaa", admin: "Bulchiinsa",
    start: "Jalqabi", submit: "Galchi", next: "Itti aanu", finish: "Xumuri",
    correct: "Sirrii", tryAgain: "Irra deebi'ii yaali", score: "Qabxii", question: "Gaaffii",
    of: "keessaa", results: "Bu'aawwan", passed: "Darbee", failed: "Ammas hin milkoofne",
    yourAnswer: "Deebii kee", run: "Fiigsi", check: "Sakatta'i", testsPassed: "qormaanni darban",
    subjects: "Barnoota", physics: "Fiiziksii", electricity: "Elektirikii",
    math: "Herrega", science: "Saayinsii", computing: "Kompiitara", english: "Ingiliffa",
    liveClasses: "Kutaalee kallattii", join: "Makami", scheduled: "Yeroon qabame", end: "Dhaabi",
    certificate: "Waraqaa ragaa", verify: "Mirkaneessi", issued: "Kenname",
    savedOffline: "Offlineffaa olkaa'ame — ni sinkii", online: "Toora irra", offline: "Toora ala",
    loading: "Fe'aa jira…", signOut: "Ba'i", back: "Deebi'i",
  },
  ti: {
    learn: "ተማሃር", library: "ቤተ መጻሕፍቲ", tutors: "ኣሰልጠንቲ", profile: "መግለጺ",
    home: "መእተዊ", assessments: "ፈተነታት", labs: "ላቦራቶሪ", live: "ቀጥታ",
    progress: "ዕቤት", certificates: "ምስክር ወረቐት", admin: "ምሕደራ",
    start: "ጀምር", submit: "ኣቕርብ", next: "ቀጻሊ", finish: "ወድኣ",
    correct: "ቅኑዕ", tryAgain: "ደጊምካ ፈትን", score: "ነጥቢ", question: "ሕቶ",
    of: "ካብ", results: "ውጽኢታት", passed: "ሓሊፉ", failed: "ጌና ኣይተዓወተን",
    yourAnswer: "መልስኻ", run: "ኣኻውሕ", check: "ፈትሽ", testsPassed: "ፈተነታት ሓሊፎም",
    subjects: "ትምህርትታት", physics: "ፊዚክስ", electricity: "ኤለክትሪክ",
    math: "ሕሳብ", science: "ሳይንስ", computing: "ኮምፒዩተር", english: "እንግሊዝኛ",
    liveClasses: "ቀጥታ ክፍሊታት", join: "ተጸምበር", scheduled: "ተመዲቡ", end: "ኣቋርጽ",
    certificate: "ምስክር ወረቐት", verify: "ኣረጋግጽ", issued: "ተዋሂቡ",
    savedOffline: "ብኦፍላይን ተቐሚጡ — ክሰናኸል", online: "ኣብ መስመር", offline: "ካብ መስመር ወጻኢ",
    loading: "ይጽዕን…", signOut: "ውጻእ", back: "ተመለስ",
  },
  so: {
    learn: "Baro", library: "Maktabadda", tutors: "Macalimiin", profile: "Profayl",
    home: "Guriga", assessments: "Imtixaanno", labs: "Shaybaadhka", live: "Toos",
    progress: "Horumar", certificates: "Shahaadooyin", admin: "Maamul",
    start: "Bilow", submit: "Gudbi", next: "Xiga", finish: "Dhammee",
    correct: "Sax", tryAgain: "Mar kale isku day", score: "Dhibcood", question: "Su'aal",
    of: "ka", results: "Natiijooyin", passed: "Gudbay", failed: "Weli ma gudbin",
    yourAnswer: "Jawaabtaada", run: "Socodsii", check: "Hubi", testsPassed: "imtixaanada gudbay",
    subjects: "Maadooyin", physics: "Fiisigis", electricity: "Koronto",
    math: "Xisaab", science: "Saynis", computing: "Kombiyuutar", english: "Ingiriisi",
    liveClasses: "Fasallo toos ah", join: "Ku biir", scheduled: "La qorsheeyay", end: "Jooji",
    certificate: "Shahaado", verify: "Xaqiiji", issued: "La bixiyay",
    savedOffline: "Offline ayaa lagu kaydiyay — wuu isku dhejin doonaa", online: "Online", offline: "Offline",
    loading: "Waa la soo dejinayaa…", signOut: "Ka bax", back: "Dib u noqo",
  },
  fr: {
    learn: "Apprendre", library: "Bibliothèque", tutors: "Tuteurs", profile: "Profil",
    home: "Accueil", assessments: "Évaluations", labs: "Laboratoires", live: "En direct",
    progress: "Progrès", certificates: "Certificats", admin: "Admin",
    start: "Commencer", submit: "Soumettre", next: "Suivant", finish: "Terminer",
    correct: "Correct", tryAgain: "Réessayer", score: "Score", question: "Question",
    of: "sur", results: "Résultats", passed: "Réussi", failed: "Pas encore",
    yourAnswer: "Votre réponse", run: "Exécuter", check: "Vérifier", testsPassed: "tests réussis",
    subjects: "Matières", physics: "Physique", electricity: "Électricité",
    math: "Mathématiques", science: "Sciences", computing: "Informatique", english: "Anglais",
    liveClasses: "Cours en direct", join: "Rejoindre", scheduled: "Programmé", end: "Terminer",
    certificate: "Certificat", verify: "Vérifier", issued: "Délivré",
    savedOffline: "Enregistré hors ligne — synchronisation", online: "En ligne", offline: "Hors ligne",
    loading: "Chargement…", signOut: "Déconnexion", back: "Retour",
  },
  sw: {
    learn: "Soma", library: "Maktaba", tutors: "Walimu", profile: "Wasifu",
    home: "Nyumbani", assessments: "Tathmini", labs: "Maabara", live: "Moja kwa moja",
    progress: "Maendeleo", certificates: "Vyeti", admin: "Usimamizi",
    start: "Anza", submit: "Tuma", next: "Ifuatayo", finish: "Maliza",
    correct: "Sahihi", tryAgain: "Jaribu tena", score: "Alama", question: "Swali",
    of: "kati ya", results: "Matokeo", passed: "Umefaulu", failed: "Bado",
    yourAnswer: "Jibu lako", run: "Endesha", check: "Angalia", testsPassed: "mitihani imefaulu",
    subjects: "Masomo", physics: "Fizikia", electricity: "Umeme",
    math: "Hisabati", science: "Sayansi", computing: "Kompyuta", english: "Kiingereza",
    liveClasses: "Madarasa ya moja kwa moja", join: "Jiunge", scheduled: "Imepangwa", end: "Maliza",
    certificate: "Cheti", verify: "Thibitisha", issued: "Imetolewa",
    savedOffline: "Imehifadhiwa nje ya mtandao — itasawazishwa", online: "Mtandaoni", offline: "Nje ya mtandao",
    loading: "Inapakia…", signOut: "Toka", back: "Rudi",
  },
  ar: {
    learn: "تعلّم", library: "المكتبة", tutors: "المعلمون", profile: "الملف الشخصي",
    home: "الرئيسية", assessments: "التقييمات", labs: "المختبرات", live: "مباشر",
    progress: "التقدّم", certificates: "الشهادات", admin: "الإدارة",
    start: "ابدأ", submit: "إرسال", next: "التالي", finish: "إنهاء",
    correct: "صحيح", tryAgain: "حاول مرة أخرى", score: "النتيجة", question: "سؤال",
    of: "من", results: "النتائج", passed: "ناجح", failed: "ليس بعد",
    yourAnswer: "إجابتك", run: "تشغيل", check: "تحقّق", testsPassed: "اختبارات ناجحة",
    subjects: "المواد", physics: "الفيزياء", electricity: "الكهرباء",
    math: "الرياضيات", science: "العلوم", computing: "الحاسوب", english: "الإنجليزية",
    liveClasses: "الحصص المباشرة", join: "انضم", scheduled: "مجدول", end: "إنهاء",
    certificate: "شهادة", verify: "تحقّق", issued: "صدرت",
    savedOffline: "تم الحفظ دون اتصال — سيتم المزامنة", online: "متصل", offline: "غير متصل",
    loading: "جارٍ التحميل…", signOut: "خروج", back: "رجوع",
  },
};

let lang = localStorage.getItem("tg_lang") || detectDefault();
const listeners = new Set();

function detectDefault() {
  const nav = (navigator.language || "en").slice(0, 2);
  return STRINGS[nav] ? nav : "en";
}

export function getLang() {
  return lang;
}

export function setLang(code) {
  if (!STRINGS[code]) code = "en";
  lang = code;
  localStorage.setItem("tg_lang", code);
  document.documentElement.lang = code;
  document.documentElement.dir = LANGUAGES.find((l) => l.code === code)?.dir || "ltr";
  listeners.forEach((l) => l());
}

export function t(key, fallback) {
  return STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? fallback ?? key;
}

export function useI18n() {
  useSyncExternalStore(
    (fn) => { listeners.add(fn); return () => listeners.delete(fn); },
    () => lang
  );
  return { t, lang, setLang, dir: LANGUAGES.find((l) => l.code === lang)?.dir || "ltr" };
}

// Apply direction on first load.
if (typeof document !== "undefined") {
  document.documentElement.lang = lang;
  document.documentElement.dir = LANGUAGES.find((l) => l.code === lang)?.dir || "ltr";
}
