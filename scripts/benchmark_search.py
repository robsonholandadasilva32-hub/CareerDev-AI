import time
import re
import random
import string

def generate_large_text(lines=50000, keywords=None):
    print(f"Generating text with {lines} lines...")
    content = []
    chars = string.ascii_letters + string.digits + " " + "\n"
    for _ in range(lines):
        line_len = random.randint(20, 100)
        line = "".join(random.choices(chars, k=line_len))
        if keywords and random.random() < 0.3:
            kw = random.choice(keywords)
            line += f" {kw} "
        content.append(line)
    return "\n".join(content)

def current_text_implementation(raw_text, keywords):
    content = raw_text.lower()
    found = []
    for kw in keywords:
        if kw in content:
            found.append(kw)
    return found

def optimized_bytes_implementation(raw_bytes, keywords_bytes):
    # Operating on bytes directly
    content = raw_bytes.lower()
    found = []
    for kw in keywords_bytes:
        if kw in content:
            found.append(kw)
    return found

def benchmark():
    keywords = [
        "react", "action", "reaction", "net", "dotnet", "network",
        "c", "c++", "java", "javascript", "script", "typescript",
        "type", "py", "python", "on", "rails", "rubyonrails",
        "ruby", "rust", "go", "google", "cloud", "aws", "amazon",
        "azure", "micro", "soft", "microsoft", "fast", "fastapi",
        "flask", "django", "ango", "star", "lette", "starlette",
        "vue", "express", "next", "nestjs", "angular", "tailwindcss",
        "spring", "hibernate", "jakarta", "junit", "kotlin",
        "tokio", "serde", "actix", "axum", "rocket", "diesel"
    ]

    # Text Setup
    raw_text = generate_large_text(lines=50000, keywords=keywords)
    keywords_lower = [k.lower() for k in keywords]

    # Bytes Setup
    raw_bytes = raw_text.encode('utf-8')
    keywords_bytes = [k.encode('utf-8') for k in keywords_lower]

    print(f"Data size: {len(raw_bytes)/1024/1024:.2f} MB")

    iterations = 50

    # Measure Text
    start = time.time()
    for _ in range(iterations):
        # In real app, we start with response.text which implies decoding happened.
        # But wait, httpx response.text performs decoding on access.
        # response.content is the raw bytes.
        # So avoiding .text access avoids decoding.
        # Here raw_text is already decoded.
        # To simulate correctly: we should start with bytes, decode it (Text Impl), vs use bytes (Bytes Impl).

        # Simulating Text Impl: Decode bytes -> lower -> search
        decoded = raw_bytes.decode('utf-8')
        res_curr = current_text_implementation(decoded, keywords_lower)
    end = time.time()
    text_time = end - start
    print(f"Text Implementation (Decode+Lower+Search): {text_time:.4f}s")

    # Measure Bytes
    start = time.time()
    for _ in range(iterations):
        res_bytes = optimized_bytes_implementation(raw_bytes, keywords_bytes)
    end = time.time()
    bytes_time = end - start
    print(f"Bytes Implementation (Lower+Search): {bytes_time:.4f}s")

    if bytes_time < text_time:
        print(f"🚀 Speedup: {text_time / bytes_time:.2f}x")
    else:
        print(f"⚠️ Slowdown: {text_time / bytes_time:.2f}x")

    # Verify correctness
    decoded = raw_bytes.decode('utf-8')
    res_text = set(current_text_implementation(decoded, keywords_lower))

    res_bytes_list = optimized_bytes_implementation(raw_bytes, keywords_bytes)
    res_bytes_decoded = set(b.decode('utf-8') for b in res_bytes_list)

    if res_text == res_bytes_decoded:
         print("✅ Results Match!")
    else:
         print("❌ Mismatch!")

if __name__ == "__main__":
    benchmark()
