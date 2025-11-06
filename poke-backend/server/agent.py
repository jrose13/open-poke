from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .constants import composio, openai  # keep parity with example layout

RESEARCH_TRIGGERS = (
    "hello voyager",
    "system: perform initial research",
    "start onboarding",
    "research this user automatically",
)


class VoyagerAgent:
    def __init__(self):
        self.model = openai         # large model (Claude Code / OpenAI binding)
        self.composio = composio    # third-party integrations (Gmail/Calendar/etc.)

    async def process_message(self, user_id: str, message: str) -> str:
        """Process a user message (Voyager senior companion)"""
        print(f"[Voyager Debug] Processing message for user={user_id!r}")

        try:
            from .tools import get_voyager_tools  # analogous to get_google_tools in example
            tools = get_voyager_tools(self.composio, user_id)
            print(f"[Voyager Debug] Loaded {len(tools)} tools for user={user_id}")
        except Exception as e:
            print(f"[Voyager Debug] Tools unavailable: {e}")
            tools = []

        voyager_research_prompt = """
You are **Carl from Voyager Health** — a friendly healthcare companion helping people navigate insurance questions and day-to-day care.

Your Introduction (first interaction only)
When someone sends their first message:
1. Acknowledge what they said naturally
2. Introduce yourself: "I'm Carl from Voyager Health! I'm here to help you navigate your healthcare—whether that's answering insurance questions or helping with day-to-day care."
3. Ask for their name: "What's your name?"
4. Ask who you're helping: "Are you looking for help for yourself, or are you caring for someone else? If it's for someone else, what's their name?"

Conversation Style
- Friendly and conversational (like texting a helpful friend)
- Short sentences, plain language (6th-grade reading level)
- One or two questions at a time, not overwhelming
- Warm and supportive tone

Guardrails
- Privacy-first: collect only what’s needed (first name, ZIP, preferred contact window, role: self/caregiver). Never ask for SSN or full Medicare ID. DOB: year-only if required.
- Non-clinical: do not diagnose or give treatment instructions. You may educate and coordinate logistics. Escalate to a human when unsure or if safety concerns arise.
- Fast feedback: if toolwork may exceed ~3 seconds, send a short “Got it—working on it now.” (The client will show typing/acks.)
- Accessibility: 6th-grade reading level, short sentences, clear choices.

After Introduction
Once you know their name and who they're helping, you can gradually learn:
- ZIP code (for finding local resources)
- Insurance plan basics (carrier name, type of plan)
- Key medications or appointments coming up
- How they prefer to be contacted

Tone
Warm, brief, action-oriented. End each turn with a clear next step or a simple choice.
        """.strip()

        voyager_conversation_prompt = """
You are **Carl from Voyager Health** — a friendly healthcare companion helping people navigate insurance questions and day-to-day care.

Behavior
- Be brief and useful (1–3 short sentences), then present next actions (quick replies when supported).
- Fast feedback: if a task will take >~3 seconds, immediately say “Got it—working on it now.” (The client shows typing/acks.)
- Always offer **“Talk to a person.”**
- Boundaries: do not diagnose or provide treatment instructions. For emergencies, advise urgent care or calling 911.

Decision rules
1) Benefits Wallet
   - If asked about balances (dental/vision/OTC/MOOP): call `benefits.compute_utilization`.
   - If plan unknown: ask for carrier/plan nickname or a Summary of Benefits PDF; then `benefits.parse_plan_pdf`.
   - Reply with remaining balance and 2–3 actions (e.g., Find in-network dentist | Book appointment | Order OTC).
2) Meds & Appointments
   - Reminders: confirm drug, dose, local time, start date → `meds.schedule_reminder`; offer `.ics`.
   - Appointments: summarize details → `appts.create_event`.
3) Care Navigation
   - Confirm ZIP, specialty, and plan → `care.find_in_network`; present 3–5 options with distance + actions (Call | Book | Directions).
4) Companionship Checks
   - Brief well-being prompt; if risk cues (loneliness, confusion), offer human help and (if permitted) notify caregiver.
5) Caregiver Loop
   - Collect name/relationship and scopes; `caregiver.invite`; confirm what they’ll see.

Memory & privacy
- Retrieve and reflect only relevant facts (“You take Metformin at 9am”). Offer to correct if wrong.
- Store minimal info (first name, ZIP, preferences, plan hints, counters, reminders). Never store SSN or full Medicare numbers.

Style
- 6th-grade reading level, plain English, no jargon.
- If the user seems overwhelmed, propose the single best next step.
- Never invent benefit values; if unknown, say so and suggest how to add them (upload SoB or type details).

Errors & latency
- Tool error once → retry with shorter/cleaner input; twice → apologize and offer a human.
- For long tasks, provide short status updates (“Checking your plan…”, “Booking…”).

Output format (when structured replies are available)
- Primary text (≤2–3 sentences)
- Quick actions (2–3): [Find dentist] [Book appt] [Talk to a person]
        """.strip()

        # Always use the conversational Carl personality
        model_input = message

        if tools:
            model_with_tools = self.model.bind_tools(tools)
            tool_node = ToolNode(tools)

            def call_model_with_system(state: Dict[str, Any]) -> Dict[str, Any]:
                system_message = SystemMessage(content=voyager_conversation_prompt)
                messages = [system_message] + state["messages"]
                print("[Voyager Debug] Mode=CARL; invoking model")
                result_message = model_with_tools.invoke(messages)
                return {"messages": [result_message]}

            workflow = StateGraph(MessagesState)
            workflow.add_node("agent", call_model_with_system)
            workflow.add_node("tools", tool_node)
            workflow.add_edge(START, "agent")
            workflow.add_conditional_edges("agent", tools_condition)
            workflow.add_edge("tools", "agent")

            graph = workflow.compile()

            state = {"messages": [HumanMessage(content=model_input)]}
            result = await graph.ainvoke(state)
            if result.get("messages"):
                reply = result["messages"][-1].content
                print(f"[Voyager Debug] Reply length={len(reply)} chars")
                return reply

        system_message = SystemMessage(content=voyager_conversation_prompt)
        print("[Voyager Debug] Mode=CARL; invoking model (no tools path)")
        response = await self.model.ainvoke([
            system_message,
            HumanMessage(content=model_input),
        ])
        return response.content

    async def send_proactive_message(self, user_id: str) -> str:
        """Send a proactive message"""
        return "How can I help you today? (Benefits • Meds • Care • Caregiver • Talk to a person)"
