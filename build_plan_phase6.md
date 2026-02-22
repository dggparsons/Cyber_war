# Phase 6 Build Plan – Conference Day Checklist

## Objectives
- Deploy the full stack to the target environment (Azure App Service or local war-room machine).
- Verify registrations/login, Socket.IO, and GM dashboard before the audience joins.
- Run the live game smoothly, capture results, and deliver the AI reveal.

## Pre-Event Setup
1. **Deployment**
   - Push backend container/build to Azure App Service (configure env vars, `/home/site/data` path, GM credentials).
   - Deploy frontend bundle (static site or App Service slot) and confirm HTTPS.
   - Seed database with production nation stats, advisors, baseline scores.
2. **Smoke Tests**
   - Register/login with test accounts, ensure team assignment works and duplicates are blocked.
   - Validate Socket.IO connectivity from multiple devices/network segments.
   - Confirm GM dashboard reflects real-time data and nuclear lock toggle functions.
3. **Content Prep**
   - Load crisis events, AI reveal assets, award badges, and any scripted GM commentary.
   - Print/hand out nation brief cards if using physical props.

## Live Run Checklist
1. **T-15 min**
   - Open registration portal, have assistants help attendees sign up, ensure they know their team name.
   - Share Teams/meeting link with leaderboard screen (GM dashboard on projector).
2. **Briefing (7 min)**
   - Walk through rules, show UI, remind about “everyone loses if nukes fire.”
3. **Rounds (32 min total)**
   - Start each round via GM panel; monitor chats and diplomacy channels for issues.
   - Inject crisis at scheduled time; watch escalation/diplomacy responses.
   - Keep an eye on nuclear lock status; be ready to pause if needed.
4. **Reveal (4-6 min)**
   - Freeze final Outcome Dashboard, present awards, then show AI comparison slides.
   - Highlight fairness metrics and AI escalation quotes.
5. **Post-Game**
   - Export logs, save leaderboard screenshots, gather quick attendee feedback.
   - Reset database (truncate user actions, keep AI results) for next run if needed.

## Contingencies
- Have paper backup of nation actions if Wi-Fi dies; GM can drive via admin panel manually.
- Keep a spare laptop logged into GM dashboard in case the main machine glitches.
- Prepare a “degraded mode” reveal slide deck in case the live app fails at the end.
