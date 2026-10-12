package org.larkspur.faq;

import dev.langchain4j.agent.tool.Tool;
import jakarta.enterprise.context.ApplicationScoped;

import java.util.Map;

/** A tiny tool so the trace also shows a tool call next to the retrieval-augmented completion. */
@ApplicationScoped
public class BranchTools {

    private static final Map<String, String> HOURS = Map.of(
            "downtown", "Downtown branch (212 Larch Street): Mon-Fri 9am-5pm, Sat 9am-1pm",
            "riverside", "Riverside branch (48 Quay Road): Mon-Fri 9am-6pm, closed weekends",
            "airport", "Airport kiosk (Terminal B): daily 6am-8pm, ATM and card services only");

    @Tool("Returns the opening hours of a Larkspur branch. The branch is one of: downtown, riverside, airport.")
    public String branchHours(String branch) {
        return HOURS.getOrDefault(branch.toLowerCase().trim(),
                "No branch called '" + branch + "'. Known branches: downtown, riverside, airport.");
    }
}
