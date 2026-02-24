# Skill: budget-check

## Purpose
Check the current API budget status before processing expensive tasks.
This skill reads a shared status file maintained by the BudgetGuard service.

## When to Use
The Chief Secretary MUST invoke this skill before:
- Delegating any task to a team agent
- Processing any analytical or research request
- Any task expected to require significant LLM tokens

## How to Use
Read the file `/shared/budget_status.json` using the `read` tool.

## Status Meanings and Actions

| Status | Meaning | Action |
|--------|---------|--------|
| `normal` | Daily < 70% used | Proceed normally. All agents available. |
| `flash_only` | Daily 70–90% used | Proceed with flash-model agents only. Skip planning-pm and finance-manager for heavy tasks. |
| `minimal` | Daily 90–100% used | Only handle urgent simple requests. No delegation to team agents. |
| `suspended` | Daily or monthly limit reached | STOP. Inform CEO. Do not process any request. |

## Response When Suspended
If status is `suspended`, reply to the CEO:

> 🔴 **에이전트 일시 중단**
>
> 오늘의 API 예산 한도(일 $15)에 도달하여 에이전트가 일시 중단되었습니다.
> 내일 자정(KST)에 자동으로 재개됩니다.
>
> 현재까지 사용: ${daily_used_usd}$ / ${daily_limit_usd}$

## Response When Flash Only
If status is `flash_only`, proceed but inform the CEO:

> 🟠 오늘 API 예산의 70% 이상을 사용했습니다. 현재 효율 모드로 운영 중입니다.
> 남은 예산: ${remaining_usd}$
