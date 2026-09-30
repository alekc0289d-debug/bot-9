"""
Tugma matnlarini locale fayllaridan (uz/uz-cyrl/ru) avtomatik yig'ish.

MUAMMO (avval): har bir handler faylida tugma matnlari qo'lda ko'chirib
yozilgan edi (masalan ACH_BTNS = {"🎖 Yutuqlarim", ...}). Locale fayldagi
haqiqiy matn bir harf yoki emoji bilan farq qilsa (masalan "🎯" vs "🎖"),
tugma umuman ishlamay qolardi — yoki battarrog'i, boshqa rol tugmasi
bilan bir xil matn chiqib, noto'g'ri handler ishga tushardi (masalan
parentning "Baholari" tugmasi studentning "Baholarim" handleriga tushib,
admin ekranida talaba xatoliklari chiqishi shu sababdan edi).

Bu yerda BITTA manba (locale JSON) dan tugma to'plami yasaladi, shuning
uchun reply keyboard va handler filtri hech qachon bir-biridan farq
qilmaydi.
"""

from bot.locales.loader import _translations


def variants(*keys: str) -> set:
    """Berilgan locale kalit(lar)i uchun barcha tillardagi matnlarni qaytaradi."""
    out = set()
    for lang, table in _translations.items():
        for key in keys:
            v = table.get(key)
            if v:
                out.add(v)
    return out
