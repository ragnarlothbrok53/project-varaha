import re

def compress(text: str) -> str:
    """ 
    Condenses text by removing redundant whitespace and common filler words. 
    Simplifies the input to maximize token efficiency for local LLM inference.
    """
    if not text:
        return ""

    # Remove extra spaces and newlines
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    # Optional: Remove common LLM 'fluff' words if they are present in high frequency
    fillers = {"basically", "actually", "literally", "just", "very", "really"}
    words = text.split()
    if len(words) > 20: # Only filter for longer texts
        words = [w for w in words if w.lower() not in fillers]
        text = " ".join(words)

    return text
