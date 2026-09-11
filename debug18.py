from app.chunking.structure_aware import count_tokens, MIN_TOKENS

text = "118 | JPMorgan Chase & Co./2023 Form 10-K"
print(f"MIN_TOKENS = {MIN_TOKENS}")
print(f"count_tokens({text!r}) = {count_tokens(text)}")

text2 = "116 | JPMorgan Chase & Co./2023 Form 10-K"
print(f"count_tokens({text2!r}) = {count_tokens(text2)}")
