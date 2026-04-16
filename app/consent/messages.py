REGISTRATION_LINK = "https://resilience241.com/register"

MESSAGES = {
    "unknown": {
        "fr": (
            "Ce service est réservé aux participants inscrits à "
            f"#BuildingResilience. Pour vous inscrire : {REGISTRATION_LINK}"
        ),
        "en": (
            "This service is reserved for registered #BuildingResilience "
            f"participants. To register: {REGISTRATION_LINK}"
        ),
        "es": (
            "Este servicio está reservado a los participantes inscritos en "
            f"#BuildingResilience. Para inscribirse: {REGISTRATION_LINK}"
        ),
        "pt": (
            "Este serviço é reservado aos participantes inscritos no "
            f"#BuildingResilience. Para se inscrever: {REGISTRATION_LINK}"
        ),
    },
    "consent_prompt": {
        "fr": (
            "Bienvenue à #BuildingResilience ! Je suis Cadidi, votre assistant "
            "IA pour l'événement. Pour continuer, j'ai besoin de votre "
            "consentement. Vos messages seront traités par une intelligence "
            "artificielle et vos données seront anonymisées conformément au "
            "RGPD. Répondez OUI pour accepter."
        ),
        "en": (
            "Welcome to #BuildingResilience! I'm Cadidi, your AI assistant "
            "for the event. To continue, I need your consent. Your messages "
            "will be processed by artificial intelligence and your data will "
            "be anonymised in compliance with GDPR. Reply YES to accept."
        ),
        "es": (
            "Bienvenido/a a #BuildingResilience. Soy Cadidi, su asistente IA "
            "para el evento. Para continuar, necesito su consentimiento. Sus "
            "mensajes serán procesados por inteligencia artificial y sus "
            "datos serán anonimizados conforme al RGPD. Responda SÍ para "
            "aceptar."
        ),
        "pt": (
            "Bem-vindo/a ao #BuildingResilience! Sou a Cadidi, o seu "
            "assistente IA para o evento. Para continuar, preciso do seu "
            "consentimento. As suas mensagens serão processadas por "
            "inteligência artificial e os seus dados serão anonimizados em "
            "conformidade com o RGPD. Responda SIM para aceitar."
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
            "Bon retour ! Cadidi est à nouveau à votre service pour "
            "#BuildingResilience. Comment puis-je vous aider ?"
        ),
        "en": (
            "Welcome back! Cadidi is at your service again for "
            "#BuildingResilience. How can I help you?"
        ),
        "es": (
            "Bienvenido/a de nuevo. Cadidi vuelve a estar a su servicio "
            "para #BuildingResilience. ¿En qué puedo ayudarle?"
        ),
        "pt": (
            "Bem-vindo/a de volta! A Cadidi está novamente ao seu serviço "
            "para #BuildingResilience. Como posso ajudá-lo/a?"
        ),
    },
    "welcome_menu": {
        "fr": (
            "Bienvenue ! Je suis Cadidi, votre assistant IA pour "
            "#BuildingResilience.\n\n"
            "Comment puis-je vous aider ? Par exemple :\n"
            "1) La campagne #BuildingResilience\n"
            "2) Le cadre CAP 241\n"
            "3) La Fondation Ma Bannière\n"
            "4) Le programme de l'événement\n"
            "5) L'OAFLAD/OPDAD\n\n"
            "Vous pouvez aussi poser n'importe quelle question librement."
        ),
        "en": (
            "Welcome! I'm Cadidi, your AI assistant for "
            "#BuildingResilience.\n\n"
            "How can I help you? For example:\n"
            "1) The #BuildingResilience campaign\n"
            "2) The CAP 241 framework\n"
            "3) The Ma Bannière Foundation\n"
            "4) The event programme\n"
            "5) OAFLAD/OPDAD\n\n"
            "You can also ask any question freely."
        ),
        "es": (
            "¡Bienvenido/a! Soy Cadidi, su asistente IA para "
            "#BuildingResilience.\n\n"
            "¿En qué puedo ayudarle? Por ejemplo:\n"
            "1) La campaña #BuildingResilience\n"
            "2) El marco CAP 241\n"
            "3) La Fundación Ma Bannière\n"
            "4) El programa del evento\n"
            "5) OAFLAD/OPDAD\n\n"
            "También puede hacer cualquier pregunta libremente."
        ),
        "pt": (
            "Bem-vindo/a! Sou a Cadidi, o seu assistente IA para "
            "#BuildingResilience.\n\n"
            "Como posso ajudá-lo/a? Por exemplo:\n"
            "1) A campanha #BuildingResilience\n"
            "2) O quadro CAP 241\n"
            "3) A Fundação Ma Bannière\n"
            "4) O programa do evento\n"
            "5) OAFLAD/OPDAD\n\n"
            "Também pode fazer qualquer pergunta livremente."
        ),
    },
    "escalation_holding": {
        "fr": (
            "Votre demande est prise en charge par l'équipe organisatrice. "
            "Vous recevrez une réponse prochainement dans cette conversation."
        ),
        "en": (
            "Your request is being handled by the organising team. "
            "You'll receive a response shortly in this conversation."
        ),
        "es": (
            "Su solicitud está siendo gestionada por el equipo organizador. "
            "Recibirá una respuesta en breve en esta conversación."
        ),
        "pt": (
            "O seu pedido está a ser tratado pela equipa organizadora. "
            "Receberá uma resposta em breve nesta conversa."
        ),
    },
}


def get_message(message_type: str, language: str) -> str:
    """Get a localised message. Falls back to French if language not found."""
    templates = MESSAGES[message_type]
    return templates.get(language, templates["fr"])
