## 1. Shared age months and age band

- [x] 1.1 Extract tip birthday→months helpers into `app/shared/` (or shared module); keep tip `derive_baby_age` as thin wrapper
- [x] 1.2 Add `age_band_from_months(months)` (`m{N}` / `y{Y}` rules) with unit tests
- [x] 1.3 Wire clinic graph to derive months after profile fetch; inject months (or 未知) into clinic answer prompts instead of raw birthday

## 2. Knowledge quality hard filter

- [x] 2.1 Add configurable `KNOWLEDGE_QUALITY_MIN` (default 0.7) and filter low-score docs in knowledge search path
- [x] 2.2 Add tests: below-threshold excluded; missing score uses store default and may pass

## 3. Q&A store and rewrite

- [x] 3.1 Add Q&A fast-path collection/API (add/search by embedding + metadata: age_band, quality_score, standalone_question, answer)
- [x] 3.2 Implement rewrite-to-standalone-question node/helper with timeout (default 2s); failure → miss, no raw-query fallback for QA search
- [x] 3.3 Implement search hit logic: sim > 0.8, quality >= 0.7, age_band match; unknown age → miss
- [x] 3.4 Implement promote-on-accepted: only when implicit accepted AND rewrite succeeded that turn; global upsert with age_band

## 4. Clinic graph fast path

- [x] 4.1 Insert nodes after implicit_feedback: profile → derive age → rewrite → search_qa → (hit) format/return END / (miss) existing prepare
- [x] 4.2 Force miss when `force_needs_history` / history point-query / sensitive block_fast_path
- [x] 4.3 Ensure stream/non-stream and intent-nested clinic both use the same graph path; emit short thinking on hit/miss rewrite
- [x] 4.4 Optional feature flag `QA_FAST_PATH_ENABLED` (default on)

## 5. Retire explicit feedback

- [x] 5.1 Remove `POST /v1/clinic/feedback` and `POST /v1/tip/feedback` routes and dead imports
- [x] 5.2 Remove or shrink unused `FeedbackRequest` / feedback schemas if unreferenced
- [x] 5.3 Update deploy docs and module comments: no explicit feedback compatibility; note Go/Flutter 404 coordination

## 6. Tests and verification

- [x] 6.1 Unit tests: rewrite miss, age_band, hit/miss thresholds, promote gates, knowledge hard filter
- [x] 6.2 Graph/integration-style tests: hit skips prepare; force_needs_history skips fast path; feedback routes 404
- [x] 6.3 Manual smoke: accepted turn promotes; next similar question with same age_band hits; docs no longer advertise `/feedback`
