# ApexAurum Cloud — Commercial/Payment/Crypto Surface Removal Checklist

## Summary

This checklist maps every commercial, payment, crypto, tier-gating, and monetization surface in the backend for removal during localification. For each file: commercial imports, what to delete vs keep, cross-references, and suggested local-mode replacement behavior.

---

## 1. STRIPE BILLING

### `backend/app/models/billing.py`
- **Commercial entities:** Subscription, CreditBalance, CreditTransaction, WebhookEvent, Coupon, CouponRedemption
- **Stripe-specific columns:** `stripe_customer_id`, `stripe_subscription_id`, `stripe_price_id`, `payment_method`, `trial_end`, `cancel_at_period_end`, `current_period_start/end`
- **Delete:**
  - `WebhookEvent` model entirely (Stripe idempotency)
  - `CreditBalance` model entirely (cents-based pay-per-use credits)
  - `CreditTransaction` model entirely (cents audit log)
  - `Coupon` model entirely (promotional codes)
  - `CouponRedemption` model entirely
  - From `Subscription`: remove `stripe_customer_id`, `stripe_subscription_id`, `stripe_price_id`, `payment_method`, `trial_end`, `current_period_start`, `current_period_end`, `cancel_at_period_end`, `messages_used`, `messages_limit`
- **Keep:** A stripped-down `Subscription` model with only `user_id`, `tier` (default `"local"`), `status` (default `"active"`), and timestamps — or replace with a simple tier string on the User model.
- **Cross-references imported by:**
  - `app/models/__init__.py` (exports all)
  - `app/models/user.py` (relationships: subscription, credit_balance)
  - `app/services/billing.py`
  - `app/api/v1/billing.py`
  - `app/api/v1/webhooks.py`
  - `app/api/v1/admin.py`
  - `app/api/v1/user.py`
  - `app/api/v1/chat.py` (indirect via BillingService)
  - `app/api/v1/council.py` (indirect via BillingService)
  - `app/api/v1/agents.py` (indirect via BillingService)
  - `app/api/v1/dream.py` (indirect via BillingService)
  - `app/api/v1/music.py` (Subscription model inline import)
  - `app/api/v1/jam.py` (Subscription model inline import)
  - `app/api/v1/nursery.py` (Subscription model inline import)
  - `app/api/v1/memory_import.py` (indirect via BillingService)
  - `app/api/v1/pocket.py` (Subscription inline import)
  - `app/api/v1/athaverse.py` (Subscription inline import)
  - `app/tools/nursery.py` (Subscription inline import)
  - `app/services/cloud_trainer.py` (Subscription inline import)
- **Suggested replacement:** Keep a minimal `Subscription` row per user with `tier="local"`, `status="active"`, no limits. All gating functions should bypass checks and return `True` / unlimited.

### `backend/app/services/billing.py`
- **Commercial imports:** `stripe` (external), `app.config.TIER_LIMITS`, `TIER_HIERARCHY`, `CREDIT_PACKS`, `app.models.billing.*`, `app.services.pricing.calculate_cost_cents`, `app.services.apexjoule.ledger/constants` (AJ renewal)
- **Delete:**
  - `_create_stripe_customer()`
  - `create_subscription_checkout()`
  - `create_credits_checkout()`
  - `create_pack_checkout()`
  - `create_portal_session()`
  - `add_credits()`
  - `deduct_credits()`
  - `record_message_usage()` (cents-based credit deduction path)
  - `is_webhook_processed()` / `mark_webhook_processed()`
  - `reset_subscription_usage()` (subscription counter reset)
  - `_ensure_valid_stripe_customer()`
  - AJ auto-renewal block inside `can_send_message()` (lines ~317-350)
- **Keep:**
  - `get_or_create_subscription()` — simplify to create a local-tier subscription with no Stripe customer creation.
  - `get_subscription_status()` — simplify to return unlimited/local tier response.
  - `can_send_message()` — replace with `return (True, "local")`
  - `can_use_model()` — replace with `return True`
  - `can_use_tools()` — replace with `return True`
  - `can_use_multi_provider()` — replace with `return True`
- **Cross-references:** Imported by `api/v1/billing.py`, `api/v1/chat.py`, `api/v1/council.py`, `api/v1/agents.py`, `api/v1/dream.py`, `api/v1/memory_import.py`, `api/v1/pocket.py`, `api/v1/athaverse.py`, `api/v1/council_ws.py`, `worker.py`.
- **Suggested replacement:** Reduce `BillingService` to a stub that always returns unlimited access. Strip all Stripe logic.

