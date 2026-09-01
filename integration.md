# Frontend Architecture & Dashboard Refactoring Plan

## Sidebar Navigation Structure
- **MAIN**: 'Dashboard', 'My chatbots', 'All Documents'
- **BOT CONFIGURATION**: (Replaces 'Workspace' and removes 'Bots' from below it)
  - 'Knowledge base'
  - 'Deployment'
  - 'Reporting'
- **ACCOUNT**: 'Billing', 'Settings', 'Help and Support', 'Logout'

## Architecture Refactoring
Please refactor the frontend architecture to align with a scalable multi-tenant SaaS design while keeping the current product scope.
### Requirements

* We will support **one workspace per login** for now (not configurable), but **`workspaceId` must remain part of the routing and API calls** because it is required for backend authorization, tenant isolation, and future scalability.
* Do **not** flatten the routes. Use URL-based routing with both `workspaceId` and `chatbotId` as the source of truth.

### Routing

Refactor the dashboard to follow this structure:

```text
dashboard/
└── [workspaceId]/
    ├── layout.tsx
    ├── page.tsx
    ├── settings/
    ├── billing/
    └── bots/
        ├── page.tsx
        ├── new/
        └── [botId]/
            ├── layout.tsx
            ├── page.tsx
            ├── knowledge/
            ├── deployment/
            └── analytics/
```

### Layouts

* `dashboard/[workspaceId]/layout.tsx` should load and provide:

  * Current workspace
  * User permissions
  * Sidebar
  * Workspace context

* `dashboard/[workspaceId]/bots/[botId]/layout.tsx` should load and provide:

  * Current chatbot
  * Chatbot context
  * Shared bot navigation/tabs
  * Deployment/knowledge metadata if required

### Global Context

Implement a global **Current Chatbot Context**.

* The selected chatbot should be available throughout the app.
* The top navigation should include a chatbot selector.
* When the chatbot changes, navigate to the equivalent route for the selected bot (e.g. `/playground`, `/knowledge`, `/deployment`, etc.), updating only `chatbotId` while preserving the current page.
* The URL remains the source of truth, and the global context should be derived from the route.

### Component Organization

Keep the `app` directory focused on routing only.

Move feature logic into reusable components, for example:

```text
components/
    features/
        bots/
            knowledge/
            deployment/
            analytics/
```

Route `page.tsx` files should remain thin wrappers around feature components.

### API Compatibility

Ensure frontend routing aligns with backend endpoints such as:

* `/workspaces/:workspaceId`
* `/workspaces/:workspaceId/bots`
* `/workspaces/:workspaceId/bots/:botId`
* `/workspaces/:workspaceId/bots/:botId/knowledge`
* `/workspaces/:workspaceId/bots/:botId/deploy`

### Goal

Create an architecture that:

* Preserves tenant isolation using `workspaceId`.
* Uses `chatbotId` in the URL for bookmarkable and shareable pages.
* Keeps components modular.
* Supports future expansion (multiple workspaces, members, billing, audit logs, etc.) without major restructuring.

### Bot Management (`/dashboard/bots`)
Instead of [AI, Test, Studio]:
* **Configure**: Directs to bot studio
* **Test**: Directs to playground (test/preview tab in bot studio)
 *Chatbot Cards*: Clicking on any chatbot card on the 'My Chatbots' page updates the global current chatbot context and navigates to that bot.
#### Bot Settings (`/dashboard/[workspaceId]/bots/[botId]/settings`)
(All these will be dynamically loaded based on chatbot ID)
1. Instead of Intelligence -> **AI Engine** [Add field to accept custom API key from model provider]
   * Remove preview widget for this tab
   * Needs to have fields: System Prompt, LLM Provider (OpenAI, Groq), Select Model, API Key
2. **Appearance tab** needs to have: Input field for Welcome Message, Bot avatar emoji, Live Preview (shows the changes being made to the appearance of the chat widget as they are being made), "Save Appearance" button.
3. **Preview/Test tab** will be replaced with contents of playground page (`/dashboard/playground`). Remove AI intelligence, Tone and FEEDBACK from this page. Then remove playground page from the sidebar.
4. Clicking **'Save and Publish'** button on top-right of bot studio will direct to deployment page (`/dashboard/[workspaceId]/bots/[botId]/deployment`) of that particular chatbot.

### All Documents (`/dashboard/[workspaceId]/all-documents`)
1. Rename from `/dashboard/knowledge` to `/dashboard/all-documents`. 
2. Remove 'upload' widget. This page will show all documents uploaded by the user irrespective of the chatbot under the **'Your AI Knowledge'** table. Users can:
   * See every uploaded document
   * Search documents
   * Filter by chatbot
   * See upload date
   * Delete documents
   * See which chatbot(s) use a document
   *(Think of it as the workspace's document library.)*
3. Remove: Connect source button, AI Knowledge: Healthy card, sources card, confidence card, synced card, sections card, ✨ AI Extraction Insights, AI Learning Activity Timeline, Teach AI, Connected Sources.

### Chatbot Knowledge Management (`/dashboard/[workspaceId]/bots/[botId]/knowledge`)
*(This comes under 'BOT CONFIGURATION')*

1. This is where the following exists: Connect source button, 'AI Knowledge: Healthy' card, sources card, confidence card, synced card, sections card, Teach AI, Connected Sources, and the 'Your AI Knowledge' table with information about documents of that particular chatbot.
2. This page answers: *"How do I manage the knowledge for this chatbot?"*
   Users can:
   * Select a chatbot
   * Upload new documents
   * See only that chatbot's documents
   * Delete documents from that chatbot
   * Re-sync/re-index
   *(This is a chatbot management page.)*

 