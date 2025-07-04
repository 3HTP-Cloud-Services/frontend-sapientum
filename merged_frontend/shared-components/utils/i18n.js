import { writable } from 'svelte/store';
import { I18n } from 'i18n-js';
import { httpCall } from './httpCall.js';

export const i18nStore = writable(null);
export const currentLocale = writable("en");

export function getSavedLanguage() {
  try {
    return localStorage.getItem('selectedLanguage') || 'en';
  } catch (error) {
    console.error('Error reading language from localStorage:', error);
    return 'en';
  }
}

export function saveLanguage(locale) {
  try {
    localStorage.setItem('selectedLanguage', locale);
  } catch (error) {
    console.error('Error saving language to localStorage:', error);
  }
}

export async function initializeI18n() {
  try {
    const savedLanguage = getSavedLanguage();
    const defaultTranslations = {
      es: {
        title: "Consola de Administración Sapientum AI",
        i18n_warning: "No se pudo conseguir la traducción necesaria",
        chat_title: "Chat",
        chat_placeholder: "Escribe tu mensaje...",
        send_button: "Enviar",
        clear_chat: "Limpiar",
        login_title: "Iniciar Sesión",
        username: "Nombre de usuario",
        password: "Contraseña",
        login_button: "Acceder",
        logging_in: "Iniciando sesión...",
        logout: "Cerrar sesión",
        ai_welcome: "¡Bienvenido! ¿Cómo puedo ayudarte hoy?",
        chat_connection_error: "Estoy teniendo problemas para conectarme al servidor. Por favor, inténtalo más tarde.",
        no_chat_access: "No tienes acceso a la funcionalidad de chat.",
        chat_only_access_required: "Esta aplicación requiere permisos de acceso al chat, que tu cuenta no tiene."
      },
      pt: {
        title: "Console de Administração Sapientum AI",
        i18n_warning: "Não foi possível obter a tradução necessária",
        chat_title: "Chat",
        chat_placeholder: "Digite sua mensagem...",
        send_button: "Enviar",
        clear_chat: "Limpar",
        login_title: "Login",
        username: "Nome de usuário",
        password: "Senha",
        login_button: "Entrar",
        logging_in: "Fazendo login...",
        logout: "Sair",
        ai_welcome: "Bem-vindo! Como posso ajudá-lo hoje?",
        chat_connection_error: "Estou tendo problemas para conectar ao servidor. Tente novamente mais tarde.",
        no_chat_access: "Você não tem acesso à funcionalidade de chat.",
        chat_only_access_required: "Esta aplicação requer permissão de acesso ao chat, que sua conta não possui."
      },
      en: {
        title: "Sapientum AI Administration Console",
        i18n_warning: "Could not get the necessary translation",
        chat_title: "Chat",
        chat_placeholder: "Type your message...",
        send_button: "Send",
        clear_chat: "Clear",
        login_title: "Login??",
        username: "Username",
        password: "Password",
        login_button: "Login",
        logging_in: "Logging in...",
        logout: "Logout",
        ai_welcome: "Welcome! How can I help you today?",
        chat_connection_error: "I'm having trouble connecting to the server. Please try again later.",
        no_chat_access: "You do not have access to chat functionality.",
        chat_only_access_required: "This application requires chat access permission, which your account does not have."
      }
    };
    let i18n = new I18n(defaultTranslations);

    try {
      const response = await httpCall('/api/i18n');
      if (response.ok) {
        const translations = await response.json();
        i18n = new I18n({ ...defaultTranslations, ...translations });
      }
    } catch (error) {
      console.error('Failed to load translations:', error);
    }
    i18n.defaultLocale = "en";
    i18n.locale = savedLanguage;
    currentLocale.set(savedLanguage);
    i18nStore.set(i18n);
    return i18n;
  } catch (error) {
    console.error('Error initializing i18n:', error);
    throw error;
  }
}

export function setLocale(locale) {
  if (locale !== 'en' && locale !== 'es' && locale !== 'pt') {
    console.error('Invalid locale:', locale);
    return false;
  }

  saveLanguage(locale);

  i18nStore.update(i18n => {
    if (i18n) {
      i18n.locale = locale;
    }
    return i18n;
  });

  currentLocale.set(locale);
  return true;
}

export function t(key, options) {
  let result;
  i18nStore.subscribe(i18n => {
    if (i18n) {
      result = i18n.t(key, options);

      if (options) {
        Object.keys(options).forEach(key => {
          const placeholder = `{${key}}`;
          result = result.replace(placeholder, options[key]);
        });
      }
    } else {
      result = key;
    }
  })();
  return result;
}

export async function updateTranslations(language, updates) {
  try {
    const response = await httpCall('/api/i18n', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ language, updates }),
      credentials: 'include'
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update translations');
    }

    await refreshTranslations();

    return { success: true };
  } catch (error) {
    console.error('Error updating translations:', error);
    return { success: false, error: error.message };
  }
}

export async function refreshTranslations() {
  try {
    const response = await httpCall('/api/i18n');
    if (response.ok) {
      const translations = await response.json();
      const i18n = new I18n(translations);

      let locale = getSavedLanguage();
      i18nStore.subscribe(currentI18n => {
        if (currentI18n) {
          locale = currentI18n.locale;
        }
      })();

      i18n.defaultLocale = "en";
      i18n.locale = locale;
      currentLocale.set(locale);
      i18nStore.set(i18n);
      return true;
    }
    return false;
  } catch (error) {
    console.error('Failed to refresh translations:', error);
    return false;
  }
}
