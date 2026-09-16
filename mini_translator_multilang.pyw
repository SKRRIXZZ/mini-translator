import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import sys
import json
import ctypes
from ctypes import wintypes
import tempfile
import urllib.request
import urllib.parse
import collections

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    TRAY_OK = True
except ImportError:
    TRAY_OK = False

try:
    import winreg
    WINREG_OK = True
except ImportError:
    WINREG_OK = False


def _set_app_id(app_id):
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

_set_app_id("MiniTranslator.Custom.App.6")


SIGNAL_FILE = os.path.join(tempfile.gettempdir(),
                           "mini_translator_singleton.signal")
_mutex_handle = None
ERROR_ALREADY_EXISTS = 183
REG_PATH = r"Software\MiniTranslator"

LINGVA_URL = "https://lingva.ml/api/v1/{source}/{target}/{query}"
DEEPLX_URL = "https://api.deeplx.org/translate"
LINGVA_URL_ALT = "https://lingva.garudalinux.org/api/v1/{source}/{target}/{query}"

MOD_ALT      = 0x0001
MOD_CONTROL  = 0x0002
MOD_SHIFT    = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY    = 0x0312
WM_QUIT      = 0x0012

INPUT_KEYBOARD   = 1
KEYEVENTF_KEYUP  = 0x0002
VK_CONTROL       = 0x11
VK_MENU          = 0x12
VK_SHIFT         = 0x10
VK_C             = 0x43
VK_Q             = 0x51

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]

user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

user32.OpenClipboard.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [wintypes.HWND]

user32.CloseClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []

user32.EmptyClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []

user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
user32.GetClipboardSequenceNumber.argtypes = []

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]

kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalFree.restype = wintypes.HGLOBAL
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]


# ============ ЛОКАЛИЗАЦИЯ ============
UI_LANGS = {
    'en': 'English', 'ru': 'Русский', 'de': 'Deutsch', 'fr': 'Français',
    'es': 'Español', 'it': 'Italiano', 'pt': 'Português', 'nl': 'Nederlands',
    'pl': 'Polski', 'tr': 'Türkçe', 'cs': 'Čeština', 'hu': 'Magyar',
    'ro': 'Română', 'uk': 'Українська', 'sv': 'Svenska', 'fi': 'Suomi',
    'ja': '日本語', 'ko': '한국어', 'zh': '中文', 'ar': 'العربية'
}


def _mk(ru, en, **kw):
    d = {'ru': ru, 'en': en}
    d.update(kw)
    return d


