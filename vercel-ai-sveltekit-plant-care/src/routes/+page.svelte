<script lang="ts">
  import { Chat } from "@ai-sdk/svelte";
  import { DefaultChatTransport } from "ai";

  // One Chat instance is one conversation, and its id becomes the Opik thread.
  const chat = new Chat({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
  });
  let input = $state("");

  function send(event: SubmitEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    void chat.sendMessage({ text });
    input = "";
  }
</script>

<main>
  <h1>Ask Fern</h1>
  <p class="hint">Houseplant care from Fernwick Plant Co.</p>

  {#each chat.messages as message (message.id)}
    <div class="msg {message.role}">
      <strong>{message.role === "user" ? "You" : "Fern"}</strong>
      {#each message.parts as part}
        {#if part.type === "text"}<span>{part.text}</span>{/if}
      {/each}
    </div>
  {/each}

  <form onsubmit={send}>
    <input bind:value={input} placeholder="Why are my pothos leaves drooping?" />
    <button disabled={chat.status !== "ready"}>Send</button>
  </form>
</main>

<style>
  main { max-width: 36rem; margin: 2rem auto; font-family: system-ui, sans-serif; padding: 0 1rem; }
  .hint { color: #666; margin-top: -0.5rem; }
  .msg { margin: 0.75rem 0; white-space: pre-wrap; }
  .msg.user { color: #1d4ed8; }
  strong { display: block; font-size: 0.8rem; text-transform: uppercase; opacity: 0.6; }
  form { display: flex; gap: 0.5rem; margin-top: 1.5rem; }
  input { flex: 1; padding: 0.5rem; }
</style>