### `backend/app/api/v1/billing.py`
- **Commercial imports:** `BillingService`, `CreditTransaction`, `Coupon`, `CouponRedemption`, `CreditBalance`, `UsageService`, `FeatureCreditService`, `TIER_LIMITS`, `TIER_HIERARCHY`, `CREDIT_PACKS`, `QUEST_TIER_MAP`, `schemas.billing.*`, `app.services.apexjoule.*` (AJ citizen, AJ tier subscription)
- **Delete routes:**
  - `POST /checkout/subscription` (Stripe checkout)
  - `POST /checkout/credits` (legacy credit purchase)
  - `POST /checkout/pack` (feature pack checkout)
  - `POST /portal` (Stripe customer portal)
  - `POST /activate-citizen` (AJ Citizen activation)
  - `POST /subscribe-with-aj` (AJ tier subscription)
  - `GET /transactions` (cents audit log)
  - `GET /usage` (usage dashboard with tier limits)
  - `GET /pricing` (public pricing display — or keep as empty/local)
  - `GET /coupon/{code}` (coupon check)
  - `POST /coupon/redeem` (coupon redeem)
  - `POST /admin/coupons` (admin coupon CRUD)
  - `GET /admin/coupons`
  - `DELETE /admin/coupons/{code}`
- **Keep:** `GET /status` — but rewrite to always return local/unlimited status with no Stripe data.
- **Cross-references:** Mounted in `api/v1/__init__.py` at prefix `/billing`. Referenced by frontend billing store/views.
- **Suggested replacement:** Replace the entire router with a minimal one containing only `GET /status` that returns a static "local unlimited" response.

### `backend/app/api/v1/webhooks.py`
- **Commercial imports:** `stripe` (external), `app.config.TIER_LIMITS`, `CREDIT_PACKS`, `QUEST_TIER_MAP`, `app.models.billing.Subscription`, `app.services.billing.BillingService`, `app.services.usage.FeatureCreditService`, `app.services.progression.ProgressionService`
- **Delete routes:**
  - `POST /stripe` (entire Stripe webhook handler)
  - `handle_checkout_completed()`
  - `handle_subscription_created()`
  - `handle_subscription_updated()`
  - `handle_subscription_deleted()`
  - `handle_invoice_paid()`
  - `handle_invoice_payment_failed()`
  - `_get_tier_from_price()`
  - `_is_quest_tier()`
- **Keep:** Nothing — this router is entirely for Stripe webhooks.
- **Cross-references:** Mounted in `api/v1/__init__.py` at prefix `/webhooks`.
- **Suggested replacement:** Delete the file and remove the router include.

### `backend/app/schemas/billing.py`
- **Commercial entities:** All schemas are monetization-specific.
- **Delete:**
  - `SubscriptionCheckoutRequest/Response`
  - `CreditsCheckoutRequest/Response`
  - `CreditBalanceResponse`
  - `CreditTransactionResponse`
  - `CreditTransactionsResponse`
  - `TierFeatures` (or simplify)
  - `BillingStatusResponse` (rewrite)
  - `PortalSessionRequest/Response`
  - `PricingTier`
  - `CreditPack`
  - `PricingResponse`
  - `CouponCreateRequest`
  - `CouponResponse`
  - `CouponListResponse`
  - `CouponRedeemRequest/Response`
  - `CouponCheckResponse`
  - `PackCheckoutRequest/Response`
  - `FeatureCreditPack`
  - `UsageSummaryResponse`
  - `UsageResourceDetail`
- **Keep:** A minimal `BillingStatusResponse` with `tier="local"`, unlimited flags, no credits/Stripe fields.
- **Cross-references:** Imported only by `api/v1/billing.py`.
- **Suggested replacement:** Replace with a minimal local-mode schema.

### `backend/alembic/versions/002_billing_tables.py`
- **Commercial entities:** Creates `subscriptions`, `credit_balances`, `credit_transactions`, `webhook_events`.
- **Delete:** Entire migration (or leave as-is since migrations are historical; do not run downgrade that drops `subscriptions` if you still need a minimal tier field). For a clean local install, skip this migration and create a new `002_local_schema.py` that only creates a stripped `subscriptions` table.
- **Cross-references:** Env imports all versions; Alembic runs sequentially.
- **Suggested replacement:** Create a replacement migration `002_local_tier.py` that creates a minimal `subscriptions` table (user_id, tier, status, timestamps) with no Stripe columns.

---

## 2. SOLANA CRYPTO

### `backend/app/api/v1/solana.py`
- **Commercial imports:** `app.services.solana.payment_service.SolanaPaymentService`, `app.config.get_settings`
- **Delete routes:**
  - `POST /create-payment`
  - `GET /check-payment/{reference}`
  - `GET /rates`
  - `GET /history`
- **Keep:** Nothing.
- **Cross-references:** Mounted in `api/v1/__init__.py` at prefix `/solana`.
- **Suggested replacement:** Delete file and remove router include.

### `backend/app/models/solana_payment.py`
- **Commercial entities:** `SolanaPayment` model (on-chain payment tracking)
- **Delete:** Entire model.
- **Cross-references:** Imported by `app/models/__init__.py` and `app/services/solana/payment_service.py`.
- **Suggested replacement:** Delete file. Remove from `models/__init__.py`.

