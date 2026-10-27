import { apiGet } from "./api";
import { MetaSchema, type Meta } from "./schemas";

export async function fetchMeta(): Promise<Meta> {
  const raw = await apiGet<unknown>("/api/v2/meta");
  // Validate loudly — if the gateway shape drifts, this throws rather than
  // rendering a stale/incorrect value.
  return MetaSchema.parse(raw);
}
