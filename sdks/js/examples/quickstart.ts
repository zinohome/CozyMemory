import { CozyMemory } from "@cozymemory/sdk";

async function main() {
  const client = new CozyMemory({
    apiKey: "cozy_live_<your-key>",
    baseUrl: "http://localhost:8000",
  });

  await client.conversations.add("alice", [
    { role: "user", content: "I love hiking" },
    { role: "assistant", content: "Got it." },
  ]);

  const ctx = await client.context.getUnified("alice", "outdoor activity");
  console.log("Context:", ctx);
}

main().catch(console.error);