### `backend/app/services/solana/client.py`
- **Commercial imports:** `httpx` (used for CoinGecko price fetch + Solana RPC)
- **Delete:** Entire file (Solana JSON-RPC client, transfer verification, price caching).
- **Cross-references:** Imported only by `app/services/solana/payment_service.py`.
- **Suggested replacement:** Delete directory `app/services/solana/`.

### `backend/app/services/solana/payment_service.py`
- **Commercial imports:** `app.models.solana_payment.SolanaPayment`, `app.services.solana.client.SolanaClient`, `app.services.apexjoule.constants.AJ_PER_USD`, `app.services.apexjoule.ledger.AJLedger`
- **Delete:** Entire file (payment lifecycle, on-chain polling, AJ credit on confirmation).
- **Cross-references:** Imported only by `app/api/v1/solana.py`.
- **Suggested replacement:** Delete file and directory.

---

## 3. APEXJOULE ECONOMY

### `backend/app/models/apexjoule.py`
- **Commercial entities:** `ApexJouleBalance`, `ApexJouleTransaction`, `LoveScore`
- **Delete:** Entire file. All three models are part of the virtual currency economy.
- **Cross-references:**
  - `app/models/__init__.py`
  - `app/models/user.py` (relationship `aj_balances`)
  - `app/services/apexjoule/ledger.py`
  - `app/services/apexjoule/calculator.py`
  - `app/services/apexjoule/shop.py`
  - `app/services/apexjoule/self_sustain.py`
  - `app/services/apexjoule/love_scorer.py`
  - `app/services/portability/exporter.py`
  - `app/services/portability/importer.py`
  - `app/services/multiverse.py`
  - `app/services/solana/payment_service.py` (AJ credit on crypto payment)
  - `app/services/progression.py` (quest bounty AJ credit)
- **Suggested replacement:** Delete file. Remove relationship from `models/user.py`.

### `backend/app/services/apexjoule/ledger.py`
- **Commercial imports:** `app.models.apexjoule.*`, `app.services.apexjoule.constants.*`
- **Delete:** Entire file (`AJLedger` — balance management, credit/debit, level-ups, love-depth updates, village broadcasts).
- **Cross-references:**
  - `app/api/v1/apexjoule.py`
  - `app/api/v1/chat.py` (AJ citizen debit inline import)
  - `app/api/v1/council.py` (inline import for council AJ credit)
  - `app/api/v1/billing.py` (AJ citizen activation, AJ tier subscription)
  - `app/api/v1/pocket.py` (imported at top)
  - `app/api/v1/marketplace.py` (inline import for purchase debit)
  - `app/services/apexjoule/shop.py`
  - `app/services/apexjoule/self_sustain.py`
  - `app/services/apexjoule/calculator.py`
  - `app/services/solana/payment_service.py`
  - `app/services/progression.py`
- **Suggested replacement:** Delete file and directory.

### `backend/app/services/apexjoule/calculator.py`
- **Commercial imports:** `app.services.pricing.calculate_cost`, `app.services.apexjoule.constants.*`, `app.services.apexjoule.love_scorer.*`, `app.services.apexjoule.ledger.AJLedger`
- **Delete:** Entire file (`compute_e_cost`, `compute_w`, `compute_kappa`, `compute_aj`, `compute_aj_for_chat`, `compute_aj_for_council_round`, `compute_aj_for_dream`).
- **Cross-references:**
  - `app/api/v1/chat.py` (inline imports for chat AJ credit)
  - `app/api/v1/council.py` (inline import for council AJ credit)
  - `app/worker.py` (inline imports for dream AJ credit)
- **Suggested replacement:** Delete file.

### `backend/app/services/apexjoule/constants.py`
- **Commercial entities:** `AJ_PER_USD`, `AJ_SHOP_PRICES`, `AJ_TIER_PRICES`, `AJ_CITIZEN_WELCOME_BONUS`, `AJ_CITIZEN_ACTION_COSTS`, `QUEST_BOUNTIES`, `LEVEL_THRESHOLDS`, `LEVEL_NAMES`, `LOVE_DEPTH_TIERS`, `TASK_MULTIPLIERS`, `EXPECTED_COSTS`, earning splits, safety caps.
- **Delete:** Entire file.
- **Cross-references:** Imported by nearly every other `apexjoule` module and by `api/v1/billing.py`, `api/v1/pocket.py`, `api/v1/athaverse.py`, `services/solana/payment_service.py`.
- **Suggested replacement:** Delete file.

### `backend/app/services/apexjoule/love_scorer.py`
- **Commercial entities:** `LoveScoreResult`, `compute_love_score`, `update_love_depth`, `love_depth_bonus`, `love_depth_tier_name`
- **Delete:** Entire file.
- **Cross-references:**
  - `app/services/apexjoule/calculator.py`
  - `app/api/v1/apexjoule.py` (import `love_depth_tier_name`)
  - `app/api/v1/pocket.py` (import `love_depth_tier_name`)
