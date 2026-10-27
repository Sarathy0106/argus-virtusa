import { z } from "zod";

// zod validates every API response so bad/unexpected data fails loudly instead
// of silently rendering a wrong number (Part 4). Keep in sync with the gateway;
// Part 3 will replace hand-written schemas with openapi-typescript-generated ones.

export const MetaSchema = z.object({
  service: z.string(),
  version: z.string(),
  llm_mode: z.enum(["ollama", "deterministic_fallback", "replay_cache"]),
  chain_verified: z.boolean(),
  first_broken_index: z.number().int().nullable(),
  last_event_seq: z.number().int(),
  web_origin: z.string(),
  server_time: z.string(),
});

export type Meta = z.infer<typeof MetaSchema>;
