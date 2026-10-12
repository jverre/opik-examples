import careSheets from "../../../data/care-sheets.json";

// The whole corpus is small enough to put straight into the system prompt.
const sheets = careSheets.sheets
  .map(
    (s) =>
      `## ${s.plant}\nLight: ${s.light}\nWater: ${s.water}\nNotes: ${s.notes}`,
  )
  .join("\n\n");

export const SYSTEM_PROMPT = `You are Fern, the plant-care assistant for ${careSheets.shop}, a fictional houseplant shop.
Answer in two or three sentences, using only the care sheets below.
If the customer asks about a plant that has no care sheet, say you don't have a sheet for it and suggest they ask a shop assistant. Do not guess.

${sheets}`;