- **Suggested replacement:** Delete file.

### `backend/app/services/apexjoule/self_sustain.py`
- **Commercial entities:** `AJSelfSustain` — agent self-funding when quotas exhausted.
- **Delete:** Entire file.
- **Cross-references:**
  - `app/services/usage.py` (inline imports in `check_usage_limit` and `deduct_aj_if_self_sustained`)
- **Suggested replacement:** Delete file.

### `backend/app/services/apexjoule/shop.py`
- **Commercial entities:** `AJShop` — purchase features with AJ, tip agents.
- **Delete:** Entire file.
- **Cross-references:**
  - `app/api/v1/apexjoule.py` (imported at top)
  - `app/api/v1/pocket.py` (imported at top)
- **Suggested replacement:** Delete file.

### `backend/app/api/v1/apexjoule.py`
- **Commercial imports:** `AJLedger`, `AJShop`, `love_depth_tier_name`, `AJ_SHOP_PRICES`, `QUEST_BOUNTIES`, `LEVEL_THRESHOLDS`, `LEVEL_NAMES`, `LOVE_DEPTH_TIERS`
- **Delete routes:**
  - `GET /balance`
  - `GET /transactions`
  - `GET /stats`
  - `GET /shop`
  - `GET /leaderboard`
  - `POST /purchase`
  - `POST /tip`
  - `GET /settings`
  - `PATCH /settings`
- **Keep:** Nothing.
- **Cross-references:** Mounted in `api/v1/__init__.py` at prefix `/aj`.
- **Suggested replacement:** Delete file and remove router include.

---

## 4. TIER GATING / USAGE LIMITS

### `backend/app/config.py` (commercial sections)
- **Commercial entities:**
  - Stripe settings: `stripe_secret_key`, `stripe_publishable_key`, `stripe_webhook_secret`, `stripe_price_*` (14 price IDs)
  - `TIER_LIMITS` dict (lines 138-353)
  - `TIER_HIERARCHY` (line 371)
  - `QUEST_TIER_MAP` (lines 375-380)
  - `QUEST_TIER_PRICES` (lines 382-387)
  - `CREDIT_PACKS` (lines 390-424)
- **Delete:**
  - All Stripe settings fields (lines ~55-77)
  - `TIER_LIMITS` (or keep a single `"local"` tier with everything enabled)
  - `TIER_HIERARCHY` (or reduce to `{"local": 99}`)
  - `QUEST_TIER_MAP`
  - `QUEST_TIER_PRICES`
  - `CREDIT_PACKS`
- **Keep:**
  - `DREAM_ELIGIBLE_MODELS`
  - `GRANTABLE_PROVIDERS`
  - Non-commercial settings (DB, SMTP, JWT, etc.)
- **Cross-references:** `TIER_LIMITS` is imported by 20+ files across `api/v1/` and `services/`. `CREDIT_PACKS` imported by `services/usage.py`, `services/billing.py`, `api/v1/webhooks.py`, `api/v1/billing.py`.
- **Suggested replacement:** Replace `TIER_LIMITS` with a single `LOCAL_TIER` dict that has `messages_per_month=None`, `tools_enabled=True`, `multi_provider=True`, `byok_allowed=True`, `api_access=True`, `dev_mode=True`, `pac_mode=True`, `nursery_access=True`, unlimited everything.

### `backend/app/services/usage.py`
- **Commercial imports:** `app.models.usage.UsageCounter`, `app.models.feature_credit.FeatureCreditBalance`, `app.config.CREDIT_PACKS`, `app.models.billing.Subscription` (inline), `app.config.TIER_LIMITS` (inline), `app.services.apexjoule.self_sustain.AJSelfSustain` (inline)
- **Delete:**
  - `FeatureCreditService` class entirely (lines 430-652)
  - `check_usage_limit()` — or simplify to always return `(True, current, None)`
  - `deduct_feature_credit_if_over_limit()`
  - `deduct_aj_if_self_sustained()`
  - `_check_usage_thresholds()` (email warnings at 80%/100%)
- **Keep:**
  - `UsageService.increment_usage()` — keep for analytics/counters, but remove limit enforcement side effects.
  - `UsageService.get_current_count()` — keep for analytics.
  - `UsageService.get_usage_summary()` — keep for dashboard.
  - Counter constants (`COUNTER_MESSAGES_HAIKU`, etc.) — keep.
  - `classify_model_family()` — keep for analytics.
  - `get_current_period()` — keep.
- **Cross-references:**
  - `app/api/v1/billing.py` (UsageService, FeatureCreditService, get_current_period)
  - `app/api/v1/chat.py` (inline UsageService imports)
  - `app/api/v1/council.py` (inline UsageService imports)
  - `app/api/v1/music.py` (inline UsageService imports)
  - `app/api/v1/jam.py` (inline UsageService imports)
  - `app/api/v1/nursery.py` (inline UsageService import)
  - `app/api/v1/admin.py` (UsageService, FeatureCreditService, get_current_period)
  - `app/services/billing.py` (inline UsageService, FeatureCreditService imports)
