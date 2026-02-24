"""
budget_guard/main.py — BudgetGuard companion service.

Reads OpenClaw gateway logs → parses token usage → tracks cost in
PostgreSQL → writes /shared/budget_status.json (read by OpenClaw agents
via the budget-check skill) → sends Telegram alerts at 70/90/100%.

Runs as a separate Docker container alongside openclaw-gateway.
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("budget_guard")

KST = ZoneInfo("Asia/Seoul")

# ============================================================
# Configuration (all from environment variables)
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CEO_TELEGRAM_ID = int(os.environ["CEO_TELEGRAM_ID"])
DAILY_BUDGET_USD = float(os.environ.get("DAILY_BUDGET_USD", "15.0"))
MONTHLY_BUDGET_USD = float(os.environ.get("MONTHLY_BUDGET_USD", "450.0"))
KRW_EXCHANGE_RATE = float(os.environ.get("KRW_EXCHANGE_RATE", "1350.0"))

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "agentdb")
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

# Model pricing (USD per 1M tokens) — update when Gemini pricing changes
FLASH_MODEL = os.environ.get("LLM_FLASH_MODEL", "gemini-3.0-flash-001")
PRO_MODEL = os.environ.get("LLM_PRO_MODEL", "gemini-3.1-pro-001")
FLASH_INPUT_COST = float(os.environ.get("LLM_FLASH_INPUT_COST_PER_1M", "0.075"))
FLASH_OUTPUT_COST = float(os.environ.get("LLM_FLASH_OUTPUT_COST_PER_1M", "0.300"))
PRO_INPUT_COST = float(os.environ.get("LLM_PRO_INPUT_COST_PER_1M", "3.50"))
PRO_OUTPUT_COST = float(os.environ.get("LLM_PRO_OUTPUT_COST_PER_1M", "10.50"))

# Shared volume paths
LOG_FILE = Path(os.environ.get("OPENCLAW_LOG_FILE", "/shared/logs/openclaw.log"))
STATUS_FILE = Path(os.environ.get("BUDGET_STATUS_FILE", "/shared/budget_status.json"))
LOG_POSITION_FILE = Path("/shared/logs/.budget_guard_pos")

STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============================================================
# Database
# ============================================================
pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        dsn = (
            f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )
        for attempt in range(1, 6):
            try:
                pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
                logger.info("DB connection pool established.")
                return pool
            except Exception as e:
                logger.warning(f"DB connect attempt {attempt}/5 failed: {e}. Retry in 5s...")
                await asyncio.sleep(5)
        raise RuntimeError("Cannot connect to PostgreSQL after 5 attempts.")
    return pool


async def get_daily_cost() -> float:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM api_usage_log "
            "WHERE date_kst = (NOW() AT TIME ZONE 'Asia/Seoul')::DATE"
        )
    return float(row["total"])


async def get_monthly_cost() -> float:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM api_usage_log "
            "WHERE DATE_TRUNC('month', called_at AT TIME ZONE 'Asia/Seoul') "
            "= DATE_TRUNC('month', NOW() AT TIME ZONE 'Asia/Seoul')"
        )
    return float(row["total"])


async def log_usage(agent: str, model: str, in_tok: int, out_tok: int) -> None:
    cost = _calc_cost(model, in_tok, out_tok)
    krw = cost * KRW_EXCHANGE_RATE
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_usage_log "
            "(agent_name, model_name, input_tokens, output_tokens, cost_usd, cost_krw) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            agent, model, in_tok, out_tok, cost, krw,
        )


async def has_alert_been_sent(alert_type: str) -> bool:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM budget_alerts_log WHERE alert_type=$1 "
            "AND date_kst=(NOW() AT TIME ZONE 'Asia/Seoul')::DATE",
            alert_type,
        )
    return row is not None


async def record_alert(alert_type: str) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "INSERT INTO budget_alerts_log (alert_type) VALUES ($1) "
            "ON CONFLICT (alert_type, date_kst) DO NOTHING",
            alert_type,
        )


# ============================================================
# Cost calculation
# ============================================================

def _calc_cost(model: str, in_tok: int, out_tok: int) -> float:
    if "flash" in model.lower():
        return (in_tok * FLASH_INPUT_COST + out_tok * FLASH_OUTPUT_COST) / 1_000_000
    return (in_tok * PRO_INPUT_COST + out_tok * PRO_OUTPUT_COST) / 1_000_000


# ============================================================
# Log parsing — reads OpenClaw gateway log for token usage
# ============================================================

# Pattern for JSON log lines with token usage data
# OpenClaw logs JSON lines including usage metadata.
_TOKEN_PATTERN = re.compile(
    r'"inputTokens"\s*:\s*(\d+).*?"outputTokens"\s*:\s*(\d+).*?"model"\s*:\s*"([^"]+)".*?"agentId"\s*:\s*"([^"]+)"',
    re.DOTALL,
)


def _get_log_position() -> int:
    if LOG_POSITION_FILE.exists():
        try:
            return int(LOG_POSITION_FILE.read_text().strip())
        except Exception:
            pass
    return 0


def _save_log_position(pos: int) -> None:
    LOG_POSITION_FILE.write_text(str(pos))


async def parse_new_log_entries() -> None:
    """Read new log lines since last position and record token usage."""
    if not LOG_FILE.exists():
        return

    pos = _get_log_position()
    file_size = LOG_FILE.stat().st_size

    # Handle log rotation (file shrunk)
    if pos > file_size:
        pos = 0

    if pos == file_size:
        return  # nothing new

    try:
        with open(LOG_FILE, "r", errors="replace") as f:
            f.seek(pos)
            new_content = f.read()
            new_pos = f.tell()
    except Exception as e:
        logger.warning(f"Log read error: {e}")
        return

    # Each line is a JSON log entry
    for line in new_content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Look for usage data in log entries
        usage = entry.get("usage") or entry.get("tokenUsage") or {}
        if not usage:
            continue

        in_tok = int(usage.get("inputTokens") or usage.get("input_tokens") or 0)
        out_tok = int(usage.get("outputTokens") or usage.get("output_tokens") or 0)
        model = str(entry.get("model") or entry.get("modelId") or "unknown")
        agent = str(entry.get("agentId") or entry.get("agent") or "unknown")

        if in_tok > 0 or out_tok > 0:
            await log_usage(agent, model, in_tok, out_tok)
            logger.info(
                f"Logged usage: agent={agent} model={model} "
                f"in={in_tok} out={out_tok} cost=${_calc_cost(model, in_tok, out_tok):.6f}"
            )

    _save_log_position(new_pos)


# ============================================================
# Status file — read by OpenClaw agents via budget-check skill
# ============================================================

async def update_status_file() -> dict:
    daily = await get_daily_cost()
    monthly = await get_monthly_cost()
    daily_ratio = daily / DAILY_BUDGET_USD
    monthly_ratio = monthly / MONTHLY_BUDGET_USD

    if daily_ratio >= 1.0 or monthly_ratio >= 1.0:
        status = "suspended"
    elif daily_ratio >= 0.90:
        status = "minimal"
    elif daily_ratio >= 0.70:
        status = "flash_only"
    else:
        status = "normal"

    data = {
        "status": status,
        "daily_used_usd": round(daily, 4),
        "daily_limit_usd": DAILY_BUDGET_USD,
        "daily_ratio": round(daily_ratio, 4),
        "monthly_used_usd": round(monthly, 4),
        "monthly_limit_usd": MONTHLY_BUDGET_USD,
        "monthly_ratio": round(monthly_ratio, 4),
        "remaining_usd": round(max(0.0, DAILY_BUDGET_USD - daily), 4),
        "updated_at": datetime.now(KST).isoformat(),
    }
    STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


# ============================================================
# Telegram alerts
# ============================================================

async def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json={
            "chat_id": CEO_TELEGRAM_ID,
            "text": text,
            "parse_mode": "Markdown",
        })
        if resp.status_code != 200:
            logger.error(f"Telegram send failed: {resp.status_code} {resp.text}")


async def check_and_send_alerts(status: dict) -> None:
    daily = status["daily_used_usd"]
    monthly = status["monthly_used_usd"]
    remaining = status["remaining_usd"]
    ratio = status["daily_ratio"]

    if monthly >= MONTHLY_BUDGET_USD:
        if not await has_alert_been_sent("monthly_100"):
            await record_alert("monthly_100")
            await send_telegram(
                f"🔴 *월 API 한도 도달*\n\n"
                f"이번 달 사용: *${monthly:.4f}* / ${MONTHLY_BUDGET_USD:.2f}\n"
                f"(₩{monthly * KRW_EXCHANGE_RATE:,.0f})\n\n"
                f"다음 달 1일까지 에이전트가 *완전 중단*됩니다."
            )

    elif ratio >= 1.0:
        if not await has_alert_been_sent("daily_100"):
            await record_alert("daily_100")
            await send_telegram(
                f"🔴 *일 API 한도 도달*\n\n"
                f"오늘 사용: *${daily:.4f}* / ${DAILY_BUDGET_USD:.2f}\n"
                f"(₩{daily * KRW_EXCHANGE_RATE:,.0f})\n\n"
                f"내일 자정(KST)에 자동으로 재개됩니다.\n"
                f"에이전트가 *일시 중단*되었습니다."
            )

    elif ratio >= 0.90:
        if not await has_alert_been_sent("daily_90"):
            await record_alert("daily_90")
            await send_telegram(
                f"🟠 *일 예산 경고 (90%)*\n\n"
                f"오늘 사용: *${daily:.2f}* / ${DAILY_BUDGET_USD:.2f}\n"
                f"남은 예산: *${remaining:.2f}* (₩{remaining * KRW_EXCHANGE_RATE:,.0f})\n\n"
                f"⚡ 최소 응답 모드로 자동 전환됩니다."
            )

    elif ratio >= 0.70:
        if not await has_alert_been_sent("daily_70"):
            await record_alert("daily_70")
            await send_telegram(
                f"🟡 *일 예산 주의 (70%)*\n\n"
                f"오늘 사용: *${daily:.2f}* / ${DAILY_BUDGET_USD:.2f}\n"
                f"남은 예산: *${remaining:.2f}* (₩{remaining * KRW_EXCHANGE_RATE:,.0f})\n\n"
                f"Flash 전용 모드로 전환됩니다."
            )


# ============================================================
# Main loop
# ============================================================

async def main() -> None:
    logger.info("BudgetGuard starting...")
    logger.info(f"Daily limit: ${DAILY_BUDGET_USD} | Monthly limit: ${MONTHLY_BUDGET_USD}")
    logger.info(f"Flash model: {FLASH_MODEL} | Pro model: {PRO_MODEL}")

    # Wait for DB
    await get_pool()

    while True:
        try:
            await parse_new_log_entries()
            status = await update_status_file()
            await check_and_send_alerts(status)
            logger.debug(
                f"Status: {status['status']} | "
                f"Daily: ${status['daily_used_usd']:.4f}/{DAILY_BUDGET_USD} | "
                f"Monthly: ${status['monthly_used_usd']:.4f}/{MONTHLY_BUDGET_USD}"
            )
        except Exception as e:
            logger.error(f"BudgetGuard loop error: {e}", exc_info=True)

        await asyncio.sleep(60)  # Check every 60 seconds


if __name__ == "__main__":
    asyncio.run(main())
