"""Launch local OpenAI audio with a hidden, process-only key prompt."""
import argparse
import getpass
import os
import sys
import warnings

from .speech import OpenAISpeech


def private_key():
    configured = os.getenv("OPENAI_API_KEY", "").strip()
    if configured:
        return configured
    if not sys.stdin.isatty():
        raise ValueError("Ouvre un terminal interactif pour la saisie masquee.")
    with warnings.catch_warnings():
        # Never permit getpass's fallback to echoed stdin.
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("Cle API OpenAI (saisie masquee) : ").strip()
        except (getpass.GetPassWarning, EOFError):
            raise ValueError("La saisie masquee est indisponible dans ce terminal.") from None
    if not key or any(character.isspace() for character in key):
        raise ValueError("Cle vide ou format invalide. Aucun secret n'a ete affiche.")
    return key


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001, help="Local port; 8001 avoids the existing offline demo")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Port attendu entre 1024 et 65535")
    try:
        key = private_key()
    except (ValueError, KeyboardInterrupt) as error:
        print(str(error) if isinstance(error, ValueError) else "Saisie annulee.", file=sys.stderr)
        return 1
    # No .env, user profile, command argument, shell history or new environment
    # variable contains the entered key; only this server process holds it.
    provider = OpenAISpeech(key,
                            transcription_model=os.getenv("VOICE_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
                            speech_model=os.getenv("VOICE_TTS_MODEL", "gpt-4o-mini-tts"))
    del key
    from .app import create_app
    import uvicorn

    app = create_app(speech=provider, allowed_origins={f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"})
    print(f"Backend audio local : http://127.0.0.1:{args.port}")
    print("VI/EN disponibles. Une requete audio peut etre facturee par OpenAI.")
    print("Aucun appel audio n'est effectue au demarrage. Ctrl+C pour arreter.")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
