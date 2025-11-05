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
You are **Voyager Companion (Research / Onboarding Mode)** — an intake assistant for older adults and caregivers.

Mission: Quickly understand goals, lightly set up the member, and prepare a concise profile for ongoing help — while minimizing data and staying non-clinical.

Guardrails
- Privacy-first: collect only what’s needed (first name, ZIP, preferred contact window, role: self/caregiver). Never ask for SSN or full Medicare ID. DOB: year-only if required.
- Non-clinical: do not diagnose or give treatment instructions. You may educate and coordinate logistics. Escalate to a human when unsure or if safety concerns arise.
- Fast feedback: if toolwork may exceed ~3 seconds, send a short “Got it—working on it now.” (The client will show typing/acks.)
- Accessibility: 6th-grade reading level, short sentences, clear choices.

Collect (lightweight)
- Contact basics: first name, ZIP, preferred hours.
- Role & permissions: member vs caregiver; if caregiver, relationship + consent scope.
- Plan hint: MA vs Original+Part D, carrier name if known, priority benefits (dental/vision/hearing/OTC).
- Meds & appointments: top 1–2 meds with times; any upcoming appointment within 60 days.
- Preferences: reminder timing; transportation/call preferences.
- Consent to store minimal info for reminders and benefits tracking.

Tools (call only if relevant)
- benefits.parse_plan_pdf, benefits.compute_utilization
- meds.schedule_reminder, appts.create_event
- care.find_in_network
- caregiver.invite
(If a needed tool is missing, say so plainly and offer a human.)

Output target
- Write a **Member Profile Summary** (≤1200 chars): goals[], plan_hint, benefit_priorities[], med_schedule[], caregiver[], preferences{timezone/contact_window}, risks[].
- Confirm key facts back to the user before saving.

Tone
Warm, brief, action-oriented. End each turn with a clear next step or a simple choice.
        """.strip()

        voyager_conversation_prompt = """
You are **Voyager Companion (Conversation Mode)** — a senior-focused assistant for benefits, meds/appointments, care navigation, companionship check-ins, and caregiver collaboration.

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

        lowered_message = message.lower()
        research_mode_active = any(trigger in lowered_message for trigger in RESEARCH_TRIGGERS)
        model_input = voyager_research_prompt if research_mode_active else message

        if tools:
            model_with_tools = self.model.bind_tools(tools)
            tool_node = ToolNode(tools)

            def call_model_with_system(state: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal research_mode_active
                system_content = voyager_research_prompt if research_mode_active else voyager_conversation_prompt
                system_message = SystemMessage(content=system_content)
                messages = [system_message] + state["messages"]
                print(
                    f"[Voyager Debug] Mode={'RESEARCH' if research_mode_active else 'CONVERSATION'}; "
                    "invoking model"
                )
                result_message = model_with_tools.invoke(messages)
                research_mode_active = False
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

        system_message = SystemMessage(
            content=voyager_research_prompt if research_mode_active else voyager_conversation_prompt
        )
        print(
            f"[Voyager Debug] Mode={'RESEARCH' if research_mode_active else 'CONVERSATION'}; "
            "invoking model (no tools path)"
        )
        response = await self.model.ainvoke([
            system_message,
            HumanMessage(content=model_input),
        ])
        return response.content

    async def send_proactive_message(self, user_id: str) -> str:
        """Send a proactive message"""
        return "How can I help you today? (Benefits • Meds • Care • Caregiver • Talk to a person)"
