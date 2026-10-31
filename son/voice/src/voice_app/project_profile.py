"""One tracked conversation profile shared by server and generated browser code."""
import argparse
import json
from pathlib import Path
import re

PROFILE_PATH = Path(__file__).with_name("project_profile.json")
CLIENT_PATH = Path(__file__).parent / "static" / "realtime-client.js"
BEGIN = "// BEGIN GENERATED PROJECT VOICE PROFILE"
END = "// END GENERATED PROJECT VOICE PROFILE"


def load_profile():
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if not isinstance(profile.get("id"), str) or not profile["id"]:
        raise ValueError("Voice profile ID missing")
    for key in ("language_instructions", "greetings"):
        if set(profile.get(key, {})) != {"vi", "en"} or not all(isinstance(value, str) and value for value in profile[key].values()):
            raise ValueError("Voice profile must define VI and EN")
    if not isinstance(profile.get("instructions"), list) or not profile["instructions"] or not all(isinstance(item, str) and item for item in profile["instructions"]):
        raise ValueError("Voice instructions missing")
    return profile


def project_instructions(language):
    profile = load_profile()
    return profile["language_instructions"][language] + "\n\n" + "\n\n".join(profile["instructions"])


def render_client(source):
    block = BEGIN + "\nexport const PROJECT_VOICE_PROFILE = " + json.dumps(load_profile(), ensure_ascii=False, indent=2) + ";\n" + END
    rendered, count = re.subn(re.escape(BEGIN) + r".*?" + re.escape(END), lambda match: block, source, flags=re.S)
    if count != 1:
        raise ValueError("Expected exactly one generated profile block")
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-client", action="store_true")
    args = parser.parse_args()
    source = CLIENT_PATH.read_text(encoding="utf-8")
    rendered = render_client(source)
    if args.write_client:
        CLIENT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        print("Voice client profile generated")
    elif source != rendered:
        raise SystemExit("Voice client profile is stale; run with --write-client")
    else:
        print("Voice profile and browser asset agree")


if __name__ == "__main__":
    main()
