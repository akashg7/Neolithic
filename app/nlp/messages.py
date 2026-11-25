"""Pre-translated fixed messages. Sent as-is, NEVER translated live.

!! DRAFTS. The mr/hi text was written by Claude and has NOT been reviewed by a
!! native speaker. The plan requires native-speaker review before the demo.
!! Flip REVIEWED[lang] to True only after review; `python -m app.nlp.messages`
!! prints what is still unreviewed.
"""
from __future__ import annotations

LANGS = ("en", "mr", "hi")
REVIEWED: dict[str, bool] = {"en": True, "mr": False, "hi": False}

MESSAGES: dict[str, dict[str, str]] = {
    # window_engine returned NO_ADVICE: must not suggest holding or selling.
    "NO_ADVICE": {
        "en": "I can't give a clear sell-or-hold recommendation right now because the price forecast "
        "is not reliable enough for this crop and market. Please check today's mandi price and the "
        "forecast range on the card before deciding.",
        "mr": "सध्या या पिकासाठी आणि बाजारासाठी भावाचा अंदाज पुरेसा विश्वासार्ह नाही, त्यामुळे मी विकायचे की "
        "थांबायचे याचा स्पष्ट सल्ला देऊ शकत नाही. निर्णय घेण्यापूर्वी आजचा बाजारभाव आणि कार्डवरील "
        "अंदाजाची श्रेणी तपासा.",
        "hi": "फिलहाल इस फसल और मंडी के लिए भाव का अनुमान पर्याप्त भरोसेमंद नहीं है, इसलिए मैं बेचने या रुकने "
        "की स्पष्ट सलाह नहीं दे सकता। फ़ैसला लेने से पहले आज का मंडी भाव और कार्ड पर दिखी अनुमान सीमा देखें।",
    },
    # number check failed twice / translation unavailable.
    "FALLBACK": {
        "en": "Sorry, I couldn't prepare a reliable answer right now. Please check the details on the "
        "card below, or try asking again.",
        "mr": "क्षमस्व, सध्या मी विश्वासार्ह उत्तर तयार करू शकलो नाही. कृपया खालील कार्डवरील माहिती पाहा किंवा "
        "पुन्हा विचारून पाहा.",
        "hi": "क्षमा करें, अभी मैं भरोसेमंद जवाब तैयार नहीं कर पाया। कृपया नीचे कार्ड की जानकारी देखें या "
        "दोबारा पूछकर देखें।",
    },
    "ASK_QUANTITY": {
        "en": "How much do you want to sell? For example, 20 bags or 5 quintals.",
        "mr": "तुम्हाला किती माल विकायचा आहे? उदाहरणार्थ २० बोरी किंवा ५ क्विंटल.",
        "hi": "आप कितना माल बेचना चाहते हैं? जैसे 20 बोरी या 5 क्विंटल।",
    },
    "ASK_MANDI": {
        "en": "Which mandi do you want to check?",
        "mr": "कोणत्या मंडीचा भाव पाहायचा आहे?",
        "hi": "आप किस मंडी का भाव देखना चाहते हैं?",
    },
    "ASK_COMMODITY": {
        "en": "Which crop are you asking about?",
        "mr": "तुम्ही कोणत्या पिकाबद्दल विचारत आहात?",
        "hi": "आप किस फसल के बारे में पूछ रहे हैं?",
    },
    # unit with no fixed size (khandi, goni, maund).
    "ASK_UNIT": {
        "en": "The size of a khandi or goni differs from place to place. Please tell me the quantity in "
        "kg, quintals or bags.",
        "mr": "खंडी किंवा गोणीचे वजन ठिकाणानुसार वेगळे असते. कृपया माल किलो, क्विंटल किंवा बोरीमध्ये सांगा.",
        "hi": "खंडी या गोनी का वज़न जगह के हिसाब से अलग होता है। कृपया माल किलो, क्विंटल या बोरी में बताएँ।",
    },
    # chemicals guard.
    "CHEMICAL_REFERRAL": {
        "en": "I can't advise on pesticides or chemical doses. Please contact your nearest Krishi Vigyan "
        "Kendra (KVK) for this.",
        "mr": "कीटकनाशके किंवा रसायनांच्या मात्रेबाबत मी सल्ला देऊ शकत नाही. कृपया यासाठी तुमच्या जवळच्या कृषी "
        "विज्ञान केंद्राशी (KVK) संपर्क साधा.",
        "hi": "मैं कीटनाशकों या रसायनों की मात्रा पर सलाह नहीं दे सकता। कृपया इसके लिए अपने नज़दीकी कृषि "
        "विज्ञान केंद्र (KVK) से संपर्क करें।",
    },
}


def get_message(key: str, lang: str) -> str:
    """Pre-translated message; unknown language falls back to English."""
    by_lang = MESSAGES[key]
    return by_lang.get(lang, by_lang["en"])


def english_template_key(text: str) -> str | None:
    """If `text` is exactly one of the English templates, return its key."""
    t = text.strip()
    for key, by_lang in MESSAGES.items():
        if by_lang["en"] == t:
            return key
    return None


def unreviewed() -> list[str]:
    return [lang for lang in LANGS if not REVIEWED.get(lang)]


if __name__ == "__main__":
    pending = unreviewed()
    print(f"{len(MESSAGES)} messages x {len(LANGS)} languages")
    print("NEEDS NATIVE-SPEAKER REVIEW:" if pending else "all reviewed", ", ".join(pending))
