import { z } from 'zod';

// =============================================================================
// environment.ts — single source of truth for two things:
//   1. "Which environment is this?" (deploy-lane detection)
//   2. The ONE Zod schema that declares every process.env var this app reads.
//
// Lands at `web/src/environment.ts`. Prefer the namespace-import form at call
// sites:
//
//   import * as Environment from '@/environment';
//   if (Environment.isProduction) { ... }
//   const region = Environment.env.MY_REGION;
//
// -----------------------------------------------------------------------------
// ENV-VAR RULE (read before adding anything):
//
// Every environment variable the app consumes MUST be declared in `EnvSchema`
// below — nowhere else should read `process.env.FOO` directly. When you add a
// var: (a) add it to the schema here, (b) add it to `.env.docker.example` with
// a comment, and (c) tell the user it was added and why. Never introduce an
// env var silently. The schema is the inventory; if it's not here, it doesn't
// exist as far as the app is concerned.
// =============================================================================

// -----------------------------------------------------------------------------
// Deploy lanes. This file ships the DEFAULT three-lane shape, named to match
// Vercel's lanes exactly (local → development, preview → preview, production →
// production), so detection is near-identity. TRIM only if your split differs:
//
//   • dev + preview +  → DEFAULT. Keep as-is (preview → preview). Rename
//     prod               'preview' → 'staging' here + below if you prefer that
//                        vocabulary; the Vercel value is always 'preview'.
//   • dev + prod only  → delete the 'preview' entry below, and in
//                        detectEnvironment() map 'preview' → 'production'
//                        (preview deploys exercise prod-like code paths).
//   • single env       → keep only 'production'; detectEnvironment() can just
//                        `return 'production'` and you can drop the is* flags
//                        you don't branch on.
// -----------------------------------------------------------------------------
export const APP_ENVS = [
  'development',
  'preview', // ← delete this line for a dev+prod or single-env split
  'production',
] as const;
export type AppEnv = (typeof APP_ENVS)[number];

// True iff this code is running on Vercel infrastructure (build, runtime,
// edge). Derived from NEXT_PUBLIC_VERCEL_ENV being set, which Vercel does on
// every deploy when "Enable access to System Environment Variables" is checked
// in project settings (Settings → Environment Variables). False in local
// Docker, ad-hoc scripts, and unit tests.
//
// Use this — NOT `isProduction` and NOT `NODE_ENV === 'production'` — when you
// want "any deployed environment, not local." `isProduction` is true only on
// the live production lane; `NODE_ENV === 'production'` is true for every
// `next build` output, including a local prod build on a developer's machine.
export const isVercel = !!process.env.NEXT_PUBLIC_VERCEL_ENV;

// Single source of truth for the NEXT_PUBLIC_VERCEL_ENV → AppEnv mapping.
// Intentionally NOT exported — callers read the cached `ENVIRONMENT` const.
//
// We read NEXT_PUBLIC_VERCEL_ENV (not VERCEL_ENV) because Vercel sets BOTH
// server-side AND inlines NEXT_PUBLIC_VERCEL_ENV into the browser bundle via
// Next.js's NEXT_PUBLIC_ convention. One env var works in both runtimes, so
// environment.ts is safe to import from server actions AND client components
// with no client/server divergence in what `Environment.is*` returns.
//
// IMPORTANT: this depends on the "Enable access to System Environment
// Variables" toggle in Vercel project settings being ON. If anyone turns it
// off, every deploy is silently detected as 'development' here — unlocking
// dev-only code paths (auth bypass, dev-login, insecure cookies) on a real
// deploy. Don't turn it off without migrating this detection to another signal.
function detectEnvironment(): AppEnv {
  const v = process.env.NEXT_PUBLIC_VERCEL_ENV;
  if (!v) return 'development'; // local Docker, scripts, unit tests
  if (v === 'production') return 'production';
  if (v === 'preview') return 'preview'; // dev+prod split: change to 'production'
  // Strict mode: a value is set but unrecognized. Refuse to silently default
  // to 'development' — that would unlock dev-only code paths if Vercel ever
  // added a new env value we haven't mapped (e.g., custom environments).
  throw new Error(
    `environment.ts: NEXT_PUBLIC_VERCEL_ENV="${v}" — expected "production", "preview", or unset.`,
  );
}

// The ONE schema for this app's environment variables. Add new vars here.
const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  VITEST: z.string().optional(),
  // Add app env vars below, each with a one-line comment on what reads it and
  // which lanes it's present on. Example:
  //   STRIPE_SECRET_KEY: z.string(), // billing; set on preview + production
});

const parsed = EnvSchema.safeParse(process.env);

if (!parsed.success) {
  throw new Error(`Invalid environment variables: ${parsed.error.message}`);
}

export const env = parsed.data;

// Canonical, cached deploy-lane label. Computed once at module load. Use when
// you need to PASS the lane as a string (telemetry tags, log fields, admin UI
// labels); use the `is*` flags for branching.
export const ENVIRONMENT: AppEnv = detectEnvironment();

// Deployment-lane guards. (Drop `isPreview` if you trimmed the preview lane.)
export const isDevelopment = ENVIRONMENT === 'development';
export const isPreview = ENVIRONMENT === 'preview';
export const isProduction = ENVIRONMENT === 'production';

// Test-runner detection. NODE_ENV === 'test' covers tooling that sets it
// explicitly; VITEST is set by vitest itself regardless of NODE_ENV.
export const isTestEnv = env.NODE_ENV === 'test';
export const isVitestRunning = !!env.VITEST;
export const isTesting = isTestEnv || isVitestRunning;
