"""Enriquecimiento de estilo por LLM — traduce el prompt a un perfil musical accionable."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.music.genre_catalog import format_genre_catalog_for_llm, normalize_genres
from cadence.music.style_profile import sanitize_style_references
from cadence.schemas.song_state import MusicalStyleProfile, SongState


def tag_enricher_node(state: SongState) -> dict:
    """
    Construye MusicalStyleProfile desde el prompt del usuario.
    Sustituye la lista rígida de 4 tags del router como fuente de verdad.
    """
    intent = state["intent"]

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("tag_enricher"),
    ).with_structured_output(MusicalStyleProfile)

    hints = ", ".join(intent.style_tags) if intent.style_tags else "ninguna"
    catalog = format_genre_catalog_for_llm()

    system = SystemMessage(content=(
        "Eres un director musical para videojuegos. Tu tarea es INTERPRETAR el prompt "
        "del usuario y producir un perfil de estilo accionable para composición.\n\n"
        f"{catalog}\n\n"
        "Reglas:\n"
        "- Traduce referencias concretas (juegos, artistas, películas) a ids del CATÁLOGO, "
        "no a etiquetas genéricas incorrectas.\n"
        "  Ej: 'Super Bomberman' → party game, techno, house, snes — NO chiptune.\n"
        "  Ej: 'boss fight techno dubstep' → boss fight, techno, dubstep, brostep, industrial.\n"
        "- genres: elige 3–8 ids EXACTOS del catálogo.\n"
        "- references: SOLO nombres propios literales del prompt (juego, artista, película, OST). "
        "Si el prompt no nombra ninguno, deja references=[]. "
        "NO pongas géneros del catálogo, moods ni palabras del propio brief (techno, dubstep, boss fight…).\n"
        "- instrumentation: timbres/roles deseados en lenguaje natural.\n"
        "- avoid: timbres o familias que NO encajan. Usa frases explícitas "
        "(no drums, without percussion) si quieres omitir batería; "
        "'drum machines' solo rechaza kits electrónicos, no taiko ni orquesta.\n"
        "- Si el prompt pide orquestación COMPACTA o pocos instrumentos a la vez "
        "(plataforma, Kraid, boss compacto): géneros action/platform/combat — "
        "NO uses orchestral/symphonic/cinematic como géneros principales.\n"
        "- Si pide chiptune/eurobeat/arcade denso: chiptune, eurobeat, arcade.\n"
        "- Si pide boss orquestal épico con muchas capas: orchestral, symphonic, epic.\n"
        "- drum_character: una frase sobre el groove (four-on-floor, half-time dubstep…).\n"
        "- reasoning: 1–2 frases explicando la traducción.\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Prompt del usuario: {intent.raw_prompt}\n"
        f"Uso: {intent.use_case}\n"
        f"Mood (router): {intent.mood}\n"
        f"Pistas del router (opcionales): {hints}\n"
    ))

    profile: MusicalStyleProfile = llm.invoke([system, human])
    genres = normalize_genres(profile.genres)
    normalized = profile.model_copy(
        update={
            "genres": genres,
            "references": sanitize_style_references(profile.references, genres),
        },
    )
    return {"style_profile": normalized}
