import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { ChatCompletionTool } from "openai/resources/chat/completions";

const factsPath = fileURLToPath(new URL("../data/hotel.md", import.meta.url));

export const SYSTEM_PROMPT = `You are the concierge of the Driftwood Pier Hotel in Tern Harbor.
Be warm, brief and concrete (two or three sentences). Quote prices in EUR.
Only use the hotel facts below. For restaurant tables always call the
check_restaurant_table tool instead of guessing. If something is not covered
by the facts, say so plainly and offer to ask the front desk team.

HOTEL FACTS
${readFileSync(factsPath, "utf8")}`;

// Fictional table inventory for the Pilot House: date -> time -> free tables.
const TABLES: Record<string, Record<string, number>> = {
  "2026-07-17": { "19:00": 0, "19:30": 2, "20:30": 4 },
  "2026-07-18": { "19:00": 3, "20:00": 5 },
};

export const TOOLS: ChatCompletionTool[] = [
  {
    type: "function",
    function: {
      name: "check_restaurant_table",
      description: "Look up free tables at the Pilot House restaurant for a date.",
      parameters: {
        type: "object",
        properties: {
          date: { type: "string", description: "ISO date, e.g. 2026-07-17" },
          party_size: { type: "integer", description: "Number of guests" },
        },
        required: ["date", "party_size"],
      },
    },
  },
];

export function checkRestaurantTable(args: { date: string; party_size: number }) {
  const slots = TABLES[args.date];
  if (!slots) return { date: args.date, available_times: [], note: "No data for that date." };
  const available_times = Object.entries(slots)
    .filter(([, free]) => free > 0 && args.party_size <= 6)
    .map(([time, free]) => ({ time, free_tables: free }));
  return { date: args.date, party_size: args.party_size, available_times };
}
