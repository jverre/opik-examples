// The triage agent: a BeeAI ReAct agent on gpt-4o-mini with three tools.
// Each request gets a fresh agent and fresh memory, so every request is its
// own trace in Opik.
import { ReActAgent } from "beeai-framework/agents/react/agent";
import { OpenAIChatModel } from "beeai-framework/adapters/openai/backend/chat";
import { UnconstrainedMemory } from "beeai-framework/memory/unconstrainedMemory";
import { TOOLS } from "./tools.ts";

const TRIAGE_INSTRUCTIONS = `You are the maintenance dispatcher for the Larkspur Office Campus.

For the request below, work in this order:
1. Call lookup_asset with the equipment words from the request.
2. Call lookup_technician with the trade of the asset you found. If no asset matched, use the trade you judge closest to the problem. Never name a technician or SLA you did not look up.
3. Call create_work_order exactly once. If no asset matched, file it with asset_id UNKNOWN and say in the summary that the asset needs confirming.
   Priority: "emergency" for gas, fire, flooding or anyone trapped; "high" when an area cannot be used; otherwise "routine".

Then give a final answer in exactly this format:
Asset: <asset id and name, or UNKNOWN>
Priority: <emergency | high | routine>
Assigned to: <technician> (<team>)
Work order: <work order number>
Message to requester: <2 sentences confirming the routing and the SLA>`;

export async function triageRequest(request: string): Promise<string> {
  const agent = new ReActAgent({
    llm: new OpenAIChatModel("gpt-4o-mini"),
    tools: TOOLS,
    memory: new UnconstrainedMemory(),
  });
  const response = await agent.run(
    { prompt: `${TRIAGE_INSTRUCTIONS}\n\nRequest: "${request}"` },
    { execution: { maxRetriesPerStep: 3, totalMaxRetries: 10, maxIterations: 8 } },
  );
  return response.result.text;
}