- **Suggested replacement:** Strip all limit enforcement and credit deduction. Keep only atomic counter increment for analytics.

### `backend/app/services/pricing.py`
- **Commercial entities:** `PRICING` table, `calculate_cost()`, `calculate_cost_cents()`, `estimate_cost()`, `get_tier_for_model()`, `format_cost_display()`
- **Delete:**
  - `calculate_cost_cents()` (only used for credit deduction)
  - `estimate_cost()`
  - `get_tier_for_model()` (tier gating)
  - `format_cost_display()`
- **Keep:**
  - `PRICING` dict and `calculate_cost()` — useful for local cost awareness/logging if desired, or delete entirely if not needed.
- **Cross-references:**
  - `app/services/billing.py` (imports `calculate_cost_cents`, `get_tier_for_model`)
  - `app/services/apexjoule/calculator.py` (imports `calculate_cost`)
- **Suggested replacement:** Keep only if you want local cost estimation; otherwise delete the whole file and remove imports.

### `backend/app/models/usage.py`
- **Commercial entities:** `UsageCounter` model
- **Delete:** Nothing — this is a generic analytics counter.
- **Keep:** Entire file (just remove the `limit_snapshot` column if no longer relevant).
- **Cross-references:** `app/models/__init__.py`, `app/services/usage.py`.
- **Suggested replacement:** Keep as-is for analytics.

---

## 5. MARKETPLACE

### `backend/app/api/v1/marketplace.py`
- **Commercial imports:** `MarketplaceListing`, `MarketplacePurchase`, `AgentImporter`, `AJLedger` (inline for AJ purchase debit)
- **Delete routes:**
  - `GET /listings`
  - `GET /listings/{id}`
  - `POST /listings`
  - `POST /purchase/{id}`
  - `POST /rate/{id}`
  - `DELETE /listings/{id}`
- **Keep:** Nothing.
- **Cross-references:** Mounted in `api/v1/__init__.py` at prefix `/marketplace`. Referenced by `app/api/v1/pocket.py` (inline import of `MarketplaceListing`).
- **Suggested replacement:** Delete file and remove router include.

### `backend/app/models/marketplace.py`
- **Commercial entities:** `MarketplaceListing`, `MarketplacePurchase`
- **Delete:** Entire file.
- **Cross-references:**
  - `app/models/__init__.py`
  - `app/api/v1/marketplace.py`
  - `app/api/v1/pocket.py` (inline import)
- **Suggested replacement:** Delete file. Remove from `models/__init__.py`.

---

## 6. QUEST PROGRESSION

### `backend/app/api/v1/quest.py`
- **Commercial imports:** `ProgressionService`, `MILESTONE_DEFINITIONS`, `ALL_MILESTONES`, `FEATURE_REGISTRY`, `check_feature_access`, `get_locked_feature_info`
- **Delete routes:**
  - `GET /progress`
  - `POST /check-milestones`
  - `GET /milestones`
  - `POST /sync-stats`
  - `POST /check-feature`
  - `GET /features`
- **Keep:** Nothing — the entire router is for gamified tier progression.
- **Cross-references:** Mounted in `api/v1/__init__.py`.
- **Suggested replacement:** Delete file and remove router include.

### `backend/app/models/progression.py`
- **Commercial entities:** `UserProgression` model
- **Delete:** Entire file.
- **Cross-references:**
  - `app/models/__init__.py`
  - `app/models/user.py` (relationship `progression`)
  - `app/services/progression.py`
  - `app/api/v1/quest.py`
  - `app/api/v1/admin.py`
  - `app/api/v1/agora.py`
  - `app/api/v1/webhooks.py`
  - `app/services/billing.py` (inline import)
- **Suggested replacement:** Delete file. Remove relationship from `models/user.py`.

### `backend/app/services/progression.py`
- **Commercial imports:** `app.config.TIER_LIMITS`, `TIER_HIERARCHY`, `app.models.progression.UserProgression`, `app.services.apexjoule.constants.QUEST_BOUNTIES`, `app.services.apexjoule.ledger.AJLedger`
- **Delete:** Entire file (`ProgressionService`, milestone definitions, feature registry, quest bounties, AJ credit on milestone completion).
- **Cross-references:**
  - `app/api/v1/quest.py`
  - `app/api/v1/admin.py`
  - `app/api/v1/webhooks.py`
  - `app/api/v1/billing.py` (inline import)
  - `app/services/billing.py` (inline import for quest status)
- **Suggested replacement:** Delete file.

### `backend/alembic/versions/003_progression_table.py`
- **Commercial entities:** Creates `user_progressions` table.
- **Delete:** Skip this migration for new local installs. Existing DBs can leave the table (unused) or run a new migration to drop it.
- **Cross-references:** Env imports all versions.
- **Suggested replacement:** For clean local install, start from a fresh migration set or skip.