UI_TR = {
    'Мини-переводчик': _mk(
        'Мини-переводчик', 'Mini Translator',
        de='Mini-Übersetzer', fr='Mini Traducteur', es='Mini Traductor',
        it='Mini Traduttore', pt='Mini Tradutor', nl='Mini Vertaler',
        pl='Mini Tłumacz', tr='Mini Çevirmen', cs='Mini Překladač',
        hu='Mini Fordító', ro='Mini Traducător', uk='Міні-перекладач',
        sv='Mini Översättare', fi='Mini Kääntäjä',
        ja='ミニ翻訳', ko='미니 번역기', zh='迷你翻译器', ar='مترجم صغير'),

    'Авто': _mk(
        'Авто', 'Auto',
        de='Auto', fr='Auto', es='Auto', it='Auto', pt='Auto', nl='Auto',
        pl='Auto', tr='Otomatik', cs='Auto', hu='Automatikus', ro='Auto',
        uk='Авто', sv='Auto', fi='Auto',
        ja='自動', ko='자동', zh='自动', ar='تلقائي'),

    'Текст для перевода': _mk(
        'Текст для перевода', 'Text to translate',
        de='Zu übersetzender Text', fr='Texte à traduire',
        es='Texto a traducir', it='Testo da tradurre',
        pt='Texto para traduzir', nl='Te vertalen tekst',
        pl='Tekst do tłumaczenia', tr='Çevrilecek metin',
        cs='Text k překladu', hu='Fordítandó szöveg',
        ro='Text de tradus', uk='Текст для перекладу',
        sv='Text att översätta', fi='Käännettävä teksti',
        ja='翻訳するテキスト', ko='번역할 텍스트',
        zh='要翻译的文本', ar='النص المراد ترجمته'),

    'Перевести': _mk(
        'Перевести', 'Translate',
        de='Übersetzen', fr='Traduire', es='Traducir', it='Traduci',
        pt='Traduzir', nl='Vertalen', pl='Tłumacz', tr='Çevir',
        cs='Přeložit', hu='Fordítás', ro='Traduce', uk='Перекласти',
        sv='Översätt', fi='Käännä',
        ja='翻訳', ko='번역', zh='翻译', ar='ترجمة'),

    '📋 Перевести буфер': _mk(
        '📋 Перевести буфер', '📋 Translate clipboard',
        de='📋 Zwischenablage übersetzen', fr='📋 Traduire le presse-papiers',
        es='📋 Traducir portapapeles', it='📋 Traduci appunti',
        pt='📋 Traduzir área de transferência', nl='📋 Klembord vertalen',
        pl='📋 Przetłumacz schowek', tr='📋 Panoyu çevir',
        cs='📋 Přeložit schránku', hu='📋 Vágólap fordítása',
        ro='📋 Tradu clipboardul', uk='📋 Перекласти буфер',
        sv='📋 Översätt urklipp', fi='📋 Käännä leikepöytä',
        ja='📋 クリップボードを翻訳', ko='📋 클립보드 번역',
        zh='📋 翻译剪贴板', ar='📋 ترجمة الحافظة'),

    '✕  Очистить буфер': _mk(
        '✕  Очистить буфер', '✕  Clear clipboard',
        de='✕  Zwischenablage leeren', fr='✕  Vider le presse-papiers',
        es='✕  Borrar portapapeles', it='✕  Cancella appunti',
        pt='✕  Limpar área de transferência', nl='✕  Klembord wissen',
        pl='✕  Wyczyść schowek', tr='✕  Panoyu temizle',
        cs='✕  Vymazat schránku', hu='✕  Vágólap törlése',
        ro='✕  Golește clipboardul', uk='✕  Очистити буфер',
        sv='✕  Rensa urklipp', fi='✕  Tyhjennä leikepöytä',
        ja='✕  クリップボードを消去', ko='✕  클립보드 지우기',
        zh='✕  清空剪贴板', ar='✕  مسح الحافظة'),

    'Перевод': _mk(
        'Перевод', 'Translation',
        de='Übersetzung', fr='Traduction', es='Traducción',
        it='Traduzione', pt='Tradução', nl='Vertaling',
        pl='Tłumaczenie', tr='Çeviri', cs='Překlad',
        hu='Fordítás', ro='Traducere', uk='Переклад',
        sv='Översättning', fi='Käännös',
        ja='翻訳', ko='번역', zh='翻译', ar='الترجمة'),

    '✕  Очистить текст': _mk(
        '✕  Очистить текст', '✕  Clear text',
        de='✕  Text leeren', fr='✕  Effacer le texte',
        es='✕  Borrar texto', it='✕  Cancella testo',
        pt='✕  Limpar texto', nl='✕  Tekst wissen',
        pl='✕  Wyczyść tekst', tr='✕  Metni temizle',
        cs='✕  Vymazat text', hu='✕  Szöveg törlése',
        ro='✕  Golește textul', uk='✕  Очистити текст',
        sv='✕  Rensa text', fi='✕  Tyhjennä teksti',
        ja='✕  テキストを消去', ko='✕  텍스트 지우기',
        zh='✕  清空文本', ar='✕  مسح النص'),

    '✕  Очистить перевод': _mk(
        '✕  Очистить перевод', '✕  Clear translation',
        de='✕  Übersetzung leeren', fr='✕  Effacer la traduction',
        es='✕  Borrar traducción', it='✕  Cancella traduzione',
        pt='✕  Limpar tradução', nl='✕  Vertaling wissen',
        pl='✕  Wyczyść tłumaczenie', tr='✕  Çeviriyi temizle',
        cs='✕  Vymazat překlad', hu='✕  Fordítás törlése',
        ro='✕  Golește traducerea', uk='✕  Очистити переклад',
        sv='✕  Rensa översättning', fi='✕  Tyhjennä käännös',
        ja='✕  翻訳を消去', ko='✕  번역 지우기',
        zh='✕  清空翻译', ar='✕  مسح الترجمة'),

    'Свернуть': _mk(
        'Свернуть', 'Minimize',
        de='Minimieren', fr='Réduire', es='Minimizar', it='Riduci',
        pt='Minimizar', nl='Minimaliseren', pl='Zwiń', tr='Küçült',
        cs='Minimalizovat', hu='Kicsinyítés', ro='Minimizează',
        uk='Згорнути', sv='Minimera', fi='Pienennä',
        ja='最小化', ko='최소화', zh='最小化', ar='تصغير'),

    'Настройки': _mk(
        'Настройки', 'Settings',
        de='Einstellungen', fr='Paramètres', es='Configuración',
        it='Impostazioni', pt='Definições', nl='Instellingen',
        pl='Ustawienia', tr='Ayarlar', cs='Nastavení',
        hu='Beállítások', ro='Setări', uk='Налаштування',
        sv='Inställningar', fi='Asetukset',
        ja='設定', ko='설정', zh='设置', ar='الإعدادات'),

    'Журнал': _mk(
        'Журнал', 'Log',
        de='Protokoll', fr='Journal', es='Registro', it='Registro',
        pt='Registo', nl='Logboek', pl='Dziennik', tr='Günlük',
        cs='Protokol', hu='Napló', ro='Jurnal', uk='Журнал',
        sv='Logg', fi='Loki',
        ja='ログ', ko='로그', zh='日志', ar='السجل'),

    'Выход': _mk(
        'Выход', 'Exit',
        de='Beenden', fr='Quitter', es='Salir', it='Esci',
        pt='Sair', nl='Afsluiten', pl='Wyjście', tr='Çıkış',
        cs='Konec', hu='Kilépés', ro='Ieșire', uk='Вихід',
        sv='Avsluta', fi='Poistu',
        ja='終了', ko='종료', zh='退出', ar='خروج'),

    '⚡  Быстрый перевод': _mk(
        '⚡  Быстрый перевод', '⚡  Quick translation',
        de='⚡  Schnellübersetzung', fr='⚡  Traduction rapide',
        es='⚡  Traducción rápida', it='⚡  Traduzione rapida',
        pt='⚡  Tradução rápida', nl='⚡  Snelle vertaling',
        pl='⚡  Szybkie tłumaczenie', tr='⚡  Hızlı çeviri',
        cs='⚡  Rychlý překlad', hu='⚡  Gyors fordítás',
        ro='⚡  Traducere rapidă', uk='⚡  Швидкий переклад',
        sv='⚡  Snabb översättning', fi='⚡  Nopea käännös',
        ja='⚡  クイック翻訳', ko='⚡  빠른 번역',
        zh='⚡  快速翻译', ar='⚡  ترجمة سريعة'),

    'Исходный текст': _mk(
        'Исходный текст', 'Source text',
        de='Quelltext', fr='Texte source', es='Texto original',
        it='Testo di origine', pt='Texto original', nl='Brontekst',
        pl='Tekst źródłowy', tr='Kaynak metin', cs='Zdrojový text',
        hu='Forrásszöveg', ro='Text sursă', uk='Вихідний текст',
        sv='Källtext', fi='Lähdeteksti',
        ja='原文', ko='원문', zh='源文本', ar='النص الأصلي'),

    'Копировать': _mk(
        'Копировать', 'Copy',
        de='Kopieren', fr='Copier', es='Copiar', it='Copia',
        pt='Copiar', nl='Kopiëren', pl='Kopiuj', tr='Kopyala',
        cs='Kopírovat', hu='Másolás', ro='Copiază', uk='Копіювати',
        sv='Kopiera', fi='Kopioi',
        ja='コピー', ko='복사', zh='复制', ar='نسخ'),

    '✓  Скопировано': _mk(
        '✓  Скопировано', '✓  Copied',
        de='✓  Kopiert', fr='✓  Copié', es='✓  Copiado',
        it='✓  Copiato', pt='✓  Copiado', nl='✓  Gekopieerd',
        pl='✓  Skopiowano', tr='✓  Kopyalandı', cs='✓  Zkopírováno',
        hu='✓  Másolva', ro='✓  Copiat', uk='✓  Скопійовано',
        sv='✓  Kopierat', fi='✓  Kopioitu',
        ja='✓  コピーしました', ko='✓  복사됨',
        zh='✓  已复制', ar='✓  تم النسخ'),

    'Закрыть': _mk(
        'Закрыть', 'Close',
        de='Schließen', fr='Fermer', es='Cerrar', it='Chiudi',
        pt='Fechar', nl='Sluiten', pl='Zamknij', tr='Kapat',
        cs='Zavřít', hu='Bezárás', ro='Închide', uk='Закрити',
        sv='Stäng', fi='Sulje',
        ja='閉じる', ko='닫기', zh='关闭', ar='إغلاق'),

    'Мой язык (перевод на него)': _mk(
        'Мой язык (перевод на него)', 'My language (translate to it)',
        de='Meine Sprache (übersetzen nach)', fr='Ma langue (traduire vers)',
        es='Mi idioma (traducir a)', it='La mia lingua (traduci in)',
        pt='Meu idioma (traduzir para)', nl='Mijn taal (naar vertalen)',
        pl='Mój język (tłumacz na)', tr='Dilim (çevir)',
        cs='Můj jazyk (přeložit do)', hu='Saját nyelv (fordítás erre)',
        ro='Limba mea (traducere în)', uk='Моя мова (перекласти на)',
        sv='Mitt språk (översätt till)', fi='Oma kieli (käännä)',
        ja='自分の言語（翻訳先）', ko='내 언어(번역 대상)',
        zh='我的语言（翻译为）', ar='لغتي (الترجمة إليها)'),

    'Второй язык (для обратного перевода)': _mk(
        'Второй язык (для обратного перевода)',
        'Second language (for reverse translation)',
        de='Zweite Sprache (für Rückübersetzung)',
        fr='Deuxième langue (pour la traduction inverse)',
        es='Segundo idioma (para traducción inversa)',
        it='Seconda lingua (per traduzione inversa)',
        pt='Segundo idioma (para tradução inversa)',
        nl='Tweede taal (voor omgekeerde vertaling)',
        pl='Drugi język (do tłumaczenia odwrotnego)',
        tr='İkinci dil (ters çeviri için)',
        cs='Druhý jazyk (pro zpětný překlad)',
        hu='Második nyelv (fordított fordításhoz)',
        ro='A doua limbă (pentru traducere inversă)',
        uk='Друга мова (для зворотного перекладу)',
        sv='Andra språket (för omvänd översättning)',
        fi='Toinen kieli (käänteiskäännökseen)',
        ja='第二言語（逆翻訳用）', ko='두 번째 언어(역번역용)',
        zh='第二语言（用于反向翻译）', ar='اللغة الثانية (للترجمة العكسية)'),

    'Как пользоваться': _mk(
        'Как пользоваться', 'How to use',
        de='Bedienung', fr="Comment utiliser", es='Cómo usar',
        it='Come usare', pt='Como usar', nl='Hoe te gebruiken',
        pl='Jak używać', tr='Nasıl kullanılır', cs='Jak používat',
        hu='Használat', ro='Cum se utilizează', uk='Як користуватися',
        sv='Hur man använder', fi='Käyttöohje',
        ja='使い方', ko='사용 방법', zh='使用方法', ar='كيفية الاستخدام'),

    'Отмена': _mk(
        'Отмена', 'Cancel',
        de='Abbrechen', fr='Annuler', es='Cancelar', it='Annulla',
        pt='Cancelar', nl='Annuleren', pl='Anuluj', tr='İptal',
        cs='Zrušit', hu='Mégse', ro='Anulare', uk='Скасувати',
        sv='Avbryt', fi='Peruuta',
        ja='キャンセル', ko='취소', zh='取消', ar='إلغاء'),

    'Сохранить': _mk(
        'Сохранить', 'Save',
        de='Speichern', fr='Enregistrer', es='Guardar', it='Salva',
        pt='Guardar', nl='Opslaan', pl='Zapisz', tr='Kaydet',
        cs='Uložit', hu='Mentés', ro='Salvează', uk='Зберегти',
        sv='Spara', fi='Tallenna',
        ja='保存', ko='저장', zh='保存', ar='حفظ'),

    'Ошибка': _mk(
        'Ошибка', 'Error',
        de='Fehler', fr='Erreur', es='Error', it='Errore',
        pt='Erro', nl='Fout', pl='Błąd', tr='Hata',
        cs='Chyba', hu='Hiba', ro='Eroare', uk='Помилка',
        sv='Fel', fi='Virhe',
        ja='エラー', ko='오류', zh='错误', ar='خطأ'),

    'Языки должны быть разными.': _mk(
        'Языки должны быть разными.', 'Languages must be different.',
        de='Die Sprachen müssen unterschiedlich sein.',
        fr='Les langues doivent être différentes.',
        es='Los idiomas deben ser diferentes.',
        it='Le lingue devono essere diverse.',
        pt='Os idiomas devem ser diferentes.',
        nl='Talen moeten verschillend zijn.',
        pl='Języki muszą być różne.',
        tr='Diller farklı olmalı.',
        cs='Jazyky musí být různé.',
        hu='A nyelveknek különbözniük kell.',
        ro='Limbile trebuie să fie diferite.',
        uk='Мови мають бути різними.',
        sv='Språken måste vara olika.',
        fi='Kielten on oltava erilaisia.',
        ja='言語は異なる必要があります。', ko='언어가 서로 달라야 합니다.',
        zh='语言必须不同。', ar='يجب أن تكون اللغات مختلفة.'),

    'Буфер пуст': _mk(
        'Буфер пуст', 'Clipboard is empty',
        de='Zwischenablage ist leer', fr='Presse-papiers vide',
        es='Portapapeles vacío', it='Appunti vuoti',
        pt='Área de transferência vazia', nl='Klembord is leeg',
        pl='Schowek jest pusty', tr='Pano boş',
        cs='Schránka je prázdná', hu='A vágólap üres',
        ro='Clipboardul este gol', uk='Буфер порожній',
        sv='Urklippet är tomt', fi='Leikepöytä on tyhjä',
        ja='クリップボードが空です', ko='클립보드가 비어 있습니다',
        zh='剪贴板为空', ar='الحافظة فارغة'),

    'Сначала выделите текст и нажмите Ctrl+C.\n\nПосле этого нажмите Ctrl+Shift+Q или Ctrl+Alt+Q.': _mk(
        'Сначала выделите текст и нажмите Ctrl+C.\n\nПосле этого нажмите Ctrl+Shift+Q или Ctrl+Alt+Q.',
        'First select text and press Ctrl+C.\n\nThen press Ctrl+Shift+Q or Ctrl+Alt+Q.',
        de='Wählen Sie zuerst Text aus und drücken Sie Strg+C.\n\nDrücken Sie dann Strg+Umschalt+Q oder Strg+Alt+Q.',
        fr="Sélectionnez d'abord le texte et appuyez sur Ctrl+C.\n\nAppuyez ensuite sur Ctrl+Maj+Q ou Ctrl+Alt+Q.",
        es='Primero seleccione el texto y pulse Ctrl+C.\n\nDespués pulse Ctrl+Mayús+Q o Ctrl+Alt+Q.',
        it='Prima seleziona il testo e premi Ctrl+C.\n\nPoi premi Ctrl+Maiusc+Q o Ctrl+Alt+Q.',
        pt='Primeiro selecione o texto e pressione Ctrl+C.\n\nDepois pressione Ctrl+Shift+Q ou Ctrl+Alt+Q.',
        nl='Selecteer eerst tekst en druk op Ctrl+C.\n\nDruk daarna op Ctrl+Shift+Q of Ctrl+Alt+Q.',
        pl='Najpierw zaznacz tekst i naciśnij Ctrl+C.\n\nNastępnie naciśnij Ctrl+Shift+Q lub Ctrl+Alt+Q.',
        tr='Önce metni seçin ve Ctrl+C tuşlayın.\n\nSonra Ctrl+Shift+Q veya Ctrl+Alt+Q tuşlayın.',
        cs='Nejprve vyberte text a stiskněte Ctrl+C.\n\nPoté stiskněte Ctrl+Shift+Q nebo Ctrl+Alt+Q.',
        hu='Először jelöljön ki szöveget, és nyomjon Ctrl+C-t.\n\nEzután nyomjon Ctrl+Shift+Q vagy Ctrl+Alt+Q billentyűt.',
        ro='Mai întâi selectați textul și apăsați Ctrl+C.\n\nApoi apăsați Ctrl+Shift+Q sau Ctrl+Alt+Q.',
        uk='Спочатку виділіть текст і натисніть Ctrl+C.\n\nПотім натисніть Ctrl+Shift+Q або Ctrl+Alt+Q.',
        sv='Markera text och tryck Ctrl+C först.\n\nTryck sedan Ctrl+Skift+Q eller Ctrl+Alt+Q.',
        fi='Valitse ensin teksti ja paina Ctrl+C.\n\nPaina sitten Ctrl+Vaihto+Q tai Ctrl+Alt+Q.',
        ja='先にテキストを選択し、Ctrl+Cを押してください。\n\n次にCtrl+Shift+QまたはCtrl+Alt+Qを押してください。',
        ko='먼저 텍스트를 선택하고 Ctrl+C를 누르세요.\n\n그다음 Ctrl+Shift+Q 또는 Ctrl+Alt+Q를 누르세요.',
        zh='先选中文本并按 Ctrl+C。\n\n然后按 Ctrl+Shift+Q 或 Ctrl+Alt+Q。',
        ar='أولاً حدد النص واضغط Ctrl+C.\n\nثم اضغط Ctrl+Shift+Q أو Ctrl+Alt+Q.'),

    'Скопируйте текст (Ctrl+C) и попробуйте снова.': _mk(
        'Скопируйте текст (Ctrl+C) и попробуйте снова.',
        'Copy the text (Ctrl+C) and try again.',
        de='Kopieren Sie den Text (Strg+C) und versuchen Sie es erneut.',
        fr='Copiez le texte (Ctrl+C) et réessayez.',
        es='Copie el texto (Ctrl+C) e inténtelo de nuevo.',
        it='Copia il testo (Ctrl+C) e riprova.',
        pt='Copie o texto (Ctrl+C) e tente novamente.',
        nl='Kopieer de tekst (Ctrl+C) en probeer opnieuw.',
        pl='Skopiuj tekst (Ctrl+C) i spróbuj ponownie.',
        tr='Metni kopyalayın (Ctrl+C) ve tekrar deneyin.',
        cs='Zkopírujte text (Ctrl+C) a zkuste to znovu.',
        hu='Másolja ki a szöveget (Ctrl+C), és próbálja újra.',
        ro='Copiați textul (Ctrl+C) și încercați din nou.',
        uk='Скопіюйте текст (Ctrl+C) і спробуйте знову.',
        sv='Kopiera texten (Ctrl+C) och försök igen.',
        fi='Kopioi teksti (Ctrl+C) ja yritä uudelleen.',
        ja='テキストをコピー（Ctrl+C）してもう一度お試しください。',
        ko='텍스트를 복사(Ctrl+C)한 후 다시 시도하세요.',
        zh='复制文本（Ctrl+C）后重试。',
        ar='انسخ النص (Ctrl+C) وحاول مرة أخرى.'),

    'Не удалось перевести': _mk(
        'Не удалось перевести', 'Translation failed',
        de='Übersetzung fehlgeschlagen', fr='Échec de la traduction',
        es='Error al traducir', it='Traduzione non riuscita',
        pt='Falha na tradução', nl='Vertaling mislukt',
        pl='Tłumaczenie nie powiodło się', tr='Çeviri başarısız',
        cs='Překlad se nezdařil', hu='A fordítás nem sikerült',
        ro='Traducerea a eșuat', uk='Не вдалося перекласти',
        sv='Översättning misslyckades', fi='Käännös epäonnistui',
        ja='翻訳に失敗しました', ko='번역 실패',
        zh='翻译失败', ar='فشلت الترجمة'),

    'Ни один сервис не ответил.\nПроверьте интернет.': _mk(
        'Ни один сервис не ответил.\nПроверьте интернет.',
        'No service responded.\nCheck your internet connection.',
        de='Kein Dienst hat geantwortet.\nPrüfen Sie die Internetverbindung.',
        fr="Aucun service n'a répondu.\nVérifiez votre connexion Internet.",
        es='Ningún servicio respondió.\nCompruebe su conexión a Internet.',
        it='Nessun servizio ha risposto.\nControlla la connessione Internet.',
        pt='Nenhum serviço respondeu.\nVerifique a ligação à Internet.',
        nl='Geen dienst reageerde.\nControleer uw internetverbinding.',
        pl='Żaden serwis nie odpowiedział.\nSprawdź połączenie z internetem.',
        tr='Hiçbir hizmet yanıt vermedi.\nİnternet bağlantınızı kontrol edin.',
        cs='Žádná služba neodpověděla.\nZkontrolujte připojení k internetu.',
        hu='Egyetlen szolgáltatás sem válaszolt.\nEllenőrizze az internetkapcsolatot.',
        ro='Niciun serviciu nu a răspuns.\nVerificați conexiunea la internet.',
        uk='Жоден сервіс не відповів.\nПеревірте інтернет-з’єднання.',
        sv='Ingen tjänst svarade.\nKontrollera internetanslutningen.',
        fi='Yksikään palvelu ei vastannut.\nTarkista internetyhteys.',
        ja='どのサービスも応答しませんでした。\nインターネット接続を確認してください。',
        ko='어떤 서비스도 응답하지 않았습니다.\n인터넷 연결을 확인하세요.',
        zh='没有任何服务响应。\n请检查网络连接。',
        ar='لم يستجب أي خدمة.\nتحقق من اتصالك بالإنترنت.'),

    'Понятно': _mk(
        'Понятно', 'OK',
        de='Verstanden', fr='OK', es='Entendido', it='OK',
        pt='OK', nl='Begrepen', pl='OK', tr='Tamam',
        cs='OK', hu='Rendben', ro='OK', uk='Зрозуміло',
        sv='OK', fi='OK',
        ja='了解', ko='확인', zh='好的', ar='حسنًا'),

    'Не удалось очистить буфер': _mk(
        'Не удалось очистить буфер', 'Failed to clear clipboard',
        de='Zwischenablage konnte nicht geleert werden',
        fr='Échec du vidage du presse-papiers',
        es='No se pudo borrar el portapapeles',
        it='Impossibile cancellare gli appunti',
        pt='Falha ao limpar a área de transferência',
        nl='Klembord kon niet worden gewist',
        pl='Nie udało się wyczyścić schowka',
        tr='Pano temizlenemedi',
        cs='Schránku se nepodařilo vymazat',
        hu='A vágólap nem törölhető',
        ro='Clipboardul nu a putut fi golit',
        uk='Не вдалося очистити буфер',
        sv='Kunde inte rensa urklippet',
        fi='Leikepöydän tyhjennys epäonnistui',
        ja='クリップボードを消去できませんでした',
        ko='클립보드를 지우지 못했습니다',
        zh='无法清空剪贴板', ar='فشل مسح الحافظة'),

    'Буфер обмена сейчас занят другой программой.\nПопробуйте нажать кнопку ещё раз.': _mk(
        'Буфер обмена сейчас занят другой программой.\nПопробуйте нажать кнопку ещё раз.',
        'The clipboard is currently used by another program.\nTry pressing the button again.',
        de='Die Zwischenablage wird derzeit von einem anderen Programm verwendet.\nVersuchen Sie es erneut.',
        fr="Le presse-papiers est actuellement utilisé par un autre programme.\nRéessayez.",
        es='Otro programa está usando el portapapeles.\nInténtelo de nuevo.',
        it='Gli appunti sono attualmente usati da un altro programma.\nRiprova.',
        pt='A área de transferência está a ser usada por outro programa.\nTente novamente.',
        nl='Het klembord wordt momenteel door een ander programma gebruikt.\nProbeer het opnieuw.',
        pl='Schowek jest aktualnie używany przez inny program.\nSpróbuj ponownie.',
        tr='Pano şu anda başka bir program tarafından kullanılıyor.\nTekrar deneyin.',
        cs='Schránku právě používá jiný program.\nZkuste to znovu.',
        hu='A vágólapot éppen egy másik program használja.\nPróbálja újra.',
        ro='Clipboardul este folosit momentan de alt program.\nÎncercați din nou.',
        uk='Буфер обміну зараз використовує інша програма.\nСпробуйте ще раз.',
        sv='Urklippet används för närvarande av ett annat program.\nFörsök igen.',
        fi='Toinen ohjelma käyttää leikepöytää parhaillaan.\nYritä uudelleen.',
        ja='クリップボードは現在他のプログラムが使用中です。\nもう一度お試しください。',
        ko='클립보드가 다른 프로그램에서 사용 중입니다.\n다시 시도하세요.',
        zh='剪贴板正被其他程序占用。\n请重试。',
        ar='الحافظة مستخدمة حاليًا بواسطة برنامج آخر.\nحاول مرة أخرى.'),

    'Системный буфер обмена очищен': _mk(
        'Системный буфер обмена очищен', 'System clipboard cleared',
        de='System-Zwischenablage geleert', fr='Presse-papiers système vidé',
        es='Portapapeles del sistema borrado', it='Appunti di sistema cancellati',
        pt='Área de transferência do sistema limpa',
        nl='Systeemklembord gewist', pl='Schowek systemowy wyczyszczony',
        tr='Sistem panosu temizlendi', cs='Systémová schránka vymazána',
        hu='Rendszervágólap törölve', ro='Clipboardul sistemului a fost golit',
        uk='Системний буфер очищено', sv='Systemurklipp rensat',
        fi='Järjestelmän leikepöytä tyhjennetty',
        ja='システムクリップボードを消去しました',
        ko='시스템 클립보드가 지워졌습니다',
        zh='系统剪贴板已清空', ar='تم مسح حافظة النظام'),

    '✓  Буфер уже очищен': _mk(
        '✓  Буфер уже очищен', '✓  Clipboard already empty',
        de='✓  Zwischenablage bereits leer', fr='✓  Presse-papiers déjà vide',
        es='✓  Portapapeles ya vacío', it='✓  Appunti già vuoti',
        pt='✓  Área de transferência já vazia', nl='✓  Klembord al leeg',
        pl='✓  Schowek już pusty', tr='✓  Pano zaten boş',
        cs='✓  Schránka již prázdná', hu='✓  A vágólap már üres',
        ro='✓  Clipboardul este deja gol', uk='✓  Буфер уже порожній',
        sv='✓  Urklippet är redan tomt', fi='✓  Leikepöytä on jo tyhjä',
        ja='✓  クリップボードは既に空です',
        ko='✓  클립보드가 이미 비어 있습니다',
        zh='✓  剪贴板已为空', ar='✓  الحافظة فارغة بالفعل'),

    '✓  Буфер очищен': _mk(
        '✓  Буфер очищен', '✓  Clipboard cleared',
        de='✓  Zwischenablage geleert', fr='✓  Presse-papiers vidé',
        es='✓  Portapapeles borrado', it='✓  Appunti cancellati',
        pt='✓  Área de transferência limpa', nl='✓  Klembord gewist',
        pl='✓  Schowek wyczyszczony', tr='✓  Pano temizlendi',
        cs='✓  Schránka vymazána', hu='✓  Vágólap törölve',
        ro='✓  Clipboard golit', uk='✓  Буфер очищено',
        sv='✓  Urklippet rensat', fi='✓  Leikepöytä tyhjennetty',
        ja='✓  クリップボードを消去しました',
        ko='✓  클립보드를 지웠습니다',
        zh='✓  剪贴板已清空', ar='✓  تم مسح الحافظة'),

    'Очистка буфера: буфер уже пуст': _mk(
        'Очистка буфера: буфер уже пуст',
        'Clipboard clearing: clipboard is already empty',
        de='Zwischenablage leeren: bereits leer',
        fr='Vidage du presse-papiers : déjà vide',
        es='Borrado del portapapeles: ya vacío',
        it='Cancellazione appunti: già vuoti',
        pt='Limpeza da área de transferência: já vazia',
        nl='Klembord wissen: al leeg',
        pl='Czyszczenie schowka: już pusty',
        tr='Pano temizleme: zaten boş',
        cs='Vymazání schránky: již prázdná',
        hu='Vágólap törlése: már üres',
        ro='Golire clipboard: deja gol',
        uk='Очищення буфера: буфер уже порожній',
        sv='Rensa urklipp: redan tomt',
        fi='Leikepöydän tyhjennys: jo tyhjä',
        ja='クリップボードを消去：既に空です',
        ko='클립보드 지우기: 이미 비어 있음',
        zh='清空剪贴板：已为空', ar='مسح الحافظة: فارغة بالفعل'),

    '(журнал пуст)': _mk(
        '(журнал пуст)', '(log is empty)',
        de='(Protokoll ist leer)', fr='(journal vide)',
        es='(registro vacío)', it='(registro vuoto)',
        pt='(registo vazio)', nl='(logboek is leeg)',
        pl='(dziennik pusty)', tr='(günlük boş)',
        cs='(protokol je prázdný)', hu='(a napló üres)',
        ro='(jurnal gol)', uk='(журнал порожній)',
        sv='(loggen är tom)', fi='(loki on tyhjä)',
        ja='（ログは空です）', ko='(로그 비어 있음)',
        zh='（日志为空）', ar='(السجل فارغ)'),

    '⏳ Проверка хоткеев…': _mk(
        '⏳ Проверка хоткеев…', '⏳ Checking hotkeys…',
        de='⏳ Hotkeys werden geprüft…', fr='⏳ Vérification des raccourcis…',
        es='⏳ Comprobando atajos…', it='⏳ Verifica scorciatoie…',
        pt='⏳ A verificar atalhos…', nl='⏳ Sneltoetsen controleren…',
        pl='⏳ Sprawdzanie skrótów…', tr='⏳ Kısayollar kontrol ediliyor…',
        cs='⏳ Kontrola klávesových zkratek…', hu='⏳ Gyorsbillentyűk ellenőrzése…',
        ro='⏳ Se verifică comenzile rapide…', uk='⏳ Перевірка хоткеїв…',
        sv='⏳ Kontrollerar snabbtangenter…', fi='⏳ Tarkistetaan pikakuvakkeita…',
        ja='⏳ ホットキーを確認中…', ko='⏳ 단축키 확인 중…',
        zh='⏳ 正在检查快捷键…', ar='⏳ جارٍ التحقق من مفاتيح الاختصار…'),

    '✓ Хоткеи активны:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q': _mk(
        '✓ Хоткеи активны:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        '✓ Hotkeys active:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        de='✓ Hotkeys aktiv:\n   Strg+Umschalt+Q  /  Strg+Alt+Q',
        fr='✓ Raccourcis actifs :\n   Ctrl+Maj+Q  /  Ctrl+Alt+Q',
        es='✓ Atajos activos:\n   Ctrl+Mayús+Q  /  Ctrl+Alt+Q',
        it='✓ Scorciatoie attive:\n   Ctrl+Maiusc+Q  /  Ctrl+Alt+Q',
        pt='✓ Atalhos ativos:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        nl='✓ Sneltoetsen actief:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        pl='✓ Skróty aktywne:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        tr='✓ Kısayollar etkin:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        cs='✓ Klávesové zkratky aktivní:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        hu='✓ Gyorsbillentyűk aktívak:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        ro='✓ Comenzi rapide active:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        uk='✓ Хоткеї активні:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        sv='✓ Snabbtangenter aktiva:\n   Ctrl+Skift+Q  /  Ctrl+Alt+Q',
        fi='✓ Pikakuvakkeet käytössä:\n   Ctrl+Vaihto+Q  /  Ctrl+Alt+Q',
        ja='✓ ホットキー有効:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        ko='✓ 단축키 활성:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        zh='✓ 快捷键已启用：\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q',
        ar='✓ مفاتيح الاختصار مفعّلة:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q'),

    '✓ Активен Ctrl+Shift+Q': _mk(
        '✓ Активен Ctrl+Shift+Q', '✓ Ctrl+Shift+Q is active',
        de='✓ Strg+Umschalt+Q ist aktiv', fr='✓ Ctrl+Maj+Q est actif',
        es='✓ Ctrl+Mayús+Q está activo', it='✓ Ctrl+Maiusc+Q è attivo',
        pt='✓ Ctrl+Shift+Q está ativo', nl='✓ Ctrl+Shift+Q is actief',
        pl='✓ Ctrl+Shift+Q jest aktywny', tr='✓ Ctrl+Shift+Q etkin',
        cs='✓ Ctrl+Shift+Q je aktivní', hu='✓ Ctrl+Shift+Q aktív',
        ro='✓ Ctrl+Shift+Q este activ', uk='✓ Активний Ctrl+Shift+Q',
        sv='✓ Ctrl+Skift+Q är aktiv', fi='✓ Ctrl+Vaihto+Q on käytössä',
        ja='✓ Ctrl+Shift+Q が有効', ko='✓ Ctrl+Shift+Q 사용 가능',
        zh='✓ Ctrl+Shift+Q 已启用', ar='✓ Ctrl+Shift+Q مفعّل'),

    '✓ Активен Ctrl+Alt+Q': _mk(
        '✓ Активен Ctrl+Alt+Q', '✓ Ctrl+Alt+Q is active',
        de='✓ Strg+Alt+Q ist aktiv', fr='✓ Ctrl+Alt+Q est actif',
        es='✓ Ctrl+Alt+Q está activo', it='✓ Ctrl+Alt+Q è attivo',
        pt='✓ Ctrl+Alt+Q está ativo', nl='✓ Ctrl+Alt+Q is actief',
        pl='✓ Ctrl+Alt+Q jest aktywny', tr='✓ Ctrl+Alt+Q etkin',
        cs='✓ Ctrl+Alt+Q je aktivní', hu='✓ Ctrl+Alt+Q aktív',
        ro='✓ Ctrl+Alt+Q este activ', uk='✓ Активний Ctrl+Alt+Q',
        sv='✓ Ctrl+Alt+Q är aktiv', fi='✓ Ctrl+Alt+Q on käytössä',
        ja='✓ Ctrl+Alt+Q が有効', ko='✓ Ctrl+Alt+Q 사용 가능',
        zh='✓ Ctrl+Alt+Q 已启用', ar='✓ Ctrl+Alt+Q مفعّل'),

    '❌ Хоткеи заняты. Используйте Ctrl+C → «📋 Перевести буфер».': _mk(
        '❌ Хоткеи заняты. Используйте Ctrl+C → «📋 Перевести буфер».',
        '❌ Hotkeys are taken. Use Ctrl+C → "📋 Translate clipboard".',
        de='❌ Hotkeys sind belegt. Nutzen Sie Strg+C → „📋 Zwischenablage übersetzen".',
        fr='❌ Raccourcis occupés. Utilisez Ctrl+C → « 📋 Traduire le presse-papiers ».',
        es='❌ Atajos ocupados. Use Ctrl+C → «📋 Traducir portapapeles».',
        it='❌ Scorciatoie occupate. Usa Ctrl+C → «📋 Traduci appunti».',
        pt='❌ Atalhos ocupados. Use Ctrl+C → «📋 Traduzir área de transferência».',
        nl='❌ Sneltoetsen bezet. Gebruik Ctrl+C → "📋 Klembord vertalen".',
        pl='❌ Skróty zajęte. Użyj Ctrl+C → „📋 Przetłumacz schowek".',
        tr='❌ Kısayollar kullanımda. Ctrl+C → "📋 Panoyu çevir" kullanın.',
        cs='❌ Klávesové zkratky obsazeny. Použijte Ctrl+C → „📋 Přeložit schránku".',
        hu='❌ A gyorsbillentyűk foglaltak. Használja: Ctrl+C → „📋 Vágólap fordítása".',
        ro='❌ Comenzi rapide ocupate. Folosiți Ctrl+C → „📋 Tradu clipboardul”.',
        uk='❌ Хоткеї зайняті. Використайте Ctrl+C → «📋 Перекласти буфер».',
        sv='❌ Snabbtangenter upptagna. Använd Ctrl+C → "📋 Översätt urklipp".',
        fi='❌ Pikakuvakkeet varattu. Käytä Ctrl+C → "📋 Käännä leikepöytä".',
        ja='❌ ホットキーが使用中です。Ctrl+C → 「📋 クリップボードを翻訳」を使用してください。',
        ko='❌ 단축키가 사용 중입니다. Ctrl+C → "📋 클립보드 번역"을 사용하세요.',
        zh='❌ 快捷键已被占用。请使用 Ctrl+C → “📋 翻译剪贴板”。',
        ar='❌ مفاتيح الاختصار مستخدمة. استخدم Ctrl+C → "📋 ترجمة الحافظة".'),

    'Показать окно': _mk(
        'Показать окно', 'Show window',
        de='Fenster anzeigen', fr='Afficher la fenêtre',
        es='Mostrar ventana', it='Mostra finestra',
        pt='Mostrar janela', nl='Venster tonen',
        pl='Pokaż okno', tr='Pencereyi göster',
        cs='Zobrazit okno', hu='Ablak megjelenítése',
        ro='Arată fereastra', uk='Показати вікно',
        sv='Visa fönster', fi='Näytä ikkuna',
        ja='ウィンドウを表示', ko='창 표시',
        zh='显示窗口', ar='إظهار النافذة'),

    'Перевести буфер': _mk(
        'Перевести буфер', 'Translate clipboard',
        de='Zwischenablage übersetzen', fr='Traduire le presse-papiers',
        es='Traducir portapapeles', it='Traduci appunti',
        pt='Traduzir área de transferência', nl='Klembord vertalen',
        pl='Przetłumacz schowek', tr='Panoyu çevir',
        cs='Přeložit schránku', hu='Vágólap fordítása',
        ro='Tradu clipboardul', uk='Перекласти буфер',
        sv='Översätt urklipp', fi='Käännä leikepöytä',
        ja='クリップボードを翻訳', ko='클립보드 번역',
        zh='翻译剪贴板', ar='ترجمة الحافظة'),

    'Поменять языки': _mk(
        'Поменять языки', 'Swap languages',
        de='Sprachen tauschen', fr='Échanger les langues',
        es='Intercambiar idiomas', it='Scambia lingue',
        pt='Trocar idiomas', nl='Talen omwisselen',
        pl='Zamień języki', tr='Dilleri değiştir',
        cs='Prohodit jazyky', hu='Nyelvek cseréje',
        ro='Schimbă limbile', uk='Поміняти мови',
        sv='Byt språk', fi='Vaihda kielet',
        ja='言語を入れ替え', ko='언어 바꾸기',
        zh='交换语言', ar='تبديل اللغات'),

    'Автозапуск Windows': _mk(
        'Автозапуск Windows', 'Windows autorun',
        de='Windows-Autostart', fr='Démarrage Windows',
        es='Inicio automático Windows', it='Avvio automatico Windows',
        pt='Arranque automático Windows', nl='Windows-autostart',
        pl='Autostart Windows', tr='Windows otomatik başlat',
        cs='Autostart Windows', hu='Windows automatikus indítás',
        ro='Pornire automată Windows', uk='Автозапуск Windows',
        sv='Windows-autostart', fi='Windows-automaattikäynnistys',
        ja='Windows 自動起動', ko='Windows 자동 실행',
        zh='Windows 自启动', ar='التشغيل التلقائي مع Windows'),

    'Через реестр': _mk(
        'Через реестр', 'Via registry',
        de='Über Registry', fr='Via le registre',
        es='Vía registro', it='Tramite registro',
        pt='Via registo', nl='Via register',
        pl='Przez rejestr', tr='Kayıt defteri ile',
        cs='Přes registr', hu='Rendszerleíró adatbázison át',
        ro='Prin registru', uk='Через реєстр',
        sv='Via registret', fi='Rekisterin kautta',
        ja='レジストリ経由', ko='레지스트리 통해',
        zh='通过注册表', ar='عبر السجل'),

    'Через папку Startup': _mk(
        'Через папку Startup', 'Via Startup folder',
        de='Über Startup-Ordner', fr='Via dossier Démarrage',
        es='Vía carpeta Inicio', it='Tramite cartella Esecuzione automatica',
        pt='Via pasta Inicializar', nl='Via opstartmap',
        pl='Przez folder Startup', tr='Başlangıç klasörü ile',
        cs='Přes složku Po spuštění', hu='Indító mappán keresztül',
        ro='Prin folderul Startup', uk='Через папку Startup',
        sv='Via Startup-mappen', fi='Startup-kansion kautta',
        ja='Startup フォルダ経由', ko='시작프로그램 폴더 통해',
        zh='通过 Startup 文件夹', ar='عبر مجلد بدء التشغيل'),

    'Отключить автозагрузку': _mk(
        'Отключить автозагрузку', 'Disable autorun',
        de='Autostart deaktivieren', fr='Désactiver le démarrage auto',
        es='Desactivar inicio automático', it='Disabilita avvio automatico',
        pt='Desativar arranque automático', nl='Autostart uitschakelen',
        pl='Wyłącz autostart', tr='Otomatik başlatmayı kapat',
        cs='Zakázat autostart', hu='Autostart kikapcsolása',
        ro='Dezactivează pornirea automată', uk='Вимкнути автозапуск',
        sv='Inaktivera autostart', fi='Poista automaattikäynnistys',
        ja='自動起動を無効化', ko='자동 실행 비활성화',
        zh='禁用自启动', ar='تعطيل التشغيل التلقائي'),

    'Запускать вместе с Windows свёрнутым в трей': _mk(
        'Запускать вместе с Windows свёрнутым в трей',
        'Start with Windows minimized to tray',
        de='Mit Windows minimiert im Infobereich starten',
        fr='Démarrer avec Windows réduit dans la barre',
        es='Iniciar con Windows minimizado en la bandeja',
        it='Avvia con Windows ridotto nella barra',
        pt='Iniciar com o Windows minimizado na bandeja',
        nl='Starten met Windows, geminimaliseerd naar systeemvak',
        pl='Uruchamiaj z Windows zminimalizowany w zasobniku',
        tr='Windows ile tepsiye küçültülmüş başlat',
        cs='Spouštět s Windows minimalizovaně v oznamovací oblasti',
        hu='Indítás a Windows-szal a tálcára kicsinyítve',
        ro='Pornește cu Windows minimizat în tavă',
        uk='Запускати разом з Windows згорнутим у трей',
        sv='Starta med Windows minimerad i aktivitetsfältet',
        fi='Käynnistä Windowsin mukana ilmaisinalueelle pienennettynä',
        ja='Windows と同時にトレイに最小化して起動',
        ko='Windows 시작 시 트레이로 최소화하여 실행',
        zh='随 Windows 启动并最小化到托盘',
        ar='التشغيل مع Windows مصغرًا في شريط النظام'),

    'Поменять языки местами': _mk(
        'Поменять языки местами', 'Swap languages',
        de='Sprachen tauschen', fr='Échanger les langues',
        es='Intercambiar idiomas', it='Scambia lingue',
        pt='Trocar idiomas', nl='Talen omwisselen',
        pl='Zamień języki miejscami', tr='Dilleri yer değiştir',
        cs='Prohodit jazyky', hu='Nyelvek felcserélése',
        ro='Inversează limbile', uk='Поміняти мови місцями',
        sv='Byt plats på språk', fi='Vaihda kielten paikkaa',
        ja='言語を入れ替える', ko='언어 위치 바꾸기',
        zh='交换语言', ar='تبديل أماكن اللغات'),

    'Перевести то, что в буфере обмена.\nСначала Ctrl+C, затем эта кнопка.': _mk(
        'Перевести то, что в буфере обмена.\nСначала Ctrl+C, затем эта кнопка.',
        'Translate what is in the clipboard.\nPress Ctrl+C first, then this button.',
        de='Übersetzt den Inhalt der Zwischenablage.\nErst Strg+C, dann diese Taste.',
        fr="Traduit le contenu du presse-papiers.\nD'abord Ctrl+C, puis ce bouton.",
        es='Traduce lo que hay en el portapapeles.\nPrimero Ctrl+C, luego este botón.',
        it='Traduce ciò che è negli appunti.\nPrima Ctrl+C, poi questo pulsante.',
        pt='Traduz o que está na área de transferência.\nPrimeiro Ctrl+C, depois este botão.',
        nl='Vertaalt wat op het klembord staat.\nEerst Ctrl+C, dan deze knop.',
        pl='Tłumaczy zawartość schowka.\nNajpierw Ctrl+C, potem ten przycisk.',
        tr='Panodaki içeriği çevirir.\nÖnce Ctrl+C, sonra bu düğme.',
        cs='Přeloží obsah schránky.\nNejprve Ctrl+C, poté toto tlačítko.',
        hu='Lefordítja a vágólap tartalmát.\nElőször Ctrl+C, aztán ez a gomb.',
        ro='Traduce ce este în clipboard.\nMai întâi Ctrl+C, apoi acest buton.',
        uk='Перекладає те, що в буфері обміну.\nСпочатку Ctrl+C, потім ця кнопка.',
        sv='Översätter det som finns i urklippet.\nTryck Ctrl+C först, sedan denna knapp.',
        fi='Kääntää leikepöydän sisällön.\nPaina ensin Ctrl+C, sitten tätä painiketta.',
        ja='クリップボードの内容を翻訳します。\n先にCtrl+C、次にこのボタンを押してください。',
        ko='클립보드에 있는 내용을 번역합니다.\n먼저 Ctrl+C, 그다음 이 버튼을 누르세요.',
        zh='翻译剪贴板中的内容。\n先按 Ctrl+C，再按此按钮。',
        ar='يترجم ما في الحافظة.\nاضغط Ctrl+C أولاً، ثم هذا الزر.'),

    'Полностью очистить системный буфер обмена Windows': _mk(
        'Полностью очистить системный буфер обмена Windows',
        'Completely clear the Windows system clipboard',
        de='Die Windows-Systemzwischenablage vollständig leeren',
        fr='Vider complètement le presse-papiers système Windows',
        es='Borrar completamente el portapapeles del sistema Windows',
        it='Cancella completamente gli appunti di sistema di Windows',
        pt='Limpar completamente a área de transferência do sistema Windows',
        nl='Het Windows-systeemklembord volledig wissen',
        pl='Całkowicie wyczyść schowek systemowy Windows',
        tr='Windows sistem panosunu tamamen temizle',
        cs='Zcela vymazat systémovou schránku Windows',
        hu='A Windows rendszervágólap teljes törlése',
        ro='Golește complet clipboardul de sistem Windows',
        uk='Повністю очистити системний буфер обміну Windows',
        sv='Rensa Windows systemurklipp helt',
        fi='Tyhjennä Windowsin järjestelmän leikepöytä kokonaan',
        ja='Windows のシステムクリップボードを完全に消去します',
        ko='Windows 시스템 클립보드를 완전히 지웁니다',
        zh='完全清空 Windows 系统剪贴板',
        ar='مسح حافظة نظام Windows بالكامل'),

    'Очистить только текст для перевода': _mk(
        'Очистить только текст для перевода',
        'Clear only the source text',
        de='Nur den zu übersetzenden Text leeren',
        fr='Effacer uniquement le texte source',
        es='Borrar solo el texto de origen',
        it='Cancella solo il testo di origine',
        pt='Limpar apenas o texto de origem',
        nl='Alleen de brontekst wissen',
        pl='Wyczyść tylko tekst źródłowy',
        tr='Yalnızca kaynak metni temizle',
        cs='Vymazat pouze zdrojový text',
        hu='Csak a forrásszöveg törlése',
        ro='Golește doar textul sursă',
        uk='Очистити лише вихідний текст',
        sv='Rensa endast källtexten',
        fi='Tyhjennä vain lähdeteksti',
        ja='翻訳元のテキストのみを消去します',
        ko='번역할 원문만 지웁니다',
        zh='仅清空要翻译的文本',
        ar='مسح النص المصدر فقط'),

    'Очистить только уже переведённый текст': _mk(
        'Очистить только уже переведённый текст',
        'Clear only the translated text',
        de='Nur den übersetzten Text leeren',
        fr='Effacer uniquement le texte traduit',
        es='Borrar solo el texto traducido',
        it='Cancella solo il testo tradotto',
        pt='Limpar apenas o texto traduzido',
        nl='Alleen de vertaalde tekst wissen',
        pl='Wyczyść tylko przetłumaczony tekst',
        tr='Yalnızca çevrilmiş metni temizle',
        cs='Vymazat pouze přeložený text',
        hu='Csak a lefordított szöveg törlése',
        ro='Golește doar textul tradus',
        uk='Очистити лише перекладений текст',
        sv='Rensa endast den översatta texten',
        fi='Tyhjennä vain käännetty teksti',
        ja='翻訳済みのテキストのみを消去します',
        ko='이미 번역된 텍스트만 지웁니다',
        zh='仅清空已翻译的文本',
        ar='مسح النص المترجم فقط'),

    '1. Выделите текст в любой программе.\n2. Нажмите Ctrl+C, чтобы скопировать его.\n3. Нажмите хоткей — переводчик возьмёт текст из буфера и переведёт его.\n\nХоткеи:\n  Ctrl+Shift+Q — быстро перевести текст из буфера\n  Ctrl+Alt+Q   — альтернативный хоткей для той же функции\n\nВажно: хоткей не копирует текст сам. Сначала обязательно нажмите Ctrl+C.\nEsc в окне быстрого перевода — закрыть окно.': _mk(
        '1. Выделите текст в любой программе.\n2. Нажмите Ctrl+C, чтобы скопировать его.\n3. Нажмите хоткей — переводчик возьмёт текст из буфера и переведёт его.\n\nХоткеи:\n  Ctrl+Shift+Q — быстро перевести текст из буфера\n  Ctrl+Alt+Q   — альтернативный хоткей для той же функции\n\nВажно: хоткей не копирует текст сам. Сначала обязательно нажмите Ctrl+C.\nEsc в окне быстрого перевода — закрыть окно.',
        '1. Select text in any program.\n2. Press Ctrl+C to copy it.\n3. Press the hotkey — the translator will take the text from the clipboard and translate it.\n\nHotkeys:\n  Ctrl+Shift+Q — quickly translate from clipboard\n  Ctrl+Alt+Q   — alternative hotkey for the same action\n\nImportant: the hotkey does not copy text itself. Always press Ctrl+C first.\nEsc in the quick translation window closes it.',
        de='1. Markieren Sie Text in einem beliebigen Programm.\n2. Drücken Sie Strg+C zum Kopieren.\n3. Drücken Sie den Hotkey — der Übersetzer holt den Text aus der Zwischenablage.\n\nHotkeys:\n  Strg+Umschalt+Q — schnell aus der Zwischenablage übersetzen\n  Strg+Alt+Q      — alternativer Hotkey für dieselbe Funktion\n\nWichtig: Der Hotkey kopiert den Text nicht selbst. Erst Strg+C drücken.\nEsc im Schnellübersetzungsfenster schließt es.',
        fr="1. Sélectionnez du texte dans n'importe quel programme.\n2. Appuyez sur Ctrl+C pour le copier.\n3. Appuyez sur le raccourci — le traducteur prendra le texte du presse-papiers.\n\nRaccourcis :\n  Ctrl+Maj+Q — traduire rapidement depuis le presse-papiers\n  Ctrl+Alt+Q — raccourci alternatif pour la même action\n\nImportant : le raccourci ne copie pas le texte. Appuyez toujours d'abord sur Ctrl+C.\nÉchap dans la fenêtre de traduction rapide la ferme.",
        es='1. Seleccione texto en cualquier programa.\n2. Pulse Ctrl+C para copiarlo.\n3. Pulse el atajo — el traductor tomará el texto del portapapeles y lo traducirá.\n\nAtajos:\n  Ctrl+Mayús+Q — traducir rápidamente desde el portapapeles\n  Ctrl+Alt+Q   — atajo alternativo para la misma acción\n\nImportante: el atajo no copia el texto. Pulse siempre Ctrl+C primero.\nEsc en la ventana de traducción rápida la cierra.',
        it='1. Seleziona il testo in qualsiasi programma.\n2. Premi Ctrl+C per copiarlo.\n3. Premi la scorciatoia — il traduttore prenderà il testo dagli appunti.\n\nScorciatoie:\n  Ctrl+Maiusc+Q — traduci rapidamente dagli appunti\n  Ctrl+Alt+Q    — scorciatoia alternativa per la stessa azione\n\nImportante: la scorciatoia non copia il testo. Premi sempre prima Ctrl+C.\nEsc nella finestra di traduzione rapida la chiude.',
        pt='1. Selecione texto em qualquer programa.\n2. Pressione Ctrl+C para copiá-lo.\n3. Pressione o atalho — o tradutor pegará o texto da área de transferência.\n\nAtalhos:\n  Ctrl+Shift+Q — traduzir rapidamente da área de transferência\n  Ctrl+Alt+Q   — atalho alternativo para a mesma ação\n\nImportante: o atalho não copia o texto. Pressione sempre Ctrl+C primeiro.\nEsc na janela de tradução rápida fecha-a.',
        nl='1. Selecteer tekst in een willekeurig programma.\n2. Druk op Ctrl+C om te kopiëren.\n3. Druk op de sneltoets — de vertaler haalt de tekst uit het klembord.\n\nSneltoetsen:\n  Ctrl+Shift+Q — snel vertalen vanuit klembord\n  Ctrl+Alt+Q   — alternatieve sneltoets voor dezelfde actie\n\nBelangrijk: de sneltoets kopieert de tekst niet. Druk altijd eerst Ctrl+C.\nEsc in het snelle vertaalvenster sluit het.',
        pl='1. Zaznacz tekst w dowolnym programie.\n2. Naciśnij Ctrl+C, aby go skopiować.\n3. Naciśnij skrót — tłumacz pobierze tekst ze schowka i przetłumaczy.\n\nSkróty:\n  Ctrl+Shift+Q — szybkie tłumaczenie ze schowka\n  Ctrl+Alt+Q   — alternatywny skrót dla tej samej funkcji\n\nWażne: skrót sam nie kopiuje tekstu. Zawsze najpierw naciśnij Ctrl+C.\nEsc w oknie szybkiego tłumaczenia zamyka je.',
        tr='1. Herhangi bir programda metni seçin.\n2. Kopyalamak için Ctrl+C tuşlayın.\n3. Kısayola basın — çevirmen metni panodan alıp çevirir.\n\nKısayollar:\n  Ctrl+Shift+Q — panodan hızlı çeviri\n  Ctrl+Alt+Q   — aynı işlev için alternatif kısayol\n\nÖnemli: Kısayol metni kendisi kopyalamaz. Önce mutlaka Ctrl+C tuşlayın.\nHızlı çeviri penceresinde Esc kapatır.',
        cs='1. Vyberte text v libovolném programu.\n2. Stiskněte Ctrl+C pro zkopírování.\n3. Stiskněte klávesovou zkratku — překladač vezme text ze schránky.\n\nZkratky:\n  Ctrl+Shift+Q — rychlý překlad ze schránky\n  Ctrl+Alt+Q   — alternativní zkratka pro stejnou funkci\n\nDůležité: zkratka text sama nekopíruje. Vždy nejprve stiskněte Ctrl+C.\nEsc v okně rychlého překladu jej zavře.',
        hu='1. Jelöljön ki szöveget bármely programban.\n2. Nyomjon Ctrl+C-t a másoláshoz.\n3. Nyomja meg a gyorsbillentyűt — a fordító a vágólapról veszi a szöveget.\n\nGyorsbillentyűk:\n  Ctrl+Shift+Q — gyors fordítás a vágólapról\n  Ctrl+Alt+Q   — alternatív gyorsbillentyű ugyanahhoz\n\nFontos: a gyorsbillentyű nem másolja a szöveget. Először mindig Ctrl+C.\nEsc a gyorsfordítás ablakban bezárja.',
        ro='1. Selectați text în orice program.\n2. Apăsați Ctrl+C pentru a-l copia.\n3. Apăsați combinația — traducătorul va lua textul din clipboard.\n\nCombinații:\n  Ctrl+Shift+Q — traducere rapidă din clipboard\n  Ctrl+Alt+Q   — combinație alternativă pentru aceeași funcție\n\nImportant: combinația nu copiază textul. Apăsați întâi Ctrl+C.\nEsc în fereastra de traducere rapidă o închide.',
        uk='1. Виділіть текст у будь-якій програмі.\n2. Натисніть Ctrl+C, щоб скопіювати.\n3. Натисніть хоткей — перекладач візьме текст із буфера й перекладе.\n\nХоткеї:\n  Ctrl+Shift+Q — швидкий переклад із буфера\n  Ctrl+Alt+Q   — альтернативний хоткей для тієї ж функції\n\nВажливо: хоткей не копіює текст сам. Спершу обов’язково натисніть Ctrl+C.\nEsc у вікні швидкого перекладу закриває його.',
        sv='1. Markera text i valfritt program.\n2. Tryck Ctrl+C för att kopiera.\n3. Tryck på snabbtangenten — översättaren tar texten från urklippet.\n\nSnabbtangenter:\n  Ctrl+Skift+Q — snabb översättning från urklipp\n  Ctrl+Alt+Q   — alternativ snabbtangent för samma funktion\n\nViktigt: snabbtangenten kopierar inte texten själv. Tryck alltid Ctrl+C först.\nEsc i snabböversättningsfönstret stänger det.',
        fi='1. Valitse teksti missä tahansa ohjelmassa.\n2. Paina Ctrl+C kopioidaksesi.\n3. Paina pikakuvaketta — kääntäjä ottaa tekstin leikepöydältä.\n\nPikakuvakkeet:\n  Ctrl+Vaihto+Q — nopea käännös leikepöydältä\n  Ctrl+Alt+Q    — vaihtoehtoinen pikakuvake samaan toimintoon\n\nTärkeää: pikakuvake ei kopioi tekstiä. Paina aina ensin Ctrl+C.\nEsc nopean käännöksen ikkunassa sulkee sen.',
        ja='1. 任意のプログラムでテキストを選択します。\n2. Ctrl+C を押してコピーします。\n3. ホットキーを押すと、翻訳ツールがクリップボードからテキストを取り出して翻訳します。\n\nホットキー:\n  Ctrl+Shift+Q — クリップボードからすばやく翻訳\n  Ctrl+Alt+Q   — 同じ機能の代替ホットキー\n\n重要: ホットキー自体はテキストをコピーしません。必ず先に Ctrl+C を押してください。\nクイック翻訳ウィンドウでは Esc で閉じます。',
        ko='1. 아무 프로그램에서 텍스트를 선택하세요.\n2. Ctrl+C로 복사하세요.\n3. 단축키를 누르면 번역기가 클립보드에서 텍스트를 가져와 번역합니다.\n\n단축키:\n  Ctrl+Shift+Q — 클립보드에서 빠르게 번역\n  Ctrl+Alt+Q   — 같은 기능의 대체 단축키\n\n중요: 단축키는 텍스트를 복사하지 않습니다. 항상 먼저 Ctrl+C를 누르세요.\n빠른 번역 창에서 Esc로 닫습니다.',
        zh='1. 在任意程序中选中文本。\n2. 按 Ctrl+C 复制它。\n3. 按快捷键——翻译器会从剪贴板取文本并翻译。\n\n快捷键：\n  Ctrl+Shift+Q — 快速翻译剪贴板内容\n  Ctrl+Alt+Q   — 同一功能的备用快捷键\n\n重要：快捷键本身不会复制文本。请务必先按 Ctrl+C。\n快速翻译窗口中按 Esc 可关闭。',
        ar='1. حدد النص في أي برنامج.\n2. اضغط Ctrl+C لنسخه.\n3. اضغط مفتاح الاختصار — سيأخذ المترجم النص من الحافظة ويترجمه.\n\nمفاتيح الاختصار:\n  Ctrl+Shift+Q — ترجمة سريعة من الحافظة\n  Ctrl+Alt+Q   — مفتاح اختصار بديل لنفس الوظيفة\n\nمهم: مفتاح الاختصار لا ينسخ النص بنفسه. اضغط دائمًا Ctrl+C أولاً.\nفي نافذة الترجمة السريعة، Esc يغلقها.'),

    'Кнопка «Перевести» — переводит текст, который вы ввели в поле выше.\n«📋 Перевести буфер» — переводит уже скопированный текст.\nХоткеи делают то же самое, что «Перевести буфер», но сразу показывают быстрый результат.\nЯзыки можно поменять кнопкой ⇄ или выбрать в настройках.': _mk(
        'Кнопка «Перевести» — переводит текст, который вы ввели в поле выше.\n«📋 Перевести буфер» — переводит уже скопированный текст.\nХоткеи делают то же самое, что «Перевести буфер», но сразу показывают быстрый результат.\nЯзыки можно поменять кнопкой ⇄ или выбрать в настройках.',
        'The "Translate" button translates the text you typed in the field above.\n"📋 Translate clipboard" translates already copied text.\nHotkeys do the same as "Translate clipboard", but immediately show a quick result.\nYou can swap languages with the ⇄ button or choose them in settings.',
        de='Die Schaltfläche „Übersetzen" übersetzt den oben eingegebenen Text.\n„📋 Zwischenablage übersetzen" übersetzt bereits kopierten Text.\nHotkeys machen dasselbe wie „Zwischenablage übersetzen", zeigen aber sofort ein schnelles Ergebnis.\nSprachen können mit ⇄ getauscht oder in den Einstellungen gewählt werden.',
        fr='Le bouton « Traduire » traduit le texte saisi ci-dessus.\n« 📋 Traduire le presse-papiers » traduit un texte déjà copié.\nLes raccourcis font la même chose que « Traduire le presse-papiers », mais affichent immédiatement un résultat rapide.\nOn peut échanger les langues avec ⇄ ou les choisir dans les paramètres.',
        es='El botón «Traducir» traduce el texto que escribió arriba.\n«📋 Traducir portapapeles» traduce texto ya copiado.\nLos atajos hacen lo mismo que «Traducir portapapeles», pero muestran inmediatamente un resultado rápido.\nPuede intercambiar idiomas con ⇄ o elegirlos en la configuración.',
        it='Il pulsante «Traduci» traduce il testo digitato sopra.\n«📋 Traduci appunti» traduce testo già copiato.\nLe scorciatoie fanno la stessa cosa di «Traduci appunti», ma mostrano subito un risultato rapido.\nPuoi scambiare le lingue con ⇄ o sceglierle nelle impostazioni.',
        pt='O botão «Traduzir» traduz o texto que escreveu acima.\n«📋 Traduzir área de transferência» traduz texto já copiado.\nOs atalhos fazem o mesmo que «Traduzir área de transferência», mas mostram logo um resultado rápido.\nPode trocar idiomas com ⇄ ou escolhê-los nas definições.',
        nl='De knop "Vertalen" vertaalt de tekst die u hierboven hebt ingevoerd.\n"📋 Klembord vertalen" vertaalt reeds gekopieerde tekst.\nSneltoetsen doen hetzelfde als "Klembord vertalen", maar tonen direct een snel resultaat.\nTalen wisselen met ⇄ of kiezen in instellingen.',
        pl='Przycisk „Tłumacz" tłumaczy tekst wpisany powyżej.\n„📋 Przetłumacz schowek" tłumaczy już skopiowany tekst.\nSkróty robią to samo co „Przetłumacz schowek", ale od razu pokazują szybki wynik.\nJęzyki można zamieniać przyciskiem ⇄ lub wybrać w ustawieniach.',
        tr='"Çevir" düğmesi yukarıdaki alana yazdığınız metni çevirir.\n"📋 Panoyu çevir" önceden kopyalanmış metni çevirir.\nKısayollar "Panoyu çevir" ile aynı işi yapar, ancak hemen hızlı sonuç gösterir.\nDiller ⇄ düğmesiyle değiştirilebilir veya ayarlardan seçilebilir.',
        cs='Tlačítko „Přeložit" přeloží text zadaný výše.\n„📋 Přeložit schránku" přeloží již zkopírový text.\nZkratky dělají totéž co „Přeložit schránku", ale ihned zobrazí rychlý výsledek.\nJazyky lze prohodit tlačítkem ⇄ nebo zvolit v nastavení.',
        hu='A „Fordítás" gomb lefordítja a fenti mezőbe írt szöveget.\nA „📋 Vágólap fordítása" a már kimásolt szöveget fordítja.\nA gyorsbillentyűk ugyanazt teszik, mint a „Vágólap fordítása", de azonnal gyors eredményt mutatnak.\nA nyelvek a ⇄ gombbal cserélhetők, vagy a beállításokban választhatók.',
        ro='Butonul „Traduce" traduce textul introdus mai sus.\n„📋 Tradu clipboardul" traduce textul deja copiat.\nComenzile rapide fac același lucru ca „Tradu clipboardul", dar afișează imediat un rezultat rapid.\nLimbile pot fi schimbate cu butonul ⇄ sau alese din setări.',
        uk='Кнопка «Перекласти» перекладає текст, який ви ввели вище.\n«📋 Перекласти буфер» перекладає вже скопійований текст.\nХоткеї роблять те саме, що «Перекласти буфер», але одразу показують швидкий результат.\nМови можна поміняти кнопкою ⇄ або вибрати в налаштуваннях.',
        sv='Knappen "Översätt" översätter texten du skrev ovan.\n"📋 Översätt urklipp" översätter redan kopierad text.\nSnabbtangenter gör samma sak som "Översätt urklipp", men visar direkt ett snabbt resultat.\nDu kan byta språk med ⇄ eller välja dem i inställningarna.',
        fi='„Käännä"-painike kääntää yllä kirjoittamasi tekstin.\n„📋 Käännä leikepöytä" kääntää jo kopioidun tekstin.\nPikakuvakkeet tekevät saman kuin „Käännä leikepöytä", mutta näyttävät heti nopean tuloksen.\nKielet voi vaihtaa ⇄-painikkeella tai valita asetuksista.',
        ja='「翻訳」ボタンは上に入力したテキストを翻訳します。\n「📋 クリップボードを翻訳」は既にコピーしたテキストを翻訳します。\nホットキーは「クリップボードを翻訳」と同じ動作ですが、すぐに結果を表示します。\n言語は ⇄ ボタンで入れ替えるか、設定で選択できます。',
        ko='"번역" 버튼은 위에 입력한 텍스트를 번역합니다.\n"📋 클립보드 번역"은 이미 복사된 텍스트를 번역합니다.\n단축키는 "클립보드 번역"과 동일하지만 결과를 즉시 표시합니다.\n언어는 ⇄ 버튼으로 바꾸거나 설정에서 선택할 수 있습니다.',
        zh='「翻译」按钮会翻译您在上方输入的文本。\n「📋 翻译剪贴板」会翻译已复制的文本。\n快捷键与「翻译剪贴板」功能相同，但会立即显示快速结果。\n可用 ⇄ 按钮交换语言，或在设置中选择。',
        ar='زر «ترجمة» يترجم النص الذي أدخلته أعلاه.\n«📋 ترجمة الحافظة» يترجم النص المنسوخ مسبقًا.\nمفاتيح الاختصار تفعل نفس «ترجمة الحافظة»، لكنها تُظهر نتيجة سريعة فورًا.\nيمكن تبديل اللغات بزر ⇄ أو اختيارها من الإعدادات.'),

    'Сервисы перевода': _mk(
        'Сервисы перевода', 'Translation services',
        de='Übersetzungsdienste', fr='Services de traduction',
        es='Servicios de traducción', it='Servizi di traduzione',
        pt='Serviços de tradução', nl='Vertaaldiensten',
        pl='Usługi tłumaczeniowe', tr='Çeviri servisleri',
        cs='Překladatelské služby', hu='Fordítási szolgáltatások',
        ro='Servicii de traducere', uk='Сервіси перекладу',
        sv='Översättningstjänster', fi='Käännöspalvelut',
        ja='翻訳サービス', ko='번역 서비스',
        zh='翻译服务', ar='خدمات الترجمة'),

    'Google → Lingva → Lingva-зеркало → MyMemory\nПереводчик автоматически пробует следующий сервис, если предыдущий не ответил.': _mk(
        'Google → Lingva → Lingva-зеркало → MyMemory\nПереводчик автоматически пробует следующий сервис, если предыдущий не ответил.',
        'Google → Lingva → Lingva mirror → MyMemory\nThe translator automatically tries the next service if the previous one does not respond.',
        de='Google → Lingva → Lingva-Spiegel → MyMemory\nDer Übersetzer probiert automatisch den nächsten Dienst, wenn der vorherige nicht antwortet.',
        fr='Google → Lingva → miroir Lingva → MyMemory\nLe traducteur essaie automatiquement le service suivant si le précédent ne répond pas.',
        es='Google → Lingva → espejo Lingva → MyMemory\nEl traductor prueba automáticamente el siguiente servicio si el anterior no responde.',
        it='Google → Lingva → mirror Lingva → MyMemory\nIl traduttore prova automaticamente il servizio successivo se il precedente non risponde.',
        pt='Google → Lingva → espelho Lingva → MyMemory\nO tradutor tenta automaticamente o serviço seguinte se o anterior não responder.',
        nl='Google → Lingva → Lingva-spiegel → MyMemory\nDe vertaler probeert automatisch de volgende dienst als de vorige niet reageert.',
        pl='Google → Lingva → Lustro Lingva → MyMemory\nTłumacz automatycznie próbuje następnej usługi, jeśli poprzednia nie odpowie.',
        tr='Google → Lingva → Lingva ayna → MyMemory\nÇevirmen, önceki yanıt vermezse otomatik olarak sonraki hizmeti dener.',
        cs='Google → Lingva → zrcadlo Lingva → MyMemory\nPřekladač automaticky zkusí další službu, pokud předchozí neodpoví.',
        hu='Google → Lingva → Lingva tükör → MyMemory\nA fordító automatikusan a következő szolgáltatást próbálja, ha az előző nem válaszol.',
        ro='Google → Lingva → oglindă Lingva → MyMemory\nTraducătorul încearcă automat următorul serviciu dacă precedentul nu răspunde.',
        uk='Google → Lingva → дзеркало Lingva → MyMemory\nПерекладач автоматично пробує наступний сервіс, якщо попередній не відповів.',
        sv='Google → Lingva → Lingva-spegel → MyMemory\nÖversättaren provar automatiskt nästa tjänst om den föregående inte svarar.',
        fi='Google → Lingva → Lingva-peili → MyMemory\nKääntäjä kokeilee automaattisesti seuraavaa palvelua, jos edellinen ei vastaa.',
        ja='Google → Lingva → Lingva ミラー → MyMemory\n前のサービスが応答しない場合、翻訳ツールは自動的に次のサービスを試します。',
        ko='Google → Lingva → Lingva 미러 → MyMemory\n이전 서비스가 응답하지 않으면 번역기가 자동으로 다음 서비스를 시도합니다.',
        zh='Google → Lingva → Lingva 镜像 → MyMemory\n如果上一个服务未响应，翻译器会自动尝试下一个服务。',
        ar='Google → Lingva → مرآة Lingva → MyMemory\nيحاول المترجم تلقائيًا الخدمة التالية إذا لم تستجب السابقة.'),

    'Переключить на светлую тему': _mk(
        'Переключить на светлую тему', 'Switch to light theme',
        de='Zum hellen Design wechseln', fr='Passer au thème clair',
        es='Cambiar al tema claro', it='Passa al tema chiaro',
        pt='Mudar para tema claro', nl='Naar licht thema schakelen',
        pl='Przełącz na jasny motyw', tr='Açık temaya geç',
        cs='Přepnout na světlé téma', hu='Váltás világos témára',
        ro='Comută pe tema deschisă', uk='Перемкнути на світлу тему',
        sv='Byt till ljust tema', fi='Vaihda vaaleaan teemaan',
        ja='ライトテーマに切り替え', ko='라이트 테마로 전환',
        zh='切换到浅色主题', ar='التبديل إلى السمة الفاتحة'),

    'Переключить на тёмную тему': _mk(
        'Переключить на тёмную тему', 'Switch to dark theme',
        de='Zum dunklen Design wechseln', fr='Passer au thème sombre',
        es='Cambiar al tema oscuro', it='Passa al tema scuro',
        pt='Mudar para tema escuro', nl='Naar donker thema schakelen',
        pl='Przełącz na ciemny motyw', tr='Koyu temaya geç',
        cs='Přepnout na tmavé téma', hu='Váltás sötét témára',
        ro='Comută pe tema închisă', uk='Перемкнути на темну тему',
        sv='Byt till mörkt tema', fi='Vaihda tummaan teemaan',
        ja='ダークテーマに切り替え', ko='다크 테마로 전환',
        zh='切换到深色主题', ar='التبديل إلى السمة الداكنة'),

    'Сменить язык интерфейса': _mk(
        'Сменить язык интерфейса', 'Change interface language',
        de='Sprache der Oberfläche ändern',
        fr="Changer la langue de l'interface",
        es='Cambiar el idioma de la interfaz',
        it="Cambia la lingua dell'interfaccia",
        pt='Alterar o idioma da interface',
        nl='Interfacetaal wijzigen',
        pl='Zmień język interfejsu',
        tr='Arayüz dilini değiştir',
        cs='Změnit jazyk rozhraní',
        hu='Felület nyelvének módosítása',
        ro='Schimbă limba interfeței',
        uk='Змінити мову інтерфейсу',
        sv='Byt gränssnittsspråk',
        fi='Vaihda käyttöliittymän kieli',
        ja='インターフェース言語を変更',
        ko='인터페이스 언어 변경',
        zh='更改界面语言', ar='تغيير لغة الواجهة'),
}


