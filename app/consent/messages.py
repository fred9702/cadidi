REGISTRATION_LINK = "https://chomei.store/register"

MESSAGES = {
    "unknown": {
        "fr": (
            "Ce service est réservé aux participants inscrits à "
            f"#BuildingResilience. Pour vous inscrire : {REGISTRATION_LINK}"
        ),
    },
    "consent_prompt": {
        "fr": (
            "Bienvenue à #BuildingResilience ! Je suis votre assistant IA pour "
            "l'événement. Pour continuer, j'ai besoin de votre consentement. "
            "Vos messages seront traités par une intelligence artificielle et "
            "vos données seront anonymisées conformément au RGPD. "
            "Répondez OUI pour accepter."
        ),
        "en": (
            "Welcome to #BuildingResilience! I'm your AI assistant for the "
            "event. To continue, I need your consent. Your messages will be "
            "processed by artificial intelligence and your data will be "
            "anonymised in compliance with GDPR. Reply YES to accept."
        ),
        "es": (
            "Bienvenido/a a #BuildingResilience. Soy su asistente IA para el "
            "evento. Para continuar, necesito su consentimiento. Sus mensajes "
            "serán procesados por inteligencia artificial y sus datos serán "
            "anonimizados conforme al RGPD. Responda SÍ para aceptar."
        ),
        "pt": (
            "Bem-vindo/a ao #BuildingResilience! Sou o seu assistente IA para "
            "o evento. Para continuar, preciso do seu consentimento. As suas "
            "mensagens serão processadas por inteligência artificial e os seus "
            "dados serão anonimizados em conformidade com o RGPD. "
            "Responda SIM para aceitar."
        ),
    },
    "opted_out": {
        "fr": (
            "Vous vous êtes désabonné(e). Vos données anonymisées sont "
            "conservées. Pour vous réinscrire, envoyez REJOINDRE."
        ),
        "en": (
            "You have unsubscribed. Your anonymised data is retained. "
            "To re-subscribe, send JOIN."
        ),
        "es": (
            "Se ha dado de baja. Sus datos anonimizados se conservan. "
            "Para volver a suscribirse, envíe UNIRSE."
        ),
        "pt": (
            "Cancelou a subscrição. Os seus dados anonimizados são "
            "conservados. Para se reinscrever, envie JUNTAR."
        ),
    },
    "welcome_back": {
        "fr": (
            "Bon retour ! Votre accès à l'assistant #BuildingResilience "
            "est réactivé. Comment puis-je vous aider ?"
        ),
        "en": (
            "Welcome back! Your access to the #BuildingResilience assistant "
            "has been reactivated. How can I help you?"
        ),
        "es": (
            "Bienvenido/a de nuevo. Su acceso al asistente "
            "#BuildingResilience ha sido reactivado. ¿En qué puedo ayudarle?"
        ),
        "pt": (
            "Bem-vindo/a de volta! O seu acesso ao assistente "
            "#BuildingResilience foi reativado. Como posso ajudá-lo/a?"
        ),
    },
}


def get_message(message_type: str, language: str) -> str:
    """Get a localised message. Falls back to French if language not found."""
    templates = MESSAGES[message_type]
    if message_type == "unknown":
        return templates["fr"]
    return templates.get(language, templates["fr"])
