/**
 * The single seam between the chat UI and whatever answers it. Today that is
 * `toolAgent.ts` (live backend tools, no LLM). When Member 5's `/agent/chat`
 * lands, call it here; the UI does not change. `USE_FIXTURES` keeps the offline
 * demo path on canned replies.
 */
import { USE_FIXTURES } from '../config';
import type { AgentChatRequest, AgentChatResponse } from './agentTypes';
import { mockAgentReply } from './mockAgent';
import { toolAgentReply } from './toolAgent';

export async function sendChatMessage(req: AgentChatRequest): Promise<AgentChatResponse> {
  return USE_FIXTURES ? mockAgentReply(req) : toolAgentReply(req);
}