def _tr(key, lang):
    entry = UI_TR.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get('en') or entry.get('ru') or key


# ============ ЯЗЫКИ ПЕРЕВОДА ============
LANGUAGES = {
    "ru": "Русский", "en": "English", "de": "Deutsch", "fr": "Français",
    "es": "Español", "it": "Italiano", "pt": "Português", "pl": "Polski",
    "uk": "Українська", "tr": "Türkçe", "zh-CN": "中文 (简体)",
    "ja": "日本語", "ko": "한국어", "ar": "العربية", "hi": "हिन्दी",
    "cs": "Čeština", "nl": "Nederlands", "sv": "Svenska", "fi": "Suomi",
    "el": "Ελληνικά", "he": "עברית", "ro": "Română", "hu": "Magyar",
    "bg": "Български",
}


# ============ ТЕМЫ ============
THEMES = {
    "dark": {
        "bg": "#1c1f26",
        "bg_dark": "#13161b",
        "fg": "#e8eaf0",
        "fg_dim": "#8b8f9c",
        "white": "#ffffff",
        "selected_fg": "#ffffff",

        "green": "#4ade80",
        "green_b": "#86efac",
        "orange": "#fbbf24",
        "orange_b": "#fde047",
        "orange_hi": "#fde047",
        "red": "#f87171",
        "red_b": "#fca5a5",
        "blue": "#5a8fc9",
        "blue_b": "#7aa8dc",

        "up_clr": "#6b6f7c",

        "preset_bg": "#262a33",
        "preset_hover": "#31363f",
        "preset_active": "#16a34a",

        "custom_bg": "#1e392e",
        "custom_hover": "#294a3c",

        "action_bg": "#262a33",
        "action_hover": "#31363f",
        "action_active": "#16a34a",

        "btn_start": "#16a34a",
        "btn_start_hov": "#22c55e",
        "btn_pause": "#475569",
        "btn_pause_hov": "#5a6879",
        "btn_cancel": "#7f1d1d",
        "btn_cancel_hov": "#991b1b",

        "entry_bg": "#13161b",
        "entry_border": "#31363f",
    },
    "light": {
        "bg": "#f6f8fb",
        "bg_dark": "#ffffff",
        "fg": "#1a1f29",
        "fg_dim": "#6b7280",
        "white": "#ffffff",
        "selected_fg": "#ffffff",

        "green": "#10b981",
        "green_b": "#059669",
        "orange": "#f59e0b",
        "orange_b": "#d97706",
        "orange_hi": "#fbbf24",
        "red": "#ef4444",
        "red_b": "#dc2626",
        "blue": "#2563eb",
        "blue_b": "#3b82f6",

        "up_clr": "#9aa1ad",

        "preset_bg": "#e8ecf3",
        "preset_hover": "#d8dee8",
        "preset_active": "#059669",

        "custom_bg": "#d1f0e0",
        "custom_hover": "#b8e5cc",

        "action_bg": "#e8ecf3",
        "action_hover": "#d8dee8",
        "action_active": "#059669",

        "btn_start": "#059669",
        "btn_start_hov": "#047857",
        "btn_pause": "#64748b",
        "btn_pause_hov": "#556070",
        "btn_cancel": "#dc2626",
        "btn_cancel_hov": "#b91c1c",

        "entry_bg": "#ffffff",
        "entry_border": "#cbd5e1",
    },
}


