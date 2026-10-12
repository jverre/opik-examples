import { Agent } from "@mastra/core/agent";
import { openai } from "@ai-sdk/openai";
import { LIBRARY_NAME } from "./library.ts";
import { searchCatalog, renewLoan, placeHold } from "./tools.ts";

export const loansAgent = new Agent({
  id: "loans-agent",
  name: "alder-creek-loans-agent",
  instructions:
    `You are the loans assistant for ${LIBRARY_NAME}. Members tell you their member id. ` +
    "Ground every answer in tool results; never guess availability, due dates or queue positions. " +
    "Use search_catalog to find books and their book_id. Use renew_loan to renew a loan. " +
    "Use place_hold only when the member asks to be put on a waiting list, and look up the " +
    "book_id with search_catalog first. Never place a hold for a book with copies on the shelf. " +
    "Never tell a member a renewal is impossible until renew_loan has said so: always call the tool " +
    "and relay its reason in plain words. Do not offer anything the tools cannot do. " +
    "Be warm and concise: 2-4 sentences, no bullet lists.",
  model: openai("gpt-4o-mini"),
  tools: { searchCatalog, renewLoan, placeHold },
});
