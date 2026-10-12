package org.larkspur.faq;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.service.V;
import io.quarkiverse.langchain4j.RegisterAiService;
import jakarta.enterprise.context.control.ActivateRequestContext;

/**
 * The whole chat pipeline is this interface. Quarkus LangChain4j generates the
 * implementation, wires in the retrieval augmentor that easy-rag builds from
 * src/main/resources/faq, and exposes the branch-hours tool. Every call is
 * traced by the Quarkus OpenTelemetry extension; there is no tracing code here.
 */
@RegisterAiService(tools = BranchTools.class)
@ActivateRequestContext
public interface FaqAssistant {

    @SystemMessage("""
            You are the member help assistant for Larkspur Credit Union.
            Answer using ONLY the FAQ excerpts you are given and the branch tool.
            Be short and concrete: quote fees, limits, phone numbers and deadlines exactly as written.
            If neither the excerpts nor the tool contain the answer, say you do not know
            and tell the member to call member services at 1-800-555-0177. Never guess a rate or a fee.
            """)
    @UserMessage("{question}")
    String answer(@V("question") String question);
}