# ============ ПЕРЕВОД ============
def _normalize_lang(code):
    if not code or code == "auto":
        return "auto"
    return code.split("-")[0].lower()


def translate_google(text, source="auto", target="ru"):
    try:
        src = _normalize_lang(source)
        tgt = _normalize_lang(target)
        params = urllib.parse.urlencode({
            "client": "gtx", "sl": src, "tl": tgt, "dt": "t", "q": text,
        })
        url = "https://translate.googleapis.com/translate_a/single?" + params
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = data[0] if isinstance(data, list) and data else []
        translated = "".join(str(x[0]) for x in parts if isinstance(x, list) and x and x[0])
        detected = data[2] if len(data) > 2 and isinstance(data[2], str) else None
        return (translated or None), detected
    except Exception as e:
        log_event(f"Google Translate: {e}")
        return None, None


def translate_mymemory(text, source="auto", target="ru"):
    try:
        src = _normalize_lang(source)
        if src == "auto":
            src = "en"
        tgt = _normalize_lang(target)
        params = urllib.parse.urlencode({"q": text, "langpair": f"{src}|{tgt}"})
        url = "https://api.mymemory.translated.net/get?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "MiniTranslator/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        translated = (data.get("responseData") or {}).get("translatedText")
        if translated and translated.strip():
            return translated, (None if source == "auto" else source)
    except Exception as e:
        log_event(f"MyMemory: {e}")
    return None, None


