# run this once to clean null bytes
with open("energy_agent.py", "rb") as f:
    content = f.read()

cleaned = content.replace(b"\x00", b"")

with open("energy_agent_cleaned.py", "wb") as f:
    f.write(cleaned)

print("✅ Cleaned null bytes. Use 'energy_agent_cleaned.py' now.")