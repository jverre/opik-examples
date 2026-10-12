// The three tools the triage agent can call. All data is fictional and read
// from data/*.json; work orders live in memory, so nothing but the LLM call
// leaves your machine.
import { readFileSync } from "node:fs";
import { DynamicTool, JSONToolOutput } from "beeai-framework/tools/base";
import { z } from "zod";

type Asset = {
  asset_id: string;
  name: string;
  aliases: string[];
  building: string;
  location: string;
  trade: string;
  warranty: string;
  notes: string;
};
type Technician = {
  name: string;
  team: string;
  pager: string;
  on_call_hours: string;
  response_sla: string;
};

const readJson = <T>(file: string): T =>
  JSON.parse(readFileSync(new URL(`../data/${file}`, import.meta.url), "utf8")) as T;

const ASSETS = readJson<Asset[]>("assets.json");
const TECHNICIANS = readJson<Record<string, Technician>>("technicians.json");

export const TRADES = Object.keys(TECHNICIANS) as [string, ...string[]];
export const PRIORITIES = ["emergency", "high", "routine"] as [string, ...string[]];

/** lookup_asset: turn the words in a request into a registered campus asset. */
export const lookupAssetTool = new DynamicTool({
  name: "lookup_asset",
  description:
    "Search the campus asset register by the words used in a maintenance request " +
    "(for example 'roof unit' or 'kitchen sink'). Returns the asset id, building, " +
    "location, trade, warranty status and notes, or found=false with the list of known assets.",
  inputSchema: z.object({
    query: z.string().describe("Short description of the equipment, as the requester worded it."),
  }),
  async handler(input) {
    const q = input.query.toLowerCase();
    const scored = ASSETS.map((asset) => {
      const terms = [asset.name, ...asset.aliases].map((t) => t.toLowerCase());
      const score = terms.filter((t) => q.includes(t) || t.includes(q)).length;
      return { asset, score };
    })
      .filter((s) => s.score > 0)
      .sort((a, b) => b.score - a.score);
    if (scored.length === 0) {
      return new JSONToolOutput({
        found: false,
        known_assets: ASSETS.map((a) => `${a.asset_id}: ${a.name}`),
      });
    }
    const { aliases: _aliases, ...asset } = scored[0].asset;
    return new JSONToolOutput({ found: true, ...asset });
  },
});

/** lookup_technician: who is on call for a trade right now. */
export const lookupTechnicianTool = new DynamicTool({
  name: "lookup_technician",
  description:
    "Find the on-call technician for a trade. " +
    `Valid trades: ${TRADES.join(", ")}. ` +
    "Returns name, team, pager handle, on-call hours and response SLA.",
  inputSchema: z.object({
    trade: z.enum(TRADES).describe("The trade that owns the asset, as returned by lookup_asset."),
  }),
  async handler(input) {
    return new JSONToolOutput({ trade: input.trade, ...TECHNICIANS[input.trade] });
  },
});

let nextWorkOrder = 4100;

/** create_work_order: file the work order. In-memory, so each run starts at WO-4101. */
export const createWorkOrderTool = new DynamicTool({
  name: "create_work_order",
  description:
    "File a work order once the asset and technician are known. " +
    "Returns the work order number and the status it was filed with.",
  inputSchema: z.object({
    asset_id: z.string().describe("Asset id from lookup_asset, or UNKNOWN if no asset matched."),
    assignee: z.string().describe("Technician or team name from lookup_technician."),
    priority: z.enum(PRIORITIES).describe("emergency, high, or routine."),
    summary: z.string().describe("One sentence describing the problem for the technician."),
  }),
  async handler(input) {
    nextWorkOrder += 1;
    return new JSONToolOutput({
      work_order: `WO-${nextWorkOrder}`,
      status: input.asset_id === "UNKNOWN" ? "needs_asset_confirmation" : "assigned",
      ...input,
    });
  },
});

export const TOOLS = [lookupAssetTool, lookupTechnicianTool, createWorkOrderTool];