def translate_lingva(text, source="auto", target="ru", url_template=None):
    try:
        url_template = url_template or LINGVA_URL
        src = _normalize_lang(source)
        tgt = _normalize_lang(target)
        url = url_template.format(source=src, target=tgt,
                                  query=urllib.parse.quote(text, safe=""))
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        translated = data.get("translation")
        detected = (data.get("info") or {}).get("detectedSource")
        return (translated or None), detected
    except Exception as e:
        log_event(f"Lingva: {e}")
        return None, None


def translate_any(text, source="auto", target="ru"):
    for name, fn in (("Google", lambda: translate_google(text, source, target)),
                     ("Lingva", lambda: translate_lingva(text, source, target, LINGVA_URL)),
                     ("Lingva mirror", lambda: translate_lingva(text, source, target, LINGVA_URL_ALT)),
                     ("MyMemory", lambda: translate_mymemory(text, source, target))):
        translated, detected = fn()
        if translated:
            log_event(f"Перевод выполнен через {name}")
            return translated, detected
    return None, None


# ============ ТУЛТИП ============
class Tooltip:
    def __init__(self, widget, key, app=None, delay=450):
        self.widget = widget
        self.app = app
        self.key = key
        self.delay = delay
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def set_key(self, key):
        self.key = key

    def _get_text(self):
        if self.app is None or self.key is None:
            return ""
        return self.app._t(self.key)

    def _on_enter(self, event=None):
        self._cancel()
        try:
            self.after_id = self.widget.after(self.delay, self._show)
        except Exception:
            pass

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show(self):
        if self.tip:
            return
        text = self._get_text()
        if not text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except Exception:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_attributes("-topmost", True)
        self.tip.configure(bg="#e0a030")
        inner = tk.Frame(self.tip, bg="#1a1a1a")
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=text, bg="#1a1a1a", fg="#ffffff",
                 font=("Segoe UI", 9), justify="left",
                 padx=12, pady=8, wraplength=420).pack()
        self.tip.update_idletasks()
        tw = self.tip.winfo_width()
        th = self.tip.winfo_height()
        sw = self.tip.winfo_screenwidth()
        sh = self.tip.winfo_screenheight()
        if x + tw > sw - 6:
            x = sw - tw - 6
        if x < 6:
            x = 6
        if y + th > sh - 6:
            y = self.widget.winfo_rooty() - th - 6
        self.tip.wm_geometry(f"+{x}+{y}")

    def _hide(self):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


# ============ WINAPI INPUT ============
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUTunion),
    ]


user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


def send_key(vk, up=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = vk
    inp.u.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def release_all_modifiers():
    for _ in range(2):
        for vk in (VK_CONTROL, VK_MENU, VK_SHIFT):
            send_key(vk, up=True)
        time.sleep(0.02)


def simulate_copy():
    try:
        release_all_modifiers()
        time.sleep(0.05)
        send_key(VK_CONTROL)
        time.sleep(0.05)
        send_key(VK_C)
        time.sleep(0.05)
        send_key(VK_C, up=True)
        time.sleep(0.05)
        send_key(VK_CONTROL, up=True)
        time.sleep(0.02)
    except Exception as e:
        log_event(f"SendInput: {e}")


# ============ SINGLE INSTANCE ============
def acquire_single_instance():
    global _mutex_handle
    try:
        _mutex_handle = kernel32.CreateMutexW(
            None, False, "MiniTranslator_SingleInstance_Mutex")
        return kernel32.GetLastError() != ERROR_ALREADY_EXISTS
    except Exception:
        return True


def signal_existing_instance():
    try:
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            f.write("1")
    except Exception:
        pass


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


APP_DIR = _app_dir()


# ============ РЕЕСТР ============
def _reg_read(name):
    if not WINREG_OK:
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                             winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, name)
            return val
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None


