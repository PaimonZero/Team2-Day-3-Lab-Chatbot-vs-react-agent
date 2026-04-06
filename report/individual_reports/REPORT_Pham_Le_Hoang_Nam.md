# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Pham Le Hoang Nam
- **Student ID**: 2A202600416
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

_Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.)._

- **Modules Implemented**: UI/UX Interface
- **Code Highlights**:
  Built an interactive user interface (UI) for the system, allowing users to interact and directly compare the Chatbot Baseline model with the ReAct Agent. Handled chat history state management and parsed data to visually display the Agent's reasoning steps (Thought/Action/Observation) instead of just outputting raw text.
- **Documentation**: The UI flow receives user input, calls the ReAct Agent or Baseline module directly, and then formats the LLM's analysis blocks into collapsible/expandable UI components, making it easier for users to evaluate the reasoning capabilities of the Agent vs the Chatbot.

---

## II. Debugging Case Study (10 Points)

_Analyze a specific failure event you encountered during the lab using the logging system._

- **Problem Description**: The interface experienced unresponsiveness (freeze) or failed to show status messages when the ReAct Agent entered a prolonged reasoning loop, leading users to mistakenly believe the system had crashed.
- **Log Source**: Console/UI Logs during the execution of a complex tool chain.
- **Diagnosis**: The Agent's processing loop (Action -> Observation -> Thought) takes significantly more time compared to the instant response of the Chatbot. Without a temporary status feedback mechanism, the UI could not render anything until the Final Answer was ready.
- **Solution**: Integrated UI components to dynamic display real-time statuses (e.g., "Calling weather tool...", "Analyzing risks..."). Implemented a mechanism to parse streams/logs in real-time to continuously update the UI for each step of the ReAct loop, resulting in a significant UX improvement.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

_Reflect on the reasoning capability difference._

1.  **Reasoning**: From a UI/UX perspective, the ReAct Agent provides much higher transparency than a standard Chatbot. Despite slower response times, visually presenting the "Thought process" helps build user trust in the final output.
2.  **Reliability**: The Agent can sometimes deliver a worse UX than the Chatbot when it "overthinks"—excessively analyzing a simple question that a Chatbot could answer immediately, or getting stuck in a tool loop without producing a final answer.
3.  **Observation**: Clearly displaying the actual collected data (Observations) via the interface helps users empathize more with the bot (e.g., when an API returns empty, the user knows it's an API failure rather than the bot being incapable).

---

## IV. Future Improvements (5 Points)

_How would you scale this for a production-level AI agent system?_

- **Scalability**: Upgrade the UI-backend connection to WebSockets to manage a more stable, bidirectional data stream, especially when handling a large number of concurrent users.
- **Safety**: Add an "Interrupt/Cancel" button directly to the interface so users can proactively halt token generations or resource-intensive loops when the Agent makes incorrect actions.
- **Performance**: Completely decouple the UI processing (Frontend) from the Agent logic (Backend) via REST/FastAPI. Apply a Collapsible UI for ReAct reasoning blocks to keep the main chat space clean and responsive.
