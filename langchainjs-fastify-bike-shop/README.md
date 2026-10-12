<div align="center">

# Bike Shop Chat with LangChain.js and Fastify

**`langchainjs-fastify-bike-shop`**

*A repair-shop chat widget whose visitors show up in Opik as readable conversations, not as separate API calls.*

</div>

---

The chat widget on a small business website is often the first place a team puts an LLM in front of real people, and it is where observability breaks first. Each message a visitor types is one `POST /chat` request, so a three-question session about a flat tire shows up as three unconnected requests, and when someone says "the bot told me $83 and now says something else" you need the whole session, not request two of three. This example is the Fastify backend for the chat widget of Spoke & Sprocket Cycle Works, a fictional bike repair shop in Pebble Ford. It is built with LangChain.js and traced with `opik-langchain`, and it is the Fastify variant of an Express chat-widget example.

## What you'll build

A Fastify server with a schema-validated `POST /chat` route, a `GET /health` route, and a small chat page served from the same process by `@fastify/static`. Each request runs one LangChain.js chain that takes the visitor's message as a plain string and returns the reply as a plain string. Inside, the first step loads that visitor's history and splices it into a prompt built from `data/shop.md` (hours, prices, policies), so the bot can add a flat fix and a tune-up into a total. Tracing is a single `OpikCallbackHandler` from `opik-langchain`, created once per session with `threadId` set to the widget's `sessionId`. That is the whole trick: every turn of a visitor's session lands in the same Opik thread. Keeping the chain string in, string out is deliberate, because the root run then holds just the visitor's sentence and the bot's sentence, which is what the Threads view shows.

`npm run demo` starts the server, plays three scripted visitor sessions over real HTTP (two with three turns, one with a single turn from a "new tab"), flushes, and stops the server.

```
widget sends { message, sessionId }
  Fastify validates the body
  chain.invoke(message, { callbacks: [handler with threadId = sessionId] })
    load-session-history -> ChatPromptTemplate -> gpt-4o-mini -> StrOutputParser
  one trace per turn, one thread per visitor
```

## See it in Opik

Open the `langchainjs-fastify-bike-shop` project in Opik.

**Threads tab.** Three threads: `visitor-flat-and-tuneup` and `visitor-ebike-brakes` (three turns each, 6 messages) and `visitor-new-tab` (one turn, 2 messages). Open `visitor-flat-and-tuneup` and it reads like a transcript. It starts with "Hi! My rear tire went flat on the way to work. How much to fix it?" and ends with the bot declining a Sunday drop-off: "I'm sorry, but we're closed on Sundays. You can drop off your bike any time from Tuesday to Saturday, 9:00 to 18:00." The middle turn is where the bot adds the $18 flat fix and the $65 tune-up into $83. In `visitor-ebike-brakes` the bot says it cannot repair motors or batteries and totals the $45 diagnostics plus the $40 brake bleed as $85.

**The new-tab thread.** `visitor-new-tab` is the same visitor opening a second tab: a fresh `sessionId`, so a fresh thread and no memory. Their question, "So the total is still $83 like you told me earlier, right?", gets an answer that starts "I'm not sure what services you are referring to" and then reconstructs the $83 anyway from the price list. The bot never saw the earlier conversation, and the Threads tab makes that visible: two separate threads where the visitor thought there was one.

**Traces tab.** Seven traces, all named `shop-chat-turn`. Expand one and you see five spans: `shop-chat-turn` (the chain), `load-session-history`, `ChatPromptTemplate`, `ChatOpenAI` and `StrOutputParser`. `ChatOpenAI` is the only span of type `llm`; the rest are `general`. It carries model `gpt-4o-mini`, provider `openai`, token usage and an estimated cost. In the verified run the first conversation's turns used 489, 562 and 623 tokens (about $0.000099, $0.000105 and $0.000111), the second used 475, 545 and 612, and prompt tokens climb every turn because the whole history is re-sent. The whole run cost about $0.0007.

**What "string in, string out" looks like.** The root trace holds exactly one sentence on each side. Through the SDK the trace input is `{'input': {'value': "Hi! My rear tire went flat on the way to work. How much to fix it?"}}` and the output is `{'output': {'value': "Hi there! ..."}}`. That is how `opik-langchain` stores a bare string, so the trace's `input` is a one-key object rather than a raw string. The thread's first and last messages are those same single sentences, with no prompt template, history array or message objects around them. `thread_id` is set on every trace. If the chain took `{ message, history }` instead, the thread would show that whole structure as its transcript.

## Run it yourself

1. Install dependencies (Node 20+): `npm install`. The `.npmrc` sets `legacy-peer-deps=true` because `opik-langchain@2.2.96` still declares a peer range of `opik@^1.8.75`, which excludes `opik@2.x`.
2. Copy the env file and fill it in: `cp .env.example .env`. Opik Cloud needs `OPIK_API_KEY`, `OPIK_WORKSPACE` and `OPIK_URL_OVERRIDE`; the OpenAI key goes in `OPENAI_API_KEY`. The server loads `.env` itself; exporting the variables in your shell also works. Set `OPIK_PROJECT_NAME=langchainjs-fastify-bike-shop` if your Opik config names a different default project (the code also sets the project explicitly).
3. Run the demo: `npm run demo`. It takes about 11 seconds and costs well under a cent.
4. Open the `langchainjs-fastify-bike-shop` project in Opik and check the Threads tab.

To use the widget yourself, run `npm run dev` and open [http://localhost:4200](http://localhost:4200). Each browser tab gets its own `sessionId` and therefore its own thread.

## Poke around

- Run `npm run dev`, chat in one tab, then open the page in a second tab and continue the topic. The second tab has no memory, and Opik shows two threads for what felt like one conversation.
- Ask something the shop facts do not cover ("do you sell child seats?") and open the trace: does the bot send you to the workshop team, as instructed, or improvise?
- Watch the `ChatOpenAI` token count climb turn by turn within a session. That line is the cost model for long conversations.
- Change `gpt-4o-mini` in `src/server.ts` to `gpt-4.1-mini` or `gpt-4o` and compare per-turn cost in the trace list.
- Remove `threadId: sessionId` from the handler and rerun: the same seven traces appear, but the Threads tab is empty.

## How it's put together

- `src/server.ts`: the Fastify app, the LangChain chain, per-session memory, one `OpikCallbackHandler` per session, `POST /chat`, `GET /health`, and static serving of the widget.
- `src/demo.ts`: starts the server, plays the scripted sessions over HTTP, flushes the traces, closes the server.
- `data/shop.md`: the fictional shop's hours, prices and policies, loaded into the system prompt.
- `public/index.html`: the chat widget, one `sessionId` per browser tab.
- `.env.example`, `.npmrc`, `.gitignore`, `package.json`, `tsconfig.json`: configuration (`opik` and `opik-langchain` are pinned to 2.2.96).
