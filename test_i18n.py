from app.i18n.loader import get_texts
import time

# Call get_texts for the first time
start_time = time.time()
texts_pt1 = get_texts("pt")
end_time = time.time()
first_call_time = end_time - start_time
print(f"First call for 'pt' took: {first_call_time:.6f} seconds")

# Call get_texts for the second time, should be cached
start_time = time.time()
texts_pt2 = get_texts("pt")
end_time = time.time()
second_call_time = end_time - start_time
print(f"Second call for 'pt' (cached) took: {second_call_time:.6f} seconds")

# Verify that the returned objects are the same
if id(texts_pt1) == id(texts_pt2):
    print("Caching works: The same object was returned.")
else:
    print("Caching failed: Different objects were returned.")

# Verify that the content is the same
if texts_pt1 == texts_pt2:
    print("Content is consistent between calls.")
else:
    print("Content is inconsistent between calls.")

# Test fallback to Portuguese
start_time = time.time()
texts_non_existent = get_texts("non_existent_lang")
end_time = time.time()
fallback_call_time = end_time - start_time
print(f"Call for non-existent language took: {fallback_call_time:.6f} seconds")

if texts_non_existent == texts_pt1:
    print("Fallback to Portuguese works correctly.")
else:
    print("Fallback to Portuguese failed.")