---

## 7. FEATURE CREDITS

### `backend/app/models/feature_credit.py`
- **Commercial entities:** `FeatureCreditBalance` model (purchased pack credits: opus_messages, suno_generations, training_jobs)
- **Delete:** Entire file.
- **Cross-references:**
  - `app/models/__init__.py`
  - `app/services/usage.py` (imported at top)
  - `app/services/apexjoule/shop.py` (inline import)
- **Suggested replacement:** Delete file. Remove from `models/__init__.py`.

### `backend/app/services/usage.py` — FeatureCreditService section
- Already covered in Section 4. Delete class `FeatureCreditService` entirely.

---

## 8. COUPONS (part of billing models + billing API)

### `backend/app/models/billing.py` — Coupon & CouponRedemption
- Already covered in Section 1. Delete both models.

### `backend/app/api/v1/billing.py` — coupon endpoints
- Already covered in Section 1. Delete all coupon routes.

---

## CROSS-REFERENCE FILES THAT IMPORT COMMERCIAL SYSTEMS (but are not themselves commercial files)

These files need surgical edits to remove inline/commercial imports while preserving their core functionality.

### `backend/app/api/v1/chat.py`
- **Commercial imports to remove:**
  - Top: `from app.services.billing import BillingService`
  - Top: `from app.config import TIER_LIMITS`
  - Inline ~992: `from app.services.usage import UsageService`
  - Inline ~1437: `from app.services.usage import UsageService`
  - Inline ~1456-1457: `from app.services.apexjoule.ledger import AJLedger`, `AJ_CITIZEN_ACTION_COSTS`
  - Inline ~1520: `from app.services.apexjoule.calculator import compute_aj_for_chat`
  - Inline ~1673: `from app.services.usage import UsageService`
  - Inline ~1692-1693: `AJLedger`, `AJ_CITIZEN_ACTION_COSTS`
  - Inline ~1726: `compute_aj_for_chat`
- **What to keep:** Chat streaming, tool execution, memory storage, message persistence.
- **Replacement behavior:** Remove billing checks (lines ~847-886). Remove usage increment calls. Remove AJ credit computation. Always allow all models/tools. Remove AJ citizen debit logic.

### `backend/app/api/v1/council.py`
- **Commercial imports to remove:**
  - Top: `from app.services.billing import BillingService`
  - Inline ~312: `from app.models.billing import Subscription`
  - Inline ~321: `from app.services.usage import UsageService`
  - Inline ~468: `from app.services.usage import UsageService`
  - Inline ~841: `from app.services.apexjoule.calculator import compute_aj_for_council_round`
  - Inline ~842: `from app.services.billing import BillingService`
- **What to keep:** Council deliberation, streaming, convergence, Agora posting.
- **Replacement behavior:** Remove tier limit checks for council sessions. Remove usage counter increment. Remove AJ credit for council rounds.

### `backend/app/api/v1/council_ws.py`
- **Commercial imports to remove:**
  - Top: `from app.services.billing import BillingService`
  - Inline ~484: `settings.stripe_secret_key` check
- **What to keep:** WebSocket streaming for council.
- **Replacement behavior:** Remove billing checks. Remove Stripe key check.

### `backend/app/api/v1/agents.py`
- **Commercial imports to remove:**
  - Top: `from app.services.billing import BillingService`
  - Inline ~126-127: `settings.stripe_secret_key` + billing usage recording
  - Inline ~342: billing usage recording
- **What to keep:** Agent spawning, PAC mode, background tasks.
- **Replacement behavior:** Remove usage recording. Remove model tier filtering.

### `backend/app/api/v1/dream.py`
- **Commercial imports to remove:**
  - Top: `from app.config import TIER_LIMITS`
  - Inline ~126, 183, 242, 355, 464: `from app.services.billing import BillingService`
- **What to keep:** Dream engine execution, memory consolidation.
- **Replacement behavior:** Remove tier limit checks for dream cycles. Remove billing checks.

### `backend/app/api/v1/music.py`
- **Commercial imports to remove:**
  - Inline ~159: `from app.models.billing import Subscription`
  - Inline ~168, 199: `from app.services.usage import UsageService`
- **What to keep:** Suno music generation, compilation.
- **Replacement behavior:** Remove tier limit checks for Suno generations. Remove usage counter increment.

### `backend/app/api/v1/jam.py`
- **Commercial imports to remove:**
  - Inline ~255: `from app.models.billing import Subscription`
  - Inline ~264, 322: `from app.services.usage import UsageService`
- **What to keep:** Jam session creation, collaboration.
- **Replacement behavior:** Remove tier limit checks. Remove usage counter increment.

### `backend/app/api/v1/nursery.py`
- **Commercial imports to remove:**
  - Top: `from app.models.billing import Subscription`
  - Inline ~76: `from app.config import TIER_LIMITS`
  - Inline ~371: `from app.services.usage import UsageService`
