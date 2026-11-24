/**
 * The single seam between the chat UI and the backend.
 *
 * ★ The UI only ever calls `sendChatMessage`. While `USE_MOCK_AGENT` is true
 *   it answers from `mockAgent.ts`; when Member 3's `agentApi.ts` lands
 *   (`POST /api/v1/agent/chat`), swap the one marked line — no component
 *   changes. Member 3 owns the real HTTP client, not this file.
 */
import type { AgentChatRequest, AgentChatResponse } from './agentTypes';
import { mockAgentReply } from './mockAgent';

export const USE_MOCK_AGENT = true;

export async function sendChatMessage(req: AgentChatRequest): Promise<AgentChatResponse> {
  if (USE_MOCK_AGENT) return mockAgentReply(req);
  // TODO(member-3): return agentApi.sendChatMessage(req);
  throw new Error('agentApi not wired');
}
