-- ============================================================
-- Migration 002: policy_rules — user-specific & data-specific markers
-- Run this in the Supabase SQL editor before deploying.
--
-- Adds two enforcement dimensions and one audit marker to policy_rules:
--   subject_type / subject — target ONE specific user (by email) instead of a
--                            role. rego_builder emits `input.user.email == subject`.
--   scope                  — server-computed label (role|user|data|user_data)
--                            purely for listing/auditing fine-grained rules.
-- Existing rows are unaffected: subject_type defaults to 'role', subject NULL.
-- ============================================================

ALTER TABLE public.policy_rules
    ADD COLUMN IF NOT EXISTS subject_type text NOT NULL DEFAULT 'role',
    ADD COLUMN IF NOT EXISTS subject      text NULL,
    ADD COLUMN IF NOT EXISTS scope        text NULL;

-- subject_type is a closed set.
ALTER TABLE public.policy_rules
    DROP CONSTRAINT IF EXISTS policy_rules_subject_type_check;
ALTER TABLE public.policy_rules
    ADD CONSTRAINT policy_rules_subject_type_check
    CHECK (subject_type IN ('role', 'user'));

-- user-scoped rows MUST name a subject; role-scoped rows MUST NOT.
-- Blocks half-configured rows that would silently never match.
ALTER TABLE public.policy_rules
    DROP CONSTRAINT IF EXISTS policy_rules_subject_presence_check;
ALTER TABLE public.policy_rules
    ADD CONSTRAINT policy_rules_subject_presence_check
    CHECK ( (subject_type = 'user' AND subject IS NOT NULL)
         OR (subject_type = 'role' AND subject IS NULL) );

CREATE INDEX IF NOT EXISTS idx_policy_subject ON public.policy_rules (subject);
CREATE INDEX IF NOT EXISTS idx_policy_scope   ON public.policy_rules (scope);
