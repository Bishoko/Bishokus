from unidecode import unidecode

def normalize_wordplay(input: str) -> str:
    base_length = len(input)
    
    map = {
        "quoi": ["quoi", "koi", "kwoi", "qwa", "pq", "pk", "tfk", "tfq", "coi"],
        "hein": ["hein", "hin"],
        "oui": ["oui", "woui", "ui", "wui", "wi", "vui"],
        "ouais": ["ouais", "ouai", "wouais", "wouai", "oue", "oe", "we"],
        "non": ["non", "nn", "nan", "nion", "sinon", "sinn", "sinan", "nom"],
        "chaud": ["chaud", "cho", "chaux", "chox"],
        "tulasvu": ["tu las vu", "tu la vu", "la tu vu", "las tu vu"],
        "ah": ["ah", "a"],
        "re": ["re"]
    }
    
    # special case
    if input.lower().strip() == "h1":
        return "hein"
    
    # Remove duplicate letters and numbers when they are next to each other, and lowercase the input
    input = ''.join(ch for i, ch in enumerate(input) if i == 0 or ch.lower() != input[i - 1].lower() or not ch.isalnum()).lower()
    # Replace numbers (skip if base word is max 3 characters and is not "oui")
    if base_length > 3:
        input = input.replace("1", "i").replace("0", "o").replace("3", "e")
    
    if base_length == 3 and input[0] == "0":
        input = "o" + input[1:]  # special case for "oui","oue" to avoid cheating
    
    if base_length > 2 and not input.endswith("4"):
        # special case for "ah" to avoid replying to a sentence ending with "4"
        input = input.replace("4", "a")
    
    # Remove accents and strip
    input = unidecode(input).strip()
    # Remove symbols
    input = ''.join(ch for ch in input if ch.isalnum() or ch == " ")
    
    for key, values in map.items():
        for value in values:
            if value == input or input.endswith(" " + value):
                return key
    return ""

if __name__ == "__main__":
    while True:
        user_input = input("Input: ")
        normalized = normalize_wordplay(user_input)
        print(f"Normalized: {normalized}")
