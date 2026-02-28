import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  arena_experiments: defineTable({
    name: v.string(),
    status: v.union(v.literal("pending"), v.literal("running"), v.literal("completed"), v.literal("failed"), v.literal("stopped")),
    config: v.any(),
    dateRange: v.object({ initDate: v.string(), endDate: v.string() }),
    teams: v.array(v.string()),
    startedAt: v.optional(v.number()),
    completedAt: v.optional(v.number()),
    totalTokenCost: v.optional(v.number()),
  }).index("by_status", ["status"]),

  arena_teams: defineTable({
    experimentId: v.id("arena_experiments"),
    team: v.string(),
    model: v.string(),
    status: v.union(v.literal("alive"), v.literal("dead"), v.literal("crashed")),
    equity: v.number(),
    returnPct: v.number(),
    drawdownPct: v.number(),
    tokenCost: v.number(),
    llmCalls: v.number(),
    survivalTier: v.string(),
    deathReason: v.optional(v.string()),
  }).index("by_experiment", ["experimentId"]),

  arena_equity: defineTable({
    experimentId: v.id("arena_experiments"),
    team: v.string(),
    timestamp: v.string(),
    equity: v.number(),
    cash: v.number(),
    drawdownPct: v.number(),
    tokenCost: v.number(),
    survivalTier: v.string(),
  }).index("by_experiment_team", ["experimentId", "team"]),

  arena_trades: defineTable({
    experimentId: v.id("arena_experiments"),
    team: v.string(),
    date: v.string(),
    action: v.string(),
    symbol: v.string(),
    amount: v.number(),
    cashAfter: v.optional(v.number()),
  }).index("by_experiment_team", ["experimentId", "team"]),
});
