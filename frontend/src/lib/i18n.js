import { writable } from 'svelte/store';
import { I18n } from 'i18n-js';

// Create a writable store with default value
export const i18nStore = writable(null);

// Initialize function that can be called from main.js
export async function initializeI18n() {
  try {
    // Initial translations
    const defaultTranslations = {
      es: {
        title: "Consola de Administración Sapientum AI",
        i18n_warning: "No se pudo conseguir la traducción necesaria",
      },
      en: {
        title: "Sapientum AI Administration Console",
        i18n_warning: "Could not get the necessary translation",
      }
    };
    let i18n = new I18n(defaultTranslations);

    try {
      const response = await fetch('/api/i18n');
      if (response.ok) {
        const translations = await response.json();
        i18n = new I18n(translations);
      }
    } catch (error) {
      console.error('Failed to load translations:', error);
    }
    i18n.defaultLocale = "en";
    i18n.locale = "en";
    i18nStore.set(i18n);
    return i18n;
  } catch (error) {
    console.error('Error initializing i18n:', error);
    throw error;
  }
}

export function t(key, options) {
  let result;
  i18nStore.subscribe(i18n => {
    if (i18n) {
      result = i18n.t(key, options);
    } else {
      result = key;
    }
  })();
  return result;
}
