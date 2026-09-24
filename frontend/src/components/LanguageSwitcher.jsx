import { LANGUAGES, useI18n } from "../i18n";

export default function LanguageSwitcher() {
  const { lang, setLang } = useI18n();
  return (
    <select
      className="lang-select"
      value={lang}
      onChange={(e) => setLang(e.target.value)}
      aria-label="Language"
      title="Language"
    >
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
