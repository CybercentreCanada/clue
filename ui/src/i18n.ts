import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import translationEN from 'locales/en/translation.json';
import translationFR from 'locales/fr/translation.json';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    clue: translationEN
  },
  fr: {
    clue: translationFR
  },
  woof: {
    clue: Object.keys(translationEN).reduce(
      (acc, key) => {
        acc[key] = 'woof';
        return acc;
      },
      {} as { [key: string]: string }
    )
  }
};

// eslint-disable-next-line import/no-named-as-default-member
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    defaultNS: 'clue',
    fallbackLng: 'en',
    keySeparator: false,
    interpolation: {
      escapeValue: false
    },
    detection: {
      order: ['localStorage', 'cookie']
    },
    resources
  });

export default i18n;
