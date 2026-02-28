import { query, mutation, action } from "./_generated/server";
import { v } from "convex/values";

// ── Queries ────────────────────────────────────────────

export const getExperiments = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("arena_experiments").order("desc").take(20);
  },
});

export const getExperiment = query({
  args: { id: v.id("arena_experiments") },
  handler: async (ctx, { id }) => {
    return await ctx.db.get(id);
  },
});

export const getLeaderboard = query({
  args: { experimentId: v.id("arena_experiments") },
  handler: async (ctx, { experimentId }) => {
    const teams = await ctx.db
      .query("arena_teams")
      .withIndex("by_experiment", (q) => q.eq("experimentId", experimentId))
      .collect();
    return teams.sort((a, b) => b.equity - a.equity);
  },
});

export const getEquityCurves = query({
  args: { experimentId: v.id("arena_experiments"), team: v.optional(v.string()) },
  handler: async (ctx, { experimentId, team }) => {
    let q = ctx.db
      .query("arena_equity")
      .withIndex("by_experiment_team", (qb) => {
        const base = qb.eq("experimentId", experimentId);
        return team ? base.eq("team", team) : base;
      });
    return await q.collect();
  },
});

export const getTrades = query({
  args: { experimentId: v.id("arena_experiments"), team: v.optional(v.string()) },
  handler: async (ctx, { experimentId, team }) => {
    let q = ctx.db
      .query("arena_trades")
      .withIndex("by_experiment_team", (qb) => {
        const base = qb.eq("experimentId", experimentId);
        return team ? base.eq("team", team) : base;
      });
    return await q.collect();
  },
});

export const getActiveExperiment = query({
  args: {},
  handler: async (ctx) => {
    const running = await ctx.db
      .query("arena_experiments")
      .withIndex("by_status", (q) => q.eq("status", "running"))
      .first();
    if (running) return running;
    // Fall back to latest completed
    return await ctx.db.query("arena_experiments").order("desc").first();
  },
});

// ── Mutations (called by VPS arena runner) ─────────────

export const createExperiment = mutation({
  args: {
    name: v.string(),
    config: v.any(),
    dateRange: v.object({ initDate: v.string(), endDate: v.string() }),
    teams: v.array(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("arena_experiments", {
      ...args,
      status: "pending",
    });
  },
});

export const updateExperimentStatus = mutation({
  args: {
    id: v.id("arena_experiments"),
    status: v.union(v.literal("pending"), v.literal("running"), v.literal("completed"), v.literal("failed"), v.literal("stopped")),
    startedAt: v.optional(v.number()),
    completedAt: v.optional(v.number()),
    totalTokenCost: v.optional(v.number()),
  },
  handler: async (ctx, { id, ...patch }) => {
    await ctx.db.patch(id, patch);
  },
});

export const upsertTeamResult = mutation({
  args: {
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
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("arena_teams")
      .withIndex("by_experiment", (q) => q.eq("experimentId", args.experimentId))
      .filter((q) => q.eq(q.field("team"), args.team))
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, args);
    } else {
      await ctx.db.insert("arena_teams", args);
    }
  },
});

export const addEquitySnapshot = mutation({
  args: {
    experimentId: v.id("arena_experiments"),
    team: v.string(),
    timestamp: v.string(),
    equity: v.number(),
    cash: v.number(),
    drawdownPct: v.number(),
    tokenCost: v.number(),
    survivalTier: v.string(),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("arena_equity", args);
  },
});

export const addTrade = mutation({
  args: {
    experimentId: v.id("arena_experiments"),
    team: v.string(),
    date: v.string(),
    action: v.string(),
    symbol: v.string(),
    amount: v.number(),
    cashAfter: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("arena_trades", args);
  },
});

export const bulkAddEquity = mutation({
  args: {
    snapshots: v.array(v.object({
      experimentId: v.id("arena_experiments"),
      team: v.string(),
      timestamp: v.string(),
      equity: v.number(),
      cash: v.number(),
      drawdownPct: v.number(),
      tokenCost: v.number(),
      survivalTier: v.string(),
    })),
  },
  handler: async (ctx, { snapshots }) => {
    for (const s of snapshots) {
      await ctx.db.insert("arena_equity", s);
    }
  },
});

export const bulkAddTrades = mutation({
  args: {
    trades: v.array(v.object({
      experimentId: v.id("arena_experiments"),
      team: v.string(),
      date: v.string(),
      action: v.string(),
      symbol: v.string(),
      amount: v.number(),
      cashAfter: v.optional(v.number()),
    })),
  },
  handler: async (ctx, { trades }) => {
    for (const t of trades) {
      await ctx.db.insert("arena_trades", t);
    }
  },
});

// ── Control mutations (called from web UI) ─────────────

export const requestStart = mutation({
  args: {
    name: v.string(),
    dateRange: v.object({ initDate: v.string(), endDate: v.string() }),
    teams: v.array(v.object({
      name: v.string(),
      model: v.string(),
      signature: v.string(),
      tokenPricing: v.object({ inputPer1m: v.number(), outputPer1m: v.number() }),
    })),
    initialCash: v.number(),
    tradingIntervalMinutes: v.number(),
    maxDrawdownPct: v.number(),
  },
  handler: async (ctx, args) => {
    // Check no other experiment is running
    const running = await ctx.db
      .query("arena_experiments")
      .withIndex("by_status", (q) => q.eq("status", "running"))
      .first();
    if (running) throw new Error("An experiment is already running");

    const pending = await ctx.db
      .query("arena_experiments")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .first();
    if (pending) throw new Error("An experiment is already pending");

    return await ctx.db.insert("arena_experiments", {
      name: args.name,
      status: "pending",
      config: {
        teams: args.teams,
        initialCash: args.initialCash,
        tradingIntervalMinutes: args.tradingIntervalMinutes,
        maxDrawdownPct: args.maxDrawdownPct,
      },
      dateRange: args.dateRange,
      teams: args.teams.map(t => t.signature),
    });
  },
});

export const requestStop = mutation({
  args: { id: v.id("arena_experiments") },
  handler: async (ctx, { id }) => {
    const exp = await ctx.db.get(id);
    if (!exp) throw new Error("Experiment not found");
    if (exp.status !== "running" && exp.status !== "pending") {
      throw new Error("Experiment is not running or pending");
    }
    await ctx.db.patch(id, { status: "stopped" });
  },
});

// ── Poller query (VPS checks this) ─────────────────────

export const getPendingExperiment = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("arena_experiments")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .first();
  },
});