- **What to keep:** Model training, dataset management.
- **Replacement behavior:** Remove tier limit checks. Remove usage counter increment for training jobs.

### `backend/app/api/v1/memory_import.py`
- **Commercial imports to remove:**
  - Inline ~98: `from app.services.billing import BillingService`
  - Top: `from app.config import TIER_LIMITS`
  - Inline ~104: `from app.config import QUEST_TIER_MAP`
- **What to keep:** Universal memory import (Transmuter).
- **Replacement behavior:** Remove tier limit checks. Remove billing checks.

### `backend/app/api/v1/pocket.py`
- **Commercial imports to remove:**
  - Top: `from app.services.billing import BillingService`
  - Top: `from app.services.apexjoule.ledger import AJLedger`
  - Top: `from app.services.apexjoule.shop import AJShop`
  - Top: `from app.services.apexjoule.constants import ...`
  - Top: `from app.services.apexjoule.love_scorer import love_depth_tier_name`
  - Inline ~906: `from app.services.apexjoule.constants import AJ_SHOP_PRICES, AJ_CITIZEN_ACTION_COSTS`
  - Inline ~1293: `from app.models.billing import Subscription`
  - Inline ~3007-3008: `Subscription`, `AJ_TIER_PRICES`
  - Inline ~3059: `Subscription`
  - Inline ~3060: `AJ_TIER_PRICES`
  - Inline ~3120: `from app.models.marketplace import MarketplaceListing`
- **What to keep:** ApexPocket device auth, cloud sync, file sync.
- **Replacement behavior:** Remove all AJ economy integrations (shop, ledger, love scores). Remove billing tier checks. Remove marketplace listing inline import.

### `backend/app/api/v1/athaverse.py`
- **Commercial imports to remove:**
  - Top: `from app.services.billing import BillingService`
  - Inline ~281: `from app.models.billing import Subscription`
  - Inline ~785: `from app.services.apexjoule.constants import AJ_SHOP_PRICES`
- **What to keep:** VR/Quest 3 agent chat, tool execution.
- **Replacement behavior:** Remove billing checks. Remove AJ shop references.

### `backend/app/api/v1/admin.py`
- **Commercial imports to remove:**
  - Top: `from app.models.billing import Subscription, CreditBalance, CreditTransaction, Coupon`
  - Top: `from app.models.progression import UserProgression`
  - Top: `from app.config import TIER_LIMITS, QUEST_TIER_MAP`
  - Inline ~321: `from app.services.usage import UsageService, FeatureCreditService, get_current_period`
  - Inline ~406: `from app.services.progression import ProgressionService`
  - Inline ~472: admin credit-grant endpoint (`POST /admin/credits`)
  - Inline ~867: `from app.config import TIER_LIMITS, GRANTABLE_PROVIDERS`
- **What to keep:** User list, error logs, stats, admin promotion.
- **Replacement behavior:** Remove billing/credit/progression admin panels. Remove credit-grant endpoint. Keep user/grants/errors tabs.

### `backend/app/api/v1/user.py`
- **Commercial imports to remove:**
  - Top: `from app.models.billing import Subscription`
  - Top: `from app.config import get_settings, TIER_LIMITS`
- **What to keep:** User profile, settings, password change.
- **Replacement behavior:** Remove subscription tier lookup from user profile endpoint. Return local/unlimited features.

### `backend/app/api/v1/agora.py`
- **Commercial imports to remove:**
  - Top: `from app.models.progression import UserProgression`
- **What to keep:** Agora social feed, posts, reactions.
- **Replacement behavior:** Remove quest progression inline import if used for feature gating.

### `backend/app/worker.py`
- **Commercial imports to remove:**
  - Top: `from app.config import get_settings, TIER_LIMITS`
  - Inline ~34: `from app.services.billing import BillingService`
  - Inline ~86: `from app.services.apexjoule.calculator import compute_aj_for_dream`
  - Inline ~154: `from app.services.apexjoule.calculator import compute_aj_for_dream`
- **What to keep:** Dream cycle execution, targeted dreams, scheduled sweep.
- **Replacement behavior:** Remove `_resolve_dream_api_key()` billing/tier resolution (resolve keys directly without BillingService). Remove AJ credit after dreams. Remove `TIER_LIMITS` dream cycle gating in `scheduled_dream_sweep()` — allow unlimited dreams.

### `backend/app/tools/nursery.py`
- **Commercial imports to remove:**
  - Inline ~401: `from app.models.billing import Subscription`
  - Inline ~1217: `from app.models.billing import Subscription`
- **What to keep:** Nursery tools (train, dataset management).
- **Replacement behavior:** Remove tier limit checks.

### `backend/app/services/cloud_trainer.py`
- **Commercial imports to remove:**
  - Inline ~270: `from app.models.billing import Subscription`
- **What to keep:** Cloud training logic.
- **Replacement behavior:** Remove tier limit checks.

### `backend/app/services/multiverse.py`
- **Commercial imports to remove:**
  - Top: `from app.models.apexjoule import ApexJouleBalance`
