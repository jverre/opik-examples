import "dotenv/config";

// Opik project every trace lands in. Set before the SDK reads its config.
export const PROJECT_NAME = "ollama-langchainjs-homebrew-rag";
process.env.OPIK_PROJECT_NAME = PROJECT_NAME;

// Nothing in this example talks to a hosted model. Drop any provider keys
// that happen to be in the shell so a stray client could not use them.
for (const key of ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]) {
  delete process.env[key];
}

export const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11535";
export const CHAT_MODEL = "llama3.2:1b"; // ~1.3 GB, small enough for CPU
export const EMBED_MODEL = "nomic-embed-text"; // ~274 MB
