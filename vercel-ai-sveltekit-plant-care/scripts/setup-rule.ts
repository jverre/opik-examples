// Creates (or replaces) the live online-evaluation rule on this example's
// Opik project. Once it exists, Opik scores every new trace server-side with
// an LLM judge and attaches the result as a feedback score. Run it once:
//   npm run setup-rule
import { Opik } from "opik";
import { config } from "dotenv";
import { PROJECT_NAME } from "../src/lib/project.ts";

config({ quiet: true });

export const RULE_NAME = `${PROJECT_NAME}-faithfulness`;
export const SCORE_NAME = "care_sheet_faithfulness";

const client = new Opik({ projectName: PROJECT_NAME });

// The rule is attached to a project id, and the project only exists after its
// first trace, so create it up front if needed.
let project;
try {
  project = await client.api.projects.retrieveProject({ name: PROJECT_NAME });
} catch {
  await client.api.projects.createProject({ name: PROJECT_NAME });
  project = await client.api.projects.retrieveProject({ name: PROJECT_NAME });
}
const projectId = project.id!;

// Idempotent: delete every rule on this project with exactly this name before
// creating it, so running the script twice still leaves exactly one rule.
const existing = await client.api.automationRuleEvaluators.findEvaluators({
  projectId,
  size: 100,
});
const ids = (existing.content ?? [])
  .filter((r) => r.name === RULE_NAME)
  .map((r) => r.id!);
if (ids.length > 0) {
  await client.api.automationRuleEvaluators.deleteAutomationRuleEvaluatorBatch({
    projectId,
    body: { ids },
  });
}

await client.api.automationRuleEvaluators.createAutomationRuleEvaluator({
  type: "llm_as_judge",
  name: RULE_NAME,
  projectIds: [projectId],
  samplingRate: 1.0, // score every trace; lower this in production
  enabled: true,
  action: "evaluator",
  code: {
    model: { name: "gpt-4o-mini", temperature: 0 },
    messages: [
      {
        role: "SYSTEM",
        content:
          "You grade replies from a houseplant shop assistant. The input is the " +
          "full conversation, starting with a system prompt that contains the " +
          "only care sheets the assistant may use. Score 1 if the final reply " +
          "sticks to what the care sheets say, or honestly says it has no care " +
          "sheet for the plant. Score 0 if the reply states care advice for a " +
          "plant that has no sheet, or contradicts a sheet.",
      },
      {
        role: "USER",
        content: "Conversation:\n{{input}}\n\nFinal reply:\n{{output}}",
      },
    ],
    variables: { input: "input", output: "output" },
    schema: [
      {
        name: SCORE_NAME,
        type: "BOOLEAN",
        description:
          "true if the reply is supported by the care sheets or admits there is no sheet, false if it invents advice",
      },
    ],
  },
});

await client.flush();
console.log(`Created rule "${RULE_NAME}" on project "${PROJECT_NAME}" (sampling 1.0, judge gpt-4o-mini).`);
console.log(`It will attach a "${SCORE_NAME}" feedback score to every new trace.`);