- **What to keep:** Cross-user portal system.
- **Replacement behavior:** Remove AJ balance reference.

### `backend/app/services/portability/exporter.py`
- **Commercial imports to remove:**
  - Top: `from app.models.apexjoule import ApexJouleBalance, LoveScore`
- **What to keep:** Agent bundle export.
- **Replacement behavior:** Remove AJ balance and love score from export bundle.

### `backend/app/services/portability/importer.py`
- **Commercial imports to remove:**
  - Top: `from app.models.apexjoule import ApexJouleBalance, LoveScore`
- **What to keep:** Agent bundle import/validation.
- **Replacement behavior:** Remove AJ balance and love score from import bundle.

### `backend/app/models/user.py`
- **Commercial relationships to remove:**
  - `subscription = relationship("Subscription", ...)`
  - `credit_balance = relationship("CreditBalance", ...)`
  - `progression = relationship("UserProgression", ...)`
  - `aj_balances = relationship("ApexJouleBalance", ...)`
- **What to keep:** All other relationships (conversations, agents, knowledge, memories, music_tasks, folders, files, deliberation_sessions, nursery_*, devices).
- **Replacement behavior:** Remove all commercial relationships. If a minimal Subscription is kept, keep that one relationship only.

### `backend/app/models/__init__.py`
- **Commercial imports to remove:**
  - `from app.models.billing import Subscription, CreditBalance, CreditTransaction, WebhookEvent, Coupon, CouponRedemption`
  - `from app.models.usage import UsageCounter` (keep if keeping counters)
  - `from app.models.feature_credit import FeatureCreditBalance`
  - `from app.models.progression import UserProgression`
  - `from app.models.apexjoule import ApexJouleBalance, ApexJouleTransaction, LoveScore`
  - `from app.models.solana_payment import SolanaPayment`
  - `from app.models.marketplace import MarketplaceListing, MarketplacePurchase`
- **What to keep:** All non-commercial models.
- **Replacement behavior:** Remove imports and `__all__` entries.

### `backend/app/api/v1/__init__.py`
- **Commercial router includes to remove:**
  - `billing` router (prefix `/billing`)
  - `webhooks` router (prefix `/webhooks`)
  - `quest` router
  - `apexjoule` router (prefix `/aj`)
  - `solana` router (prefix `/solana`)
  - `marketplace` router (prefix `/marketplace`)
- **What to keep:** All other routers.
- **Replacement behavior:** Delete the six `router.include_router(...)` lines.

### `backend/app/main.py`
- **Commercial content:** `stripe-integration` in the `features` list of `/health` (line ~330). No actual Stripe imports here.
- **What to keep:** Everything else.
- **Replacement behavior:** Remove `"stripe-integration"` from the health check features list.

---

## DATABASE MIGRATION SUMMARY

| Migration | Action | Notes |
|-----------|--------|-------|
| `001_neo_cortex_columns.py` | **Keep** | Non-commercial (CerebroCortex) |
| `002_billing_tables.py` | **Replace** | Contains `subscriptions`, `credit_balances`, `credit_transactions`, `webhook_events`. Replace with a minimal `002_local_tier.py` that only creates a stripped `subscriptions` table. |
| `003_progression_table.py` | **Skip / Drop** | Creates `user_progressions`. Skip for new installs; drop table for existing. |

---

## ORDER OF REMOVAL (recommended)

1. **Router layer** (`api/v1/__init__.py`): Remove commercial router includes first so endpoints disappear.
2. **API layer** (`api/v1/billing.py`, `webhooks.py`, `solana.py`, `apexjoule.py`, `marketplace.py`, `quest.py`): Delete files.
3. **Service layer** (`services/billing.py`, `services/usage.py` FeatureCreditService, `services/pricing.py`, `services/progression.py`, `services/apexjoule/*`, `services/solana/*`): Delete or stub out.
4. **Model layer** (`models/billing.py` strip, `models/apexjoule.py`, `models/solana_payment.py`, `models/marketplace.py`, `models/progression.py`, `models/feature_credit.py`): Delete or strip.
5. **Schema layer** (`schemas/billing.py`): Replace with minimal local schema.
6. **Cross-reference surgery** (`chat.py`, `council.py`, `agents.py`, `dream.py`, `music.py`, `jam.py`, `nursery.py`, `memory_import.py`, `pocket.py`, `athaverse.py`, `admin.py`, `user.py`, `agora.py`, `worker.py`, `tools/nursery.py`, `services/cloud_trainer.py`, `services/multiverse.py`, `services/portability/*`): Remove inline imports and commercial logic.
7. **Config** (`config.py`): Remove Stripe settings, replace `TIER_LIMITS` with single local tier.
8. **Models init & User model**: Clean up imports and relationships.
9. **Migrations**: Replace `002`, skip/drop `003`.
10. **Health check** (`main.py`): Remove `"stripe-integration"` from features list.