def _reg_write(name, value):
    if not WINREG_OK:
        return False
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        try:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def load_settings():
    raw = _reg_read("settings")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def save_settings(data):
    try:
        _reg_write("settings", json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


# ============ АВТОЗАПУСК ============
AUTORUN_REG_NAME = "MiniTranslator"


def _startup_folder():
    return os.path.join(os.environ.get("APPDATA", ""),
                        r"Microsoft\Windows\Start Menu\Programs\Startup")


def _startup_shortcut_path():
    return os.path.join(_startup_folder(), "MiniTranslator.lnk")


def _autostart_command():
    if getattr(sys, "frozen", False):
        return sys.executable, "--minimized"
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    return pythonw, f'"{os.path.abspath(sys.argv[0])}" --minimized'


def _set_registry_autostart(enabled):
    if not WINREG_OK:
        return False
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run")
        try:
            if enabled:
                target, args = _autostart_command()
                command = f'"{target}"'
                if args:
                    command += f' {args}'
                winreg.SetValueEx(key, AUTORUN_REG_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, AUTORUN_REG_NAME)
                except FileNotFoundError:
                    pass
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        log_event(f"Автозапуск реестр: {e}")
        return False


def _set_startup_autostart(enabled):
    shortcut = _startup_shortcut_path()
    try:
        if not enabled:
            if os.path.exists(shortcut):
                os.remove(shortcut)
            return True
        os.makedirs(os.path.dirname(shortcut), exist_ok=True)
        target, args = _autostart_command()
        esc = lambda x: x.replace("'", "''")
        ps = (
            "$ws=New-Object -ComObject WScript.Shell;"
            f"$s=$ws.CreateShortcut('{esc(shortcut)}');"
            f"$s.TargetPath='{esc(target)}';"
            f"$s.Arguments='{esc(args.strip())}';"
            f"$s.WorkingDirectory='{esc(os.path.dirname(target))}';"
            "$s.IconLocation=$s.TargetPath;$s.Save()"
        )
        import subprocess
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", ps],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=8, check=True)
        return os.path.exists(shortcut)
    except Exception as e:
        log_event(f"Автозапуск Startup: {e}")
        return False


def _get_autostart_mode():
    if bool(_reg_read("autostart_registry")):
        return "registry"
    if bool(_reg_read("autostart_startup")) or os.path.exists(_startup_shortcut_path()):
        return "startup"
    return "off"


_LOG_BUFFER = collections.deque(maxlen=200)


def log_event(text):
    try:
        ts = time.strftime("%H:%M:%S")
        _LOG_BUFFER.append(f"[{ts}] {text}")
    except Exception:
        pass


def get_log_text():
    if not _LOG_BUFFER:
        return "(log is empty)"
    return "\n".join(_LOG_BUFFER)


# ============ БУФЕР ============
def get_clipboard_text():
    CF_UNICODETEXT = 13
    CF_TEXT = 1
    for attempt in range(20):
        try:
            if not user32.OpenClipboard(None):
                time.sleep(0.05)
                continue
            text = ""
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if handle:
                    size = kernel32.GlobalSize(handle)
                    if size and size > 0:
                        ptr = kernel32.GlobalLock(handle)
                        if ptr:
                            try:
                                n_chars = size // 2
                                raw = ctypes.wstring_at(ptr, n_chars)
                                idx = raw.find('\x00')
                                if idx >= 0:
                                    raw = raw[:idx]
                                text = raw
                            finally:
                                kernel32.GlobalUnlock(handle)
                if not text.strip():
                    handle = user32.GetClipboardData(CF_TEXT)
                    if handle:
                        size = kernel32.GlobalSize(handle)
                        if size and size > 0:
                            ptr = kernel32.GlobalLock(handle)
                            if ptr:
                                try:
                                    data = ctypes.string_at(ptr, size)
                                    idx = data.find(b'\x00')
                                    if idx >= 0:
                                        data = data[:idx]
                                    for enc in ('cp1251', 'utf-8', 'cp866'):
                                        try:
                                            text = data.decode(enc)
                                            if text.strip():
                                                break
                                        except Exception:
                                            continue
                                finally:
                                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
            if text.strip():
                return text
        except Exception as e:
            try:
                user32.CloseClipboard()
            except Exception:
                pass
            log_event(f"Буфер (попытка {attempt + 1}): {e}")
        time.sleep(0.06)
    return ""


def set_clipboard_text(text):
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    for _ in range(8):
        try:
            if not user32.OpenClipboard(None):
                time.sleep(0.05)
                continue
            try:
                user32.EmptyClipboard()
                data = text.encode("utf-16-le") + b"\x00\x00"
                size = len(data)
                handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
                if not handle:
                    return False
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    kernel32.GlobalFree(handle)
                    return False
                try:
                    ctypes.memmove(ptr, data, size)
                finally:
                    kernel32.GlobalUnlock(handle)
                result = user32.SetClipboardData(CF_UNICODETEXT, handle)
                return bool(result)
            finally:
                user32.CloseClipboard()
        except Exception:
            try:
                user32.CloseClipboard()
            except Exception:
                pass
        time.sleep(0.05)
    return False


def clear_windows_clipboard():
    for _ in range(8):
        try:
            if not user32.OpenClipboard(None):
                time.sleep(0.05)
                continue
            try:
                return bool(user32.EmptyClipboard())
            finally:
                user32.CloseClipboard()
        except Exception:
            try:
                user32.CloseClipboard()
            except Exception:
                pass
        time.sleep(0.05)
    return False


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_pos():
    pt = POINT()
    try:
        user32.GetCursorPos(ctypes.byref(pt))
    except Exception:
        pass
    return pt.x, pt.y


# ============ ГЛАВНЫЙ КЛАСС ============
class App:
    HOTKEY_ID_1 = 1
    HOTKEY_ID_2 = 2

    def __init__(self):
        self.settings = load_settings()
        self._autorun_launch = ("--minimized" in sys.argv
                                 or bool(self.settings.get("start_in_tray", False)))

        self.theme_name = self.settings.get("theme", "dark")
        if self.theme_name not in THEMES:
            self.theme_name = "dark"
        self.T = {}
        self.T.update(THEMES[self.theme_name])

        self._ui_lang = self.settings.get("ui_lang", "en")
        if self._ui_lang not in UI_LANGS:
            self._ui_lang = "en"

        self.my_lang = self.settings.get("my_lang", "ru")
        self.other_lang = self.settings.get("other_lang", "en")

        self.tray_icon = None
        self._icon_photo = None
        self._styled = []
        self._i18n_widgets = []
        self._tooltips = []
        self._warning_dlg = None
        self._settings_dlg = None
        self._log_dlg = None
        self._popup = None
        self._popup_topmost_job = None

        self._last_source = ""
        self._last_translated = ""
        self._last_src_lang = ""
        self._last_tgt_lang = ""

        self._hotkey_thread_id = None
        self._hotkey_registered_1 = False
        self._hotkey_registered_2 = False

        self._base_w = 480
        self._base_h = 580

        self._build_ui()

        self.root.after_idle(self._center_main_window)
        self.root.after(50, self._center_main_window)
        self.root.after(250, self._center_main_window)
        self.root.after(600, self._center_main_window)
        self.root.after(200, self._apply_icon)
        self.root.after(500, self._poll_signal)
        self.root.after(1000, self._setup_tray)
        self.root.after(1200, self._start_hotkey_thread)

        log_event("=== Переводчик запущен ===")
        log_event("Хоткеи: Ctrl+Shift+Q / Ctrl+Alt+Q")
        log_event("Сервисы: Google → Lingva → Lingva-зеркало → MyMemory")

    # ============ i18n утилиты ============
    def _t(self, key, **fmt):
        text = _tr(key, self._ui_lang)
        if fmt:
            try:
                return text.format(**fmt)
            except Exception:
                return text
        return text

    def _reg(self, widget, role):
        self._styled.append((widget, role))

    def _reg_i18n(self, widget, key):
        self._i18n_widgets.append((widget, key))

    def _rebuild_all_texts(self):
        for w, key in self._i18n_widgets:
            try:
                if w.winfo_exists():
                    w.config(text=self._t(key))
            except Exception:
                pass
        try:
            self.root.title(self._t('Мини-переводчик'))
        except Exception:
            pass
        try:
            if hasattr(self, 'buffer_btn') and self.buffer_btn.winfo_exists():
                cur = self.buffer_btn.cget("text")
                if not cur.startswith("✓"):
                    self.buffer_btn.config(text=self._t('📋 Перевести буфер'))
        except Exception:
            pass
        try:
            if hasattr(self, 'clear_buffer_btn') and self.clear_buffer_btn.winfo_exists():
                cur = self.clear_buffer_btn.cget("text")
                if not cur.startswith("✓"):
                    self.clear_buffer_btn.config(text=self._t('✕  Очистить буфер'))
        except Exception:
            pass
        try:
            self.tgt_lang_lbl.config(
                text=LANGUAGES.get(self.my_lang, self.my_lang))
            if not self._last_src_lang or self._last_src_lang == "?":
                self.src_lang_lbl.config(text=self._t('Авто'))
        except Exception:
            pass
        try:
            self._update_hotkey_status()
        except Exception:
            pass
        try:
            for tip in self._tooltips:
                if getattr(tip, "widget", None) is self._theme_btn:
                    tip.set_key(self._theme_tooltip_key())
        except Exception:
            pass
        try:
            if TRAY_OK and self.tray_icon is not None:
                self._rebuild_tray_menu()
        except Exception:
            pass

    def _set_ui_lang(self, code):
        if code not in UI_LANGS:
            return
        self._ui_lang = code
        self.settings["ui_lang"] = code
        save_settings(self.settings)
        try:
            if self._lang_btn is not None:
                self._lang_btn.config(text=f"🌐 {code.upper()}")
        except Exception:
            pass
        self._rebuild_all_texts()
        self._fit_window()

    # ==== ПОДГОНКА РАЗМЕРА ОКНА ПОД ТЕКУЩИЙ ЯЗЫК ====
    def _fit_window(self):
        """Пересчитывает натуральные размеры окна и меняет геометрию,
        сохраняя центр окна на экране. Вызывается после смены языка."""
        try:
            self.root.update_idletasks()
            req_w = self.root.winfo_reqwidth()
            req_h = self.root.winfo_reqheight()

            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()
            cur_x = self.root.winfo_x()
            cur_y = self.root.winfo_y()

            w = max(self._base_w, req_w + 8)
            h = max(self._base_h, req_h + 8)

            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            if w > sw - 40:
                w = sw - 40
            if h > sh - 60:
                h = sh - 60

            new_x = cur_x + (cur_w - w) // 2
            new_y = cur_y + (cur_h - h) // 2

            if new_x < 0:
                new_x = 0
            if new_y < 0:
                new_y = 0
            if new_x + w > sw:
                new_x = sw - w
            if new_y + h > sh:
                new_y = sh - h

            self.root.geometry(f"{w}x{h}+{new_x}+{new_y}")
            self.root.update_idletasks()
        except Exception:
            pass

    def _show_lang_menu(self):
        T = self.T
        m = tk.Menu(self.root, tearoff=0,
                    bg=T["bg_dark"], fg=T["fg"],
                    activebackground=T["preset_active"],
                    activeforeground=T["selected_fg"],
                    bd=0, relief="flat",
                    font=("Segoe UI", 10))
        for code, name in UI_LANGS.items():
            prefix = "✓  " if code == self._ui_lang else "     "
            m.add_command(label=prefix + name,
                          command=lambda c=code: self._set_ui_lang(c))
        try:
            x = self._lang_btn.winfo_rootx()
            y = self._lang_btn.winfo_rooty() + self._lang_btn.winfo_height() + 2
            m.tk_popup(x, y)
        finally:
            try:
                m.grab_release()
            except Exception:
                pass

    def _lang_press(self, e):
        self._lang_click_x = e.x_root
        self._lang_click_y = e.y_root

    def _lang_release(self, e):
        try:
            if (abs(e.x_root - self._lang_click_x) < 5 and
                    abs(e.y_root - self._lang_click_y) < 5):
                self._show_lang_menu()
        except Exception:
            pass

    # ============ BUILD UI ============
    def _build_ui(self):
        T = self.T
        self.root = tk.Tk()
        self.root.title(self._t('Мини-переводчик'))
        self.root.configure(bg=T["bg"])
        self.root.resizable(False, False)
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass

        w, h = self._base_w, self._base_h
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
        except Exception:
            pass

        if self._autorun_launch:
            try:
                self.root.withdraw()
            except Exception:
                pass

        # ===== Шапка =====
        header = tk.Frame(self.root, bg=T["bg"], cursor="fleur")
        header.pack(fill="x", padx=0, pady=(14, 0))
        self._reg(header, "frame")

        # Правые кнопки (сначала тема, потом язык — так они стоят рядом)
        self._theme_btn = tk.Label(
            header, text="☾", bg=T["bg"], fg=T["fg_dim"],
            font=("Segoe UI", 16), cursor="hand2")
        self._theme_btn.pack(side="right", padx=(8, 20))
        self._reg(self._theme_btn, "theme_btn")
        self._theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())
        self._theme_btn.bind("<Enter>",
                              lambda e: self._theme_btn.config(fg=self.T["green"]))
        self._theme_btn.bind("<Leave>",
                              lambda e: self._theme_btn.config(fg=self.T["fg_dim"]))

        self._lang_btn = tk.Label(
            header, text=f"🌐 {self._ui_lang.upper()}",
            bg=T["bg"], fg=T["fg_dim"],
            font=("Segoe UI", 10, "bold"), cursor="hand2",
            padx=6, pady=2)
        self._lang_btn.pack(side="right", padx=(8, 0))
        self._reg(self._lang_btn, "lang_btn")
        self._lang_btn.bind("<ButtonPress-1>", self._lang_press, add="+")
        self._lang_btn.bind("<ButtonRelease-1>", self._lang_release, add="+")
        self._lang_btn.bind("<Enter>",
                             lambda e: self._lang_btn.config(fg=self.T["green"]),
                             add="+")
        self._lang_btn.bind("<Leave>",
                             lambda e: self._lang_btn.config(fg=self.T["fg_dim"]),
                             add="+")

        title_area = tk.Frame(header, bg=T["bg"], cursor="fleur")
        title_area.pack(side="left", fill="x", expand=True, padx=(18, 0))
        self._reg(title_area, "frame")

        self._title_icon_lbl = tk.Label(
            title_area, text="🌐", bg=T["bg"], fg=T["blue"],
            font=("Segoe UI", 22), cursor="fleur")
        self._title_icon_lbl.pack(side="left", padx=(0, 8))
        self._reg(self._title_icon_lbl, "icon_blue")

        self._app_title_lbl = tk.Label(
            title_area, text=self._t('Мини-переводчик'),
            bg=T["bg"], fg=T["fg"],
            font=("Segoe UI", 16, "bold"), cursor="fleur")
        self._app_title_lbl.pack(side="left")
        self._reg(self._app_title_lbl, "label")
        self._reg_i18n(self._app_title_lbl, 'Мини-переводчик')

        self._enable_drag(header)

        self._tooltips.append(Tooltip(self._theme_btn, self._theme_tooltip_key(), app=self))
        self._tooltips.append(Tooltip(self._lang_btn, 'Сменить язык интерфейса', app=self))

        # ===== Статус хоткеев =====
        self.hotkey_status_lbl = tk.Label(
            self.root, text=self._t('⏳ Проверка хоткеев…'),
            bg=T["bg"], fg=T["fg_dim"],
            font=("Segoe UI", 9), anchor="w", justify="left")
        self.hotkey_status_lbl.pack(fill="x", padx=18, pady=(8, 0))
        self._reg(self.hotkey_status_lbl, "label_dim")

        # ===== Языковая строка =====
        langs_row = tk.Frame(self.root, bg=T["bg"])
        langs_row.pack(fill="x", padx=18, pady=(10, 0))
        self._reg(langs_row, "frame")

        self.src_lang_lbl = tk.Label(
            langs_row, text=self._t('Авто'), bg=T["action_bg"], fg=T["fg"],
            font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.src_lang_lbl.pack(side="left")
        self._reg(self.src_lang_lbl, "action_btn")
        self._reg_i18n(self.src_lang_lbl, 'Авто')

        self._arrow_lbl = tk.Label(langs_row, text="→", bg=T["bg"], fg=T["fg_dim"],
                                     font=("Segoe UI", 12))
        self._arrow_lbl.pack(side="left", padx=8)
        self._reg(self._arrow_lbl, "label_dim")

        self.tgt_lang_lbl = tk.Label(
            langs_row, text=LANGUAGES.get(self.my_lang, self.my_lang),
            bg=T["action_bg"], fg=T["fg"],
            font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.tgt_lang_lbl.pack(side="left")
        self._reg(self.tgt_lang_lbl, "action_btn")

        self._swap_btn = tk.Label(
            langs_row, text="⇄", bg=T["bg"], fg=T["fg_dim"],
            font=("Segoe UI", 14), cursor="hand2", padx=6)
        self._swap_btn.pack(side="left", padx=(12, 0))
        self._reg(self._swap_btn, "label_dim")
        self._swap_btn.bind("<Button-1>", lambda e: self._swap_languages())
        self._swap_btn.bind("<Enter>",
                             lambda e: self._swap_btn.config(fg=self.T["green"]))
        self._swap_btn.bind("<Leave>",
                             lambda e: self._swap_btn.config(fg=self.T["fg_dim"]))
        self._tooltips.append(Tooltip(self._swap_btn, 'Поменять языки местами', app=self))

        # ===== Поле ввода =====
        self._input_lbl = tk.Label(
            self.root, text=self._t('Текст для перевода'),
            bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9))
        self._input_lbl.pack(anchor="w", padx=22, pady=(14, 2))
        self._reg(self._input_lbl, "label_dim")   # <— ВАЖНО: регистрируем под тему
        self._reg_i18n(self._input_lbl, 'Текст для перевода')

        self.input_text = tk.Text(
            self.root, height=4, bg=T["entry_bg"], fg=T["fg"],
            insertbackground=T["fg"], font=("Segoe UI", 11),
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=T["entry_border"],
            highlightcolor=T["blue"], wrap="word")
        self.input_text.pack(fill="x", padx=22, ipady=6)

        # ===== Кнопки действий =====
        btn_row = tk.Frame(self.root, bg=T["bg"])
        btn_row.pack(pady=(12, 6))
        self._reg(btn_row, "frame")

        self.translate_btn = tk.Button(
            btn_row, text=self._t('Перевести'),
            bg=T["btn_start"], fg="white",
            activebackground=T["btn_start_hov"], activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            padx=18, pady=8, cursor="hand2",
            command=self._translate_manual)
        self.translate_btn.pack(side="left", padx=4)
        self._reg(self.translate_btn, "btn_start")
        self._reg_i18n(self.translate_btn, 'Перевести')

        self.buffer_btn = tk.Button(
            btn_row, text=self._t('📋 Перевести буфер'),
            bg=T["action_bg"], fg=T["fg"],
            activebackground=T["action_hover"], activeforeground=T["fg"],
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            padx=14, pady=8, cursor="hand2",
            command=self._translate_from_clipboard_btn)
        self.buffer_btn.pack(side="left", padx=4)
        self._reg(self.buffer_btn, "action_btn")
        self._tooltips.append(Tooltip(
            self.buffer_btn,
            'Перевести то, что в буфере обмена.\nСначала Ctrl+C, затем эта кнопка.',
            app=self))

        self.clear_buffer_btn = tk.Button(
            btn_row, text=self._t('✕  Очистить буфер'),
            bg=T["action_bg"], fg=T["fg"],
            activebackground=T["action_hover"], activeforeground=T["fg"],
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            padx=14, pady=8, cursor="hand2",
            command=self._clear_clipboard)
        self.clear_buffer_btn.pack(side="left", padx=4)
        self._reg(self.clear_buffer_btn, "action_btn")
        self._tooltips.append(Tooltip(
            self.clear_buffer_btn,
            'Полностью очистить системный буфер обмена Windows', app=self))

        # ===== Поле результата =====
        self._result_lbl = tk.Label(
            self.root, text=self._t('Перевод'),
            bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9))
        self._result_lbl.pack(anchor="w", padx=22, pady=(8, 2))
        self._reg(self._result_lbl, "label_dim")  # <— ВАЖНО
        self._reg_i18n(self._result_lbl, 'Перевод')

        self.result_text = tk.Text(
            self.root, height=4, bg=T["bg_dark"], fg=T["fg"],
            font=("Segoe UI", 11), relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=T["entry_border"],
            highlightcolor=T["green"], wrap="word", state="disabled")
        self.result_text.pack(fill="x", padx=22, ipady=6)

        clear_row = tk.Frame(self.root, bg=T["bg"])
        clear_row.pack(fill="x", padx=22, pady=(5, 0))
        self._reg(clear_row, "frame")

        self.clear_input_btn = tk.Button(
            clear_row, text=self._t('✕  Очистить текст'),
            bg=T["action_bg"], fg=T["fg_dim"],
            activebackground=T["action_hover"], activeforeground=T["fg"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
            padx=14, pady=5, cursor="hand2",
            command=self._clear_input)
        self.clear_input_btn.pack(side="left")
        self._reg(self.clear_input_btn, "action_btn")
        self._reg_i18n(self.clear_input_btn, '✕  Очистить текст')
        self._tooltips.append(Tooltip(
            self.clear_input_btn, 'Очистить только текст для перевода', app=self))

        self.clear_result_btn = tk.Button(
            clear_row, text=self._t('✕  Очистить перевод'),
            bg=T["action_bg"], fg=T["fg_dim"],
            activebackground=T["action_hover"], activeforeground=T["fg"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
            padx=14, pady=5, cursor="hand2",
            command=self._clear_result)
        self.clear_result_btn.pack(side="right")
        self._reg(self.clear_result_btn, "action_btn")
        self._reg_i18n(self.clear_result_btn, '✕  Очистить перевод')
        self._tooltips.append(Tooltip(
            self.clear_result_btn, 'Очистить только уже переведённый текст', app=self))

        # ===== Нижняя строка =====
        bottom = tk.Frame(self.root, bg=T["bg"])
        bottom.pack(side="bottom", fill="x", pady=(8, 12))
        self._reg(bottom, "frame")

        for key, cmd, color in (
            ('Свернуть', self._hide_to_tray, T["green"]),
            ('Настройки', self._open_settings_dialog, T["blue"]),
            ('Журнал', self._open_log_window, T["orange"]),
            ('Выход', self._really_quit, T["red"]),
        ):
            lbl = tk.Label(bottom, text=self._t(key), bg=T["bg"],
                           fg=T["fg_dim"],
                           font=("Segoe UI", 9, "underline"), cursor="hand2")
            lbl.pack(side="left", padx=8)
            self._reg(lbl, "label_dim")
            self._reg_i18n(lbl, key)
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            lbl.bind("<Enter>", lambda e, l=lbl, c=color: l.config(fg=c))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=T["fg_dim"]))

        self._refresh_theme_colors()
        self._update_theme_button()

    def _theme_tooltip_key(self):
        if self.theme_name == "dark":
            return 'Переключить на светлую тему'
        return 'Переключить на тёмную тему'

    def _update_theme_button(self):
        try:
            self._theme_btn.config(text="☾" if self.theme_name == "dark" else "☀")
        except Exception:
            pass

    def _center_main_window(self):
        try:
            self.root.update_idletasks()
            w = max(self._base_w, self.root.winfo_reqwidth() + 8)
            h = max(self._base_h, self.root.winfo_reqheight() + 8)
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            if w > sw - 40:
                w = sw - 40
            if h > sh - 60:
                h = sh - 60
            x = int((sw - w) / 2)
            y = int((sh - h) / 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.update_idletasks()
            self.root.lift()
        except Exception:
            pass

    def _set_hotkey_status(self, key_or_text, color_key="fg_dim"):
        try:
            text = self._t(key_or_text) if key_or_text in UI_TR else key_or_text
            self.hotkey_status_lbl.config(text=text, fg=self.T[color_key])
        except Exception:
            pass

    def _hide_to_tray(self):
        try:
            self.root.withdraw()
        except Exception:
            pass

    def _enable_drag(self, widget):
        widget.bind("<Button-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_move, add="+")
        for child in widget.winfo_children():
            self._enable_drag(child)

    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._dx
        y = e.y_root - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _refresh_theme_colors(self):
        T = self.T
        for widget, role in self._styled:
            try:
                if not widget.winfo_exists():
                    continue
                if role == "frame":
                    widget.config(bg=T["bg"])
                elif role == "label":
                    widget.config(bg=T["bg"], fg=T["fg"])
                elif role == "label_dim":
                    widget.config(bg=T["bg"], fg=T["fg_dim"])
                elif role == "icon_blue":
                    widget.config(bg=T["bg"], fg=T["blue"])
                elif role == "theme_btn":
                    widget.config(bg=T["bg"], fg=T["fg_dim"])
                elif role == "lang_btn":
                    widget.config(bg=T["bg"], fg=T["fg_dim"])
                elif role == "action_btn":
                    widget.config(bg=T["action_bg"], fg=T["fg"],
                                  activebackground=T["action_hover"],
                                  activeforeground=T["fg"])
                elif role == "btn_start":
                    widget.config(bg=T["btn_start"], fg="white",
                                  activebackground=T["btn_start_hov"])
            except Exception:
                pass
        try:
            self.input_text.config(bg=T["entry_bg"], fg=T["fg"],
                                    insertbackground=T["fg"],
                                    highlightbackground=T["entry_border"])
            self.result_text.config(bg=T["bg_dark"], fg=T["fg"],
                                     highlightbackground=T["entry_border"])
        except Exception:
            pass
        try:
            self.root.configure(bg=T["bg"])
        except Exception:
            pass
        # После смены темы пересчитаем размер окна (вдруг поменялись шрифты/отступы)
        try:
            self.root.after(50, self._fit_window)
        except Exception:
            pass

    def _toggle_theme(self):
        new = "light" if self.theme_name == "dark" else "dark"
        self.theme_name = new
        self.settings["theme"] = new
        save_settings(self.settings)
        self.T.clear()
        self.T.update(THEMES[new])
        self._refresh_theme_colors()
        self._update_theme_button()
        try:
            for tip in self._tooltips:
                if getattr(tip, "widget", None) is self._theme_btn:
                    tip.set_key(self._theme_tooltip_key())
        except Exception:
            pass

    def _swap_languages(self):
        self.my_lang, self.other_lang = self.other_lang, self.my_lang
        self.settings["my_lang"] = self.my_lang
        self.settings["other_lang"] = self.other_lang
        save_settings(self.settings)
        self.tgt_lang_lbl.config(text=LANGUAGES.get(self.my_lang, self.my_lang))
        log_event(f"Языки: {self.other_lang} → {self.my_lang}")

    # ============ ХОТКЕИ ============
    def _start_hotkey_thread(self):
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop, daemon=True, name="hotkey")
        self._hotkey_thread.start()

    def _hotkey_loop(self):
        self._hotkey_thread_id = kernel32.GetCurrentThreadId()
        ok1 = user32.RegisterHotKey(None, self.HOTKEY_ID_1,
                                     MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, ord('Q'))
        ok2 = user32.RegisterHotKey(None, self.HOTKEY_ID_2,
                                     MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord('Q'))
        self._hotkey_registered_1 = bool(ok1)
        self._hotkey_registered_2 = bool(ok2)
        log_event(f"RegisterHotKey 1 (Ctrl+Shift+Q): {ok1}")
        log_event(f"RegisterHotKey 2 (Ctrl+Alt+Q): {ok2}")
        self.root.after(0, self._update_hotkey_status)
        if not ok1 and not ok2:
            return
        msg = wintypes.MSG()
        while True:
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r == 0 or r == -1:
                break
            if msg.message == WM_HOTKEY:
                hid = msg.wParam
                if hid in (self.HOTKEY_ID_1, self.HOTKEY_ID_2):
                    self.root.after(0, self._on_hotkey_fired)

    def _update_hotkey_status(self):
        if self._hotkey_registered_1 and self._hotkey_registered_2:
            self._set_hotkey_status(
                '✓ Хоткеи активны:\n   Ctrl+Shift+Q  /  Ctrl+Alt+Q', "green")
        elif self._hotkey_registered_1:
            self._set_hotkey_status('✓ Активен Ctrl+Shift+Q', "green")
        elif self._hotkey_registered_2:
            self._set_hotkey_status('✓ Активен Ctrl+Alt+Q', "green")
        else:
            self._set_hotkey_status(
                '❌ Хоткеи заняты. Используйте Ctrl+C → «📋 Перевести буфер».', "red")

    def _on_hotkey_fired(self):
        log_event("Хоткей сработал")
        threading.Thread(target=self._do_hotkey_action, daemon=True).start()

    def _do_hotkey_action(self):
        try:
            log_event("Хоткей: запуск перевода буфера")
            self.root.after(0, self._translate_from_clipboard_hotkey)
        except Exception as e:
            log_event(f"Ошибка хоткея: {e}")

    def _translate_from_clipboard_hotkey(self):
        text = get_clipboard_text().strip()
        if not text:
            self._show_error(
                'Буфер пуст',
                'Сначала выделите текст и нажмите Ctrl+C.\n\nПосле этого нажмите Ctrl+Shift+Q или Ctrl+Alt+Q.')
            return
        self._do_translate(text, popup=True)

    def _translate_from_clipboard_btn(self):
        text = get_clipboard_text().strip()
        if not text:
            self._show_error('Буфер пуст',
                              'Скопируйте текст (Ctrl+C) и попробуйте снова.')
            return
        self._do_translate(text, popup=False)

    def _clear_clipboard(self):
        try:
            if user32.OpenClipboard(None):
                try:
                    if user32.CountClipboardFormats() == 0:
                        self.clear_buffer_btn.config(text=self._t('✓  Буфер уже очищен'))
                        self.root.after(1200, lambda: self.clear_buffer_btn.config(
                            text=self._t('✕  Очистить буфер'))
                            if self.clear_buffer_btn.winfo_exists() else None)
                        log_event("Очистка буфера: буфер уже пуст")
                        return
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass

        if clear_windows_clipboard():
            log_event("Системный буфер обмена очищен")
            try:
                self.clear_buffer_btn.config(text=self._t('✓  Буфер очищен'))
                self.root.after(1000, lambda: self.clear_buffer_btn.config(
                    text=self._t('✕  Очистить буфер'))
                    if self.clear_buffer_btn.winfo_exists() else None)
            except Exception:
                pass
        else:
            self._show_error(
                'Не удалось очистить буфер',
                'Буфер обмена сейчас занят другой программой.\nПопробуйте нажать кнопку ещё раз.')

    # ============ ПЕРЕВОД ============
    def _clear_input(self):
        try:
            self.input_text.delete("1.0", "end")
            log_event("Текст для перевода очищен")
        except Exception as e:
            log_event(f"Ошибка очистки текста: {e}")

    def _clear_result(self):
        try:
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", "end")
            self.result_text.config(state="disabled")
            self._last_translated = ""
            self._last_source = ""
            self._last_src_lang = ""
            self._last_tgt_lang = ""
            self.src_lang_lbl.config(text=self._t('Авто'))
            self.tgt_lang_lbl.config(text=LANGUAGES.get(self.my_lang, self.my_lang))
            log_event("Перевод очищен")
        except Exception as e:
            log_event(f"Ошибка очистки перевода: {e}")

    def _translate_manual(self):
        text = self.input_text.get("1.0", "end").strip()
        if not text:
            return
        self._do_translate(text, popup=False)

    def _do_translate(self, text, popup=True):
        if not text:
            return

        def _worker():
            try:
                src = "auto"
                tgt = self.my_lang
                translated, detected = translate_any(text, src, tgt)
                if not translated:
                    self.root.after(0, lambda: self._show_error(
                        'Не удалось перевести',
                        'Ни один сервис не ответил.\nПроверьте интернет.'))
                    return
                if detected and detected.split("-")[0] == self.my_lang.split("-")[0]:
                    rev, _ = translate_any(text, detected, self.other_lang)
                    if rev:
                        translated = rev
                        tgt = self.other_lang
                self._last_source = text
                self._last_translated = translated
                self._last_src_lang = detected or "?"
                self._last_tgt_lang = tgt
                log_event(f"Перевод: {detected} → {tgt}")
                self.root.after(0, lambda: self._update_result(text, translated, popup))
            except Exception as e:
                log_event(f"Ошибка: {e}")
                self.root.after(0, lambda: self._show_error('Ошибка', f"{e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _update_result(self, source, translated, show_popup):
        try:
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", translated)
            self.result_text.config(state="disabled")
        except Exception:
            pass
        try:
            if self._last_src_lang and self._last_src_lang != "?":
                self.src_lang_lbl.config(
                    text=LANGUAGES.get(self._last_src_lang,
                                        self._last_src_lang.upper()))
            self.tgt_lang_lbl.config(
                text=LANGUAGES.get(self._last_tgt_lang,
                                    self._last_tgt_lang.upper()))
        except Exception:
            pass
        if show_popup:
            self._show_popup(source, translated)

    # ============ ПОПАП ============
    def _show_popup(self, source, translated):
        self._close_popup()
        T = self.T

        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.resizable(False, False)
        p.configure(bg=T["blue"])

        outer = tk.Frame(p, bg=T["blue"])
        outer.pack(fill="both", expand=True, padx=2, pady=2)
        inner = tk.Frame(outer, bg=T["bg"])
        inner.pack(fill="both", expand=True)

        title_bar = tk.Frame(inner, bg=T["bg"], cursor="fleur")
        title_bar.pack(fill="x", padx=24, pady=(16, 12))

        title = tk.Label(
            title_bar, text=self._t('⚡  Быстрый перевод'),
            bg=T["bg"], fg=T["fg"],
            font=("Segoe UI", 17, "bold"), anchor="w", cursor="fleur")
        title.pack(side="left")

        src_lbl = LANGUAGES.get(self._last_src_lang or "?",
                                 (self._last_src_lang or "?").upper())
        tgt_lbl = LANGUAGES.get(self._last_tgt_lang, self._last_tgt_lang.upper())
        langs = tk.Label(
            title_bar, text=f"{src_lbl}  →  {tgt_lbl}",
            bg=T["bg"], fg=T["fg_dim"],
            font=("Segoe UI", 11), cursor="fleur")
        langs.pack(side="right", pady=3)

        content = tk.Frame(inner, bg=T["bg"])
        content.pack(fill="both", expand=True, padx=24)

        left = tk.Frame(content, bg=T["bg_dark"])
        left.pack(fill="x", pady=(0, 10))
        tk.Label(left, text=self._t('Исходный текст'),
                 bg=T["bg_dark"], fg=T["fg_dim"],
                 font=("Segoe UI", 10, "bold"), anchor="w"
                 ).pack(fill="x", padx=16, pady=(11, 4))

        source_box = tk.Text(
            left, height=8, wrap="word", bg=T["bg_dark"], fg=T["fg"],
            insertbackground=T["fg"], selectbackground=T["blue"],
            selectforeground="white", relief="flat", bd=0,
            font=("Segoe UI", 13), padx=16, pady=8,
            highlightthickness=0, spacing1=2, spacing3=2)
        source_box.pack(fill="x", padx=2, pady=(0, 4))
        source_box.insert("1.0", source)
        source_box.configure(state="disabled")

        right = tk.Frame(content, bg=T["bg"])
        right.pack(fill="x", pady=(0, 12))
        tk.Label(right, text=self._t('Перевод'),
                 bg=T["bg"], fg=T["fg_dim"],
                 font=("Segoe UI", 10, "bold"), anchor="w"
                 ).pack(fill="x", pady=(0, 4))

        result_box = tk.Text(
            right, height=9, wrap="word", bg=T["bg"], fg=T["fg"],
            insertbackground=T["fg"], selectbackground=T["blue"],
            selectforeground="white", relief="flat", bd=0,
            font=("Segoe UI", 16, "bold"), padx=4, pady=5,
            highlightthickness=0, spacing1=2, spacing3=3)
        result_box.pack(fill="x")
        result_box.insert("1.0", translated)
        result_box.configure(state="disabled")

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(fill="x", padx=24, pady=(0, 18))

        def do_copy():
            if set_clipboard_text(translated):
                copy_btn.config(text=self._t('✓  Скопировано'))
                p.after(1200, lambda: copy_btn.config(text=self._t('Копировать')))

        copy_btn = tk.Button(
            btn_row, text=self._t('Копировать'),
            bg=T["btn_start"], fg="white",
            activebackground=T["btn_start_hov"], activeforeground="white",
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            padx=24, pady=9, cursor="hand2", command=do_copy)
        copy_btn.pack(side="left")

        close_btn = tk.Button(
            btn_row, text=self._t('Закрыть'),
            bg=T["action_bg"], fg=T["fg"],
            activebackground=T["action_hover"], activeforeground=T["fg"],
            font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
            padx=24, pady=9, cursor="hand2", command=self._close_popup)
        close_btn.pack(side="left", padx=9)

        def drag_start(e):
            p._dx = e.x_root - p.winfo_x()
            p._dy = e.y_root - p.winfo_y()

        def drag_move(e):
            p.geometry(f"+{e.x_root - p._dx}+{e.y_root - p._dy}")

        for w in (title_bar, title, langs):
            w.bind("<Button-1>", drag_start)
            w.bind("<B1-Motion>", drag_move)

        p.update_idletasks()
        sw, sh = p.winfo_screenwidth(), p.winfo_screenheight()
        pw = min(1200, sw - 60)
        ph = min(800, sh - 80)
        px = max(20, (sw - pw) // 2)
        py = max(20, (sh - ph) // 2)
        p.geometry(f"{pw}x{ph}+{px}+{py}")

        def recenter_popup():
            try:
                if not p.winfo_exists():
                    return
                sw2 = p.winfo_screenwidth()
                sh2 = p.winfo_screenheight()
                x2 = int((sw2 - pw) / 2)
                y2 = int((sh2 - ph) / 2)
                p.geometry(f"{pw}x{ph}+{x2}+{y2}")
                p.lift()
            except Exception:
                pass

        p.after(20, recenter_popup)
        p.after(120, recenter_popup)

        try:
            p.attributes("-topmost", True)
            p.lift()
            p.focus_force()
        except Exception:
            pass

        p.bind("<Escape>", lambda e: self._close_popup())
        self._popup = p
        self._ensure_popup_topmost()

    def _ensure_popup_topmost(self):
        try:
            if not self._popup or not self._popup.winfo_exists():
                return
            self._popup.attributes("-topmost", True)
            self._popup.lift()
            self._popup_topmost_job = self.root.after(
                500, self._ensure_popup_topmost)
        except Exception:
            pass

    def _close_popup(self):
        if self._popup_topmost_job:
            try:
                self.root.after_cancel(self._popup_topmost_job)
            except Exception:
                pass
            self._popup_topmost_job = None
        try:
            if self._popup and self._popup.winfo_exists():
                self._popup.destroy()
        except Exception:
            pass
        self._popup = None

    # ============ ИКОНКА ============
    def _make_icon_image(self):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        color = self.T["blue"]
        d.ellipse((2, 2, size - 2, size - 2), fill=color)
        font = None
        for fname in ("seguiemj.ttf", "arialbd.ttf", "segoeuib.ttf"):
            try:
                font = ImageFont.truetype(fname, 40)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        try:
            bbox = d.textbbox((0, 0), "🌐", font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
                   "🌐", font=font, fill="white")
        except Exception:
            d.text((14, 14), "A", fill="white")
        return img

    # ============ ТРЕЙ ============
    def _build_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem(self._t('Показать окно'), self._tray_open, default=True),
            pystray.MenuItem(self._t('Перевести буфер'), self._tray_translate_buf),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._t('Поменять языки'), self._tray_swap),
            pystray.MenuItem(self._t('Автозапуск Windows'), pystray.Menu(
                pystray.MenuItem(self._t('Через реестр'),
                                  self._tray_autostart_registry,
                                  checked=lambda i: _get_autostart_mode() == "registry"),
                pystray.MenuItem(self._t('Через папку Startup'),
                                  self._tray_autostart_startup,
                                  checked=lambda i: _get_autostart_mode() == "startup"),
                pystray.MenuItem(self._t('Отключить автозагрузку'),
                                  self._tray_autostart_disable,
                                  checked=lambda i: _get_autostart_mode() == "off"),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    self._t('Запускать вместе с Windows свёрнутым в трей'),
                    self._tray_toggle_start_in_tray,
                    checked=lambda i: bool(self.settings.get("start_in_tray", False)))
            )),
            pystray.MenuItem(self._t('Настройки'), self._tray_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._t('Выход'), self._tray_quit),
        )

    def _rebuild_tray_menu(self):
        if not TRAY_OK or not self.tray_icon:
            return
        try:
            self.tray_icon.menu = self._build_tray_menu()
            self.tray_icon.title = self._t('Мини-переводчик')
            self.tray_icon.update_menu()
        except Exception:
            pass

    def _setup_tray(self):
        if not TRAY_OK:
            return

        def _run():
            try:
                icon = pystray.Icon(
                    "mini_translator", self._make_icon_image(),
                    self._t('Мини-переводчик'), self._build_tray_menu())
                self.tray_icon = icon
                icon.run()
            except Exception as e:
                log_event(f"Трей: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _tray_open(self, icon=None, item=None):
        self.root.after(0, self._restore_main)

    def _tray_translate_buf(self, icon=None, item=None):
        self.root.after(0, self._translate_from_clipboard_btn)

    def _tray_swap(self, icon=None, item=None):
        self.root.after(0, self._swap_languages)

    def _tray_autostart_registry(self, icon=None, item=None):
        def apply():
            if _set_registry_autostart(True):
                _set_startup_autostart(False)
                self.settings["autostart_registry"] = True
                self.settings["autostart_startup"] = False
                save_settings(self.settings)
                log_event("Автозапуск: через реестр")
            else:
                self._show_error('Ошибка',
                                  'Не удалось включить автозапуск через реестр.')
        self.root.after(0, apply)

    def _tray_autostart_startup(self, icon=None, item=None):
        def apply():
            if _set_startup_autostart(True):
                _set_registry_autostart(False)
                self.settings["autostart_registry"] = False
                self.settings["autostart_startup"] = True
                save_settings(self.settings)
                log_event("Автозапуск: через папку Startup")
            else:
                self._show_error('Ошибка',
                                  'Не удалось создать ярлык в папке Startup.')
        self.root.after(0, apply)

    def _tray_autostart_disable(self, icon=None, item=None):
        def apply():
            _set_registry_autostart(False)
            _set_startup_autostart(False)
            self.settings["autostart_registry"] = False
            self.settings["autostart_startup"] = False
            save_settings(self.settings)
            log_event("Автозапуск: отключён")
        self.root.after(0, apply)

    def _tray_toggle_start_in_tray(self, icon=None, item=None):
        def apply():
            self.settings["start_in_tray"] = not bool(
                self.settings.get("start_in_tray", False))
            save_settings(self.settings)
            log_event("Запуск свёрнутым в трей: " +
                       ("включён" if self.settings["start_in_tray"] else "выключен"))
        self.root.after(0, apply)

    def _tray_settings(self, icon=None, item=None):
        self.root.after(0, self._open_settings_dialog)

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self._really_quit)

    def _restore_main(self):
        self.root.deiconify()
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass
        self._center_main_window()
        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    # ============ НАСТРОЙКИ ============
    def _open_settings_dialog(self):
        if self._settings_dlg is not None:
            try:
                if self._settings_dlg.winfo_exists():
                    self._settings_dlg.lift()
                    return
            except Exception:
                pass
            self._settings_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["blue"])
        self._settings_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(18, 10))
        tk.Label(top, text="⚙", bg=T["bg"], fg=T["blue"],
                 font=("Segoe UI", 20)).pack(side="left", padx=(0, 10))
        tk.Label(top, text=self._t('Настройки'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        tk.Label(inner, text=self._t('Мой язык (перевод на него)'),
                 bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9)
                 ).pack(anchor="w", padx=22, pady=(8, 2))
        name_to_code = {v: k for k, v in LANGUAGES.items()}
        my_var = tk.StringVar(value=LANGUAGES.get(self.my_lang, self.my_lang))
        my_menu = tk.OptionMenu(inner, my_var,
                                 *[LANGUAGES[k] for k in LANGUAGES.keys()])
        my_menu.config(bg=T["entry_bg"], fg=T["fg"],
                        activebackground=T["action_hover"],
                        activeforeground=T["fg"],
                        highlightthickness=0, bd=0,
                        font=("Segoe UI", 10), relief="flat",
                        width=25, anchor="w")
        my_menu["menu"].config(bg=T["entry_bg"], fg=T["fg"],
                                 activebackground=T["action_hover"],
                                 activeforeground=T["fg"],
                                 font=("Segoe UI", 10))
        my_menu.pack(fill="x", padx=22, ipady=2)

        tk.Label(inner, text=self._t('Второй язык (для обратного перевода)'),
                 bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9)
                 ).pack(anchor="w", padx=22, pady=(10, 2))
        other_var = tk.StringVar(
            value=LANGUAGES.get(self.other_lang, self.other_lang))
        other_menu = tk.OptionMenu(inner, other_var,
                                    *[LANGUAGES[k] for k in LANGUAGES.keys()])
        other_menu.config(bg=T["entry_bg"], fg=T["fg"],
                           activebackground=T["action_hover"],
                           activeforeground=T["fg"],
                           highlightthickness=0, bd=0,
                           font=("Segoe UI", 10), relief="flat",
                           width=25, anchor="w")
        other_menu["menu"].config(bg=T["entry_bg"], fg=T["fg"],
                                    activebackground=T["action_hover"],
                                    activeforeground=T["fg"],
                                    font=("Segoe UI", 10))
        other_menu.pack(fill="x", padx=22, ipady=2)

        info = tk.Frame(inner, bg=T["bg"])
        info.pack(fill="x", padx=22, pady=(14, 0))

        tk.Label(info, text=self._t('Как пользоваться'),
                 bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            info,
            text=self._t('1. Выделите текст в любой программе.\n2. Нажмите Ctrl+C, чтобы скопировать его.\n3. Нажмите хоткей — переводчик возьмёт текст из буфера и переведёт его.\n\nХоткеи:\n  Ctrl+Shift+Q — быстро перевести текст из буфера\n  Ctrl+Alt+Q   — альтернативный хоткей для той же функции\n\nВажно: хоткей не копирует текст сам. Сначала обязательно нажмите Ctrl+C.\nEsc в окне быстрого перевода — закрыть окно.'),
            bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9),
            justify="left", anchor="w", wraplength=420).pack(fill="x", pady=(5, 0))

        tk.Label(info, text=self._t('Перевод'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 10, "bold"), anchor="w"
                 ).pack(fill="x", pady=(12, 0))
        tk.Label(
            info,
            text=self._t('Кнопка «Перевести» — переводит текст, который вы ввели в поле выше.\n«📋 Перевести буфер» — переводит уже скопированный текст.\nХоткеи делают то же самое, что «Перевести буфер», но сразу показывают быстрый результат.\nЯзыки можно поменять кнопкой ⇄ или выбрать в настройках.'),
            bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9),
            justify="left", anchor="w", wraplength=420).pack(fill="x", pady=(5, 0))

        tk.Label(info, text=self._t('Сервисы перевода'),
                 bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 10, "bold"), anchor="w"
                 ).pack(fill="x", pady=(12, 0))
        tk.Label(info,
                 text=self._t('Google → Lingva → Lingva-зеркало → MyMemory\nПереводчик автоматически пробует следующий сервис, если предыдущий не ответил.'),
                 bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9),
                 justify="left", anchor="w", wraplength=420
                 ).pack(fill="x", pady=(5, 0))

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(pady=(18, 16))

        def close_dlg():
            self._settings_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        def do_save():
            my_code = name_to_code.get(my_var.get().strip(), self.my_lang)
            other_code = name_to_code.get(other_var.get().strip(),
                                            self.other_lang)
            if my_code == other_code:
                self._show_error('Ошибка', 'Языки должны быть разными.')
                return
            self.my_lang = my_code
            self.other_lang = other_code
            self.settings["my_lang"] = my_code
            self.settings["other_lang"] = other_code
            save_settings(self.settings)
            self.tgt_lang_lbl.config(
                text=LANGUAGES.get(self.my_lang, self.my_lang))
            log_event(f"Настройки: {self.other_lang} ⇄ {self.my_lang}")
            close_dlg()

        tk.Button(btn_row, text=self._t('Отмена'),
                  bg=T["action_bg"], fg=T["fg"],
                  activebackground=T["action_hover"],
                  activeforeground=T["fg"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=22, pady=8, cursor="hand2",
                  command=close_dlg).pack(side="left", padx=6)
        tk.Button(btn_row, text=self._t('Сохранить'),
                  bg=T["btn_start"], fg="white",
                  activebackground=T["btn_start_hov"],
                  activeforeground="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=22, pady=8, cursor="hand2",
                  command=do_save).pack(side="left", padx=6)

        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"+{(sw - dw) // 2}+{(sh - dh) // 2}")

        def _drag_start(e):
            dlg._dx = e.x_root - dlg.winfo_x()
            dlg._dy = e.y_root - dlg.winfo_y()

        def _drag_move(e):
            dlg.geometry(f"+{e.x_root - dlg._dx}+{e.y_root - dlg._dy}")

        top.bind("<Button-1>", _drag_start)
        top.bind("<B1-Motion>", _drag_move)
        dlg.bind("<Escape>", lambda e: close_dlg())

    # ============ ЖУРНАЛ ============
    def _open_log_window(self):
        if self._log_dlg is not None:
            try:
                if self._log_dlg.winfo_exists():
                    self._log_dlg.lift()
                    self._refresh_log()
                    return
            except Exception:
                pass
            self._log_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["green"])
        self._log_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(18, 8))
        tk.Label(top, text="📋", bg=T["bg"], fg=T["green"],
                 font=("Segoe UI", 18)).pack(side="left", padx=(0, 10))
        tk.Label(top, text=self._t('Журнал'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        text_wrap = tk.Frame(inner, bg=T["entry_border"])
        text_wrap.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        self._log_text = tk.Text(text_wrap, height=14, width=60,
                                  bg=T["entry_bg"], fg=T["fg"],
                                  insertbackground=T["fg"],
                                  font=("Consolas", 9), relief="flat",
                                  bd=0, wrap="word")
        self._log_text.pack(padx=1, pady=1, fill="both", expand=True)

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(pady=(0, 16))

        def close_dlg():
            self._log_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        tk.Button(btn_row, text=self._t('Закрыть'),
                  bg=T["btn_start"], fg="white",
                  activebackground=T["btn_start_hov"],
                  activeforeground="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=18, pady=8, cursor="hand2",
                  command=close_dlg).pack()

        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"+{(sw - dw) // 2}+{(sh - dh) // 2}")
        dlg.bind("<Escape>", lambda e: close_dlg())
        self._refresh_log()

    def _refresh_log(self):
        try:
            self._log_text.config(state="normal")
            self._log_text.delete("1.0", "end")
            self._log_text.insert("end", get_log_text())
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        except Exception:
            pass

    # ============ ОШИБКИ ============
    def _show_error(self, title_key, message_key):
        title = self._t(title_key) if title_key in UI_TR else title_key
        message = self._t(message_key) if message_key in UI_TR else message_key

        if self._warning_dlg is not None:
            try:
                if self._warning_dlg.winfo_exists():
                    self._warning_dlg.lift()
                    return
            except Exception:
                pass
            self._warning_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["orange"])
        self._warning_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(20, 10))
        tk.Label(top, text="⚠", bg=T["bg"], fg=T["orange"],
                 font=("Segoe UI", 22)).pack(side="left", padx=(0, 12))
        tk.Label(top, text=title, bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 13, "bold")).pack(side="left")

        tk.Label(inner, text=message, bg=T["bg"], fg=T["fg_dim"],
                 justify="left", font=("Segoe UI", 10),
                 wraplength=380).pack(padx=22, pady=(0, 16), anchor="w")

        def close_dlg():
            self._warning_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        ok = tk.Button(inner, text=self._t('Понятно'),
                       bg=T["orange"], fg="#1a1a1a",
                       activebackground=T["orange"],
                       activeforeground="#1a1a1a",
                       font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                       padx=26, pady=8, cursor="hand2",
                       command=close_dlg)
        ok.pack(pady=(0, 18))

        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"+{(sw - dw) // 2}+{(sh - dh) // 2}")
        dlg.bind("<Escape>", lambda e: close_dlg())
        dlg.bind("<Return>", lambda e: close_dlg())
        ok.focus_set()

    # ============ ЗАКРЫТИЕ ============
    def _really_quit(self):
        log_event("=== Выход ===")
        self._close_popup()
        try:
            if self._hotkey_thread_id:
                user32.PostThreadMessageW(self._hotkey_thread_id,
                                            WM_QUIT, 0, 0)
        except Exception:
            pass
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            os._exit(0)
        except Exception:
            pass

    def _poll_signal(self):
        try:
            if os.path.exists(SIGNAL_FILE):
                try:
                    os.remove(SIGNAL_FILE)
                except Exception:
                    pass
                self._restore_main()
        except Exception:
            pass
        try:
            self.root.after(500, self._poll_signal)
        except Exception:
            pass

    def _apply_icon(self):
        if not TRAY_OK:
            return
        try:
            img = self._make_icon_image()
            ico_path = os.path.join(tempfile.gettempdir(),
                                     "mini_translator.ico")
            img.save(ico_path, format="ICO",
                     sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            self.root.iconbitmap(default=ico_path)
            photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, photo)
            self._icon_photo = photo
        except Exception:
            pass

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.root.mainloop()


if __name__ == "__main__":
    if not acquire_single_instance():
        signal_existing_instance()
        time.sleep(0.15)
        sys.exit(0)

    if not TRAY_OK:
        import tkinter.messagebox as mb
        mb.showerror("Ошибка",
                      "Нужны библиотеки pystray и Pillow.\n\n"
                      "pip install pystray Pillow")
        sys.exit(1)

    App().run()