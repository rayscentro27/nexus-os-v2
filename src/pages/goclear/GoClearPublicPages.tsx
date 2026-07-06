import React, { useState } from "react";
import { ShieldCheck, Building2, Landmark, TrendingUp, ClipboardCheck, BadgeCheck, Lock, Users, FileCheck, CreditCard, HelpCircle } from "lucide-react";
import { supabase, isSupabaseConfigured } from "../../lib/supabaseClient";
import { getPasswordResetRedirectUrl } from "../../lib/authHelpers";
import "./goclear-public.css";

const features = [
  {
    title: "Improve Readiness for Credit",
    text: "Understand and strengthen the key factors lenders and funders look for.",
    icon: "shield",
  },
  {
    title: "Business Setup Guidance",
    text: "Get help forming your business the right way from the start.",
    icon: "users",
  },
  {
    title: "Business Bankability",
    text: "Build strong financial foundations and business systems that build trust.",
    icon: "bank",
  },
  {
    title: "Funding Preparation",
    text: "Prepare documents, financials, and profiles that support funding readiness.",
    icon: "chart",
  },
  {
    title: "Action Plans That Work",
    text: "Personalized, step-by-step plans to help you move forward with confidence.",
    icon: "checklist",
  },
];

const steps = [
  ["Assess", "Take a quick assessment to understand where your business stands."],
  ["Analyze", "We review your readiness and identify opportunities for improvement."],
  ["Plan", "Get your personalized action plan and expert recommendations."],
  ["Implement", "Take action with tools, templates, and resources that guide you."],
  ["Get Fundable", "Strengthen your profile and prepare for better opportunities."],
];

const plans = [
  {
    name: "Readiness Snapshot",
    price: "$0",
    cadence: "Free",
    cta: "Get Started Free",
    featured: false,
    description: "Get a quick snapshot of your business readiness.",
    includes: [
      "Business Readiness Assessment",
      "Credit Readiness Overview",
      "Basic Recommendations",
      "Resource Library Access",
    ],
    muted: ["Action Plan", "Document Tools", "Expert Support"],
  },
  {
    name: "GoClear Readiness Portal",
    price: "$49",
    cadence: "/month",
    cta: "Start My Plan",
    featured: true,
    description: "Everything you need to improve and build your business.",
    includes: [
      "Personalized Action Plan",
      "Business Bankability Tools",
      "Document & Template Library",
      "Funding Readiness Checklist",
      "Progress Tracking",
      "Email Support",
    ],
    muted: [],
  },
  {
    name: "Funding Builder Plus",
    price: "$149",
    cadence: "/month",
    cta: "Start My Plan",
    featured: false,
    description: "Advanced tools and support to prepare and raise funding.",
    includes: [
      "Funding Strategy Session",
      "Advanced Financial Tools",
      "Investor & Lender Materials",
      "Priority Support",
      "Funding Opportunity Alerts",
      "Quarterly Business Review",
    ],
    muted: [],
  },
];

function GoClearLogo() {
  return (
    <a className="gc-logo" href="/goclear" aria-label="GoClear home">
      <span className="gc-logo-mark">✓</span>
      <span>GoClear</span>
    </a>
  );
}

function IconBadge({ children }: { children: React.ReactNode }) {
  return <span className="gc-icon-badge">{children}</span>;
}

function Header({ active = "" }: { active?: string }) {
  return (
    <header className="gc-header">
      <div className="gc-container gc-header-inner">
        <GoClearLogo />
        <nav className="gc-nav" aria-label="GoClear navigation">
          <a href="/goclear#solutions" className={active === "solutions" ? "active" : ""}>Solutions</a>
          <a href="/goclear#how-it-works" className={active === "how" ? "active" : ""}>How It Works</a>
          <a href="/goclear/pricing" className={active === "pricing" ? "active" : ""}>Pricing</a>
          <a href="/goclear#resources">Resources</a>
          <a href="/goclear#about">About</a>
        </nav>
        <div className="gc-header-actions">
          <a className="gc-btn gc-btn-ghost" href="/goclear/login">Login</a>
          <a className="gc-btn gc-btn-primary" href="/goclear/signup">Sign Up</a>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="gc-footer">
      <div className="gc-container gc-footer-grid">
        <div>
          <GoClearLogo />
          <p>Tools, guidance, and action plans to strengthen your business and unlock greater opportunities.</p>
          <div className="gc-socials">
            <span>in</span><span>f</span><span>ig</span><span>▶</span>
          </div>
        </div>

        <div>
          <h4>Solutions</h4>
          <a href="/goclear#solutions">Credit Readiness</a>
          <a href="/goclear#solutions">Business Setup</a>
          <a href="/goclear#solutions">Business Bankability</a>
          <a href="/goclear#solutions">Funding Preparation</a>
          <a href="/goclear#solutions">Action Plans</a>
        </div>

        <div>
          <h4>Company</h4>
          <a href="/goclear#about">About Us</a>
          <a href="/goclear#how-it-works">How It Works</a>
          <a href="/goclear/pricing">Pricing</a>
          <a href="/goclear#resources">Success Stories</a>
          <a href="/goclear#about">Careers</a>
        </div>

        <div>
          <h4>Resources</h4>
          <a href="/goclear#resources">Blog</a>
          <a href="/goclear#resources">Guides & Templates</a>
          <a href="/goclear#resources">Funding Directory</a>
          <a href="/goclear#resources">FAQs</a>
          <a href="/goclear#resources">Community</a>
        </div>

        <div>
          <h4>Stay Updated</h4>
          <p>Get tips, resources, and offers straight to your inbox.</p>
          <form className="gc-email-form" onSubmit={(e) => e.preventDefault()}>
            <input placeholder="Enter your email" />
            <button type="submit">→</button>
          </form>
        </div>
      </div>

      <div className="gc-container gc-footer-bottom">
        <span>© 2026 GoClear. All rights reserved.</span>
        <span>🔒 Your information is secure and encrypted.</span>
      </div>
    </footer>
  );
}

function FeatureCard({ feature }: { feature: typeof features[0] }) {
  const iconMap: Record<string, React.ReactNode> = {
    shield: <ShieldCheck size={28} strokeWidth={2} />,
    users: <Users size={28} strokeWidth={2} />,
    bank: <Landmark size={28} strokeWidth={2} />,
    chart: <TrendingUp size={28} strokeWidth={2} />,
    checklist: <ClipboardCheck size={28} strokeWidth={2} />,
  };

  return (
    <article className="gc-card gc-feature-card">
      <IconBadge>{iconMap[feature.icon] || <BadgeCheck size={28} strokeWidth={2} />}</IconBadge>
      <h3>{feature.title}</h3>
      <p>{feature.text}</p>
    </article>
  );
}

function PromoBanner() {
  return (
    <section className="gc-promo">
      <div>
        <span className="gc-pill">Launch Offer</span>
        <h2>Limited Time: Launch Offer</h2>
        <p>Get 50% off your first 3 months on any paid plan. Build today. Fund tomorrow.</p>
        <a href="/goclear/pricing" className="gc-btn gc-btn-primary">View Plans & Save →</a>
      </div>

      <div className="gc-promo-right">
        <strong>50%</strong>
        <span>OFF</span>
        <p>FIRST 3 MONTHS</p>
        <div className="gc-rocket" aria-hidden="true">🚀</div>
      </div>
    </section>
  );
}

export function GoClearLandingPage() {
  return (
    <main className="gc-page">
      <Header />

      <section className="gc-hero">
        <div className="gc-container gc-hero-grid">
          <div className="gc-hero-copy">
            <h1>
              Stronger Business.
              <br />
              Better Credit. More Funding.
            </h1>
            <p>
              GoClear helps you improve readiness for credit and funding with expert guidance,
              proven frameworks, and a clear plan to move your business forward.
            </p>

            <div className="gc-hero-actions">
              <a href="/goclear/signup" className="gc-btn gc-btn-primary">Get Started Free →</a>
              <a href="#how-it-works" className="gc-btn gc-btn-secondary">See How It Works ▶</a>
            </div>

            <div className="gc-micro-trust">
              <span>✓ No credit card required</span>
              <span>✓ Cancel anytime</span>
              <span>✓ Works for any business</span>
            </div>
          </div>

          <div className="gc-hero-visual" aria-label="GoClear readiness visual">
            <div className="gc-hero-illustration">
              <div className="gc-readiness-badge">
                <span>GoClear</span>
                <strong>Readiness</strong>
              </div>

              <div className="gc-hero-score-card">
                <span>Readiness Score</span>
                <strong>82%</strong>
                <div className="gc-score-bar"><i /></div>
              </div>

              <div className="gc-hero-main-card">
                <div className="gc-hero-avatar">GC</div>
                <strong>Business Readiness</strong>
                <span>Credit · Funding · Growth</span>
              </div>

              <div className="gc-floating-card gc-floating-card-one">
                <span><BadgeCheck size={16} strokeWidth={2.5} /></span>
                <b>Credit Ready</b>
              </div>

              <div className="gc-floating-card gc-floating-card-two">
                <span><FileCheck size={16} strokeWidth={2.5} /></span>
                <b>Funding Prep</b>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="gc-container gc-trust-strip" aria-label="Trust indicators">
        <div>
          <strong>★★★★★</strong>
          <span>4.8/5 Member Rating</span>
        </div>
        <div>
          <strong>Trusted Guidance</strong>
          <span>Built for entrepreneurs and small businesses</span>
        </div>
        <div>
          <strong>Secure & Private</strong>
          <span>Designed to protect your information</span>
        </div>
        <div>
          <strong>A+ Readiness Support</strong>
          <span>Focused on clear next steps</span>
        </div>
      </section>

      <section className="gc-container gc-section" id="solutions">
        <div className="gc-section-heading">
          <h2>Everything You Need to Get Fundable</h2>
          <p>Tools, guidance, and action plans to strengthen your business and improve your access to credit and capital.</p>
        </div>

        <div className="gc-feature-grid">
          {features.map((feature) => (
            <FeatureCard feature={feature} key={feature.title} />
          ))}
        </div>
      </section>

      <section className="gc-container gc-section" id="how-it-works">
        <div className="gc-section-heading">
          <h2>Your Path to Readiness in 5 Simple Steps</h2>
        </div>

        <div className="gc-steps">
          {steps.map(([title, text], index) => (
            <article className="gc-step" key={title}>
              <span>{index + 1}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="gc-container">
        <PromoBanner />
      </div>

      <section className="gc-container gc-compliance-note">
        <p>
          GoClear does not guarantee funding approval or credit score increases. Outcomes depend on profile,
          documentation, lender/program requirements, and client follow-through.
        </p>
      </section>

      <Footer />
    </main>
  );
}

export function GoClearSignupPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  function validatePassword(p: string): string[] {
    const issues: string[] = [];
    if (p.length < 8) issues.push("At least 8 characters");
    if (!/\d/.test(p)) issues.push("One number");
    if (!/[A-Z]/.test(p)) issues.push("One uppercase letter");
    if (!/[!@#$%^&*(),.?\":{}|<>]/.test(p)) issues.push("One special character");
    return issues;
  }

  const passwordIssues = validatePassword(password);
  const passwordValid = passwordIssues.length === 0;

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setErr("");

    if (!passwordValid) {
      setErr("Please meet all password requirements.");
      return;
    }
    if (password !== confirm) {
      setErr("Passwords do not match.");
      return;
    }
    if (!agreed) {
      setErr("You must agree to the Terms of Service and Privacy Policy.");
      return;
    }

    setBusy(true);
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
          business_name: businessName || undefined,
        },
      },
    });

    if (error) {
      const msg = error.message.toLowerCase();
      if (msg.includes("already registered")) {
        setErr("An account with this email already exists. Try logging in instead.");
      } else if (msg.includes("password")) {
        setErr("Password does not meet requirements. Please use at least 8 characters with a number, uppercase letter, and special character.");
      } else {
        setErr(error.message);
      }
      setBusy(false);
    } else {
      setDone(true);
      setBusy(false);
    }
  }

  if (done) {
    return (
      <main className="gc-page gc-auth-page">
        <Header />
        <section className="gc-container gc-login-card">
          <GoClearLogo />
          <h1>Check Your Email</h1>
          <p>We sent a confirmation link to <strong>{email}</strong>. Click the link to activate your account, then come back to sign in.</p>
          <a href="/goclear/login" className="gc-btn gc-btn-primary gc-full-btn">Go to Login</a>
        </section>
      </main>
    );
  }

  return (
    <main className="gc-page gc-auth-page">
      <Header />

      <section className="gc-container gc-auth-shell">
        <div className="gc-signup-form">
          <h1>Welcome to GoClear! 👋</h1>
          <p>Create your account and take the first step toward a stronger, fundable business.</p>

          {!isSupabaseConfigured && (
            <div className="gc-error">Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
          )}

          <form onSubmit={handleSignup}>
            <label>
              Full Name
              <input
                placeholder="Enter your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                required
              />
            </label>

            <label>
              Email Address
              <input
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              Password
              <input
                placeholder="Create a strong password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
            </label>

            <ul className="gc-check-list gc-password-list">
              <li className={password.length >= 8 ? "gc-met" : ""}>At least 8 characters</li>
              <li className={/\d/.test(password) ? "gc-met" : ""}>One number</li>
              <li className={/[A-Z]/.test(password) ? "gc-met" : ""}>One uppercase letter</li>
              <li className={/[!@#$%^&*(),.?\":{}|<>]/.test(password) ? "gc-met" : ""}>One special character</li>
            </ul>

            <label>
              Confirm Password
              <input
                placeholder="Confirm your password"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </label>

            <label>
              Business Name <em>(Optional)</em>
              <input
                placeholder="Enter your business name"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
              />
            </label>

            <label className="gc-checkbox">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
              />
              <span>I agree to GoClear&apos;s <a href="/goclear">Terms of Service</a> and <a href="/goclear">Privacy Policy</a>.</span>
            </label>

            {err && <div className="gc-error">{err}</div>}

            <button
              className="gc-btn gc-btn-primary gc-full-btn"
              type="submit"
              disabled={busy || !isSupabaseConfigured}
            >
              {busy ? "Creating Account…" : "Create My Account"}
            </button>
          </form>

          <div className="gc-divider">or sign up with</div>

          <button className="gc-social-btn" type="button" disabled>G Continue with Google</button>
          <button className="gc-social-btn" type="button" disabled>Continue with Apple</button>

          <p className="gc-secure-line">🔒 Your information is secure and encrypted.</p>
        </div>

        <aside className="gc-benefits-panel">
          <h2>What You&apos;ll Get with GoClear</h2>

          {[
            ["Improve Readiness for Credit", "Understand and strengthen what lenders look for.", <ShieldCheck size={20} strokeWidth={2} />],
            ["Expert Business Setup Guidance", "Start your business the right way with confidence.", <Building2 size={20} strokeWidth={2} />],
            ["Build Business Bankability", "Create strong financial foundations and credibility.", <Landmark size={20} strokeWidth={2} />],
            ["Prepare for Funding", "Get your documents and profile funding-ready.", <TrendingUp size={20} strokeWidth={2} />],
            ["Personalized Action Plans", "Step-by-step plans tailored to your business goals.", <ClipboardCheck size={20} strokeWidth={2} />],
          ].map(([title, text, icon]) => (
            <div className="gc-benefit-mini" key={title as string}>
              <IconBadge>{icon}</IconBadge>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </div>
          ))}

          <div className="gc-testimonial">
            <strong>&ldquo;</strong>
            <p>GoClear helped us organize our business and understand what to work on next.</p>
            <b>— Jasmine R.</b>
            <span>Founder, JRC Consulting</span>
          </div>
        </aside>
      </section>

      <section className="gc-container gc-auth-trust-row">
        <div><Lock size={20} strokeWidth={2} /> <strong>Secure & Private</strong><span>Bank-level encryption</span></div>
        <div><Users size={20} strokeWidth={2} /> <strong>Trusted Platform</strong><span>Built for businesses</span></div>
        <div><HelpCircle size={20} strokeWidth={2} /> <strong>Expert Support</strong><span>We&apos;re here to help</span></div>
        <div><BadgeCheck size={20} strokeWidth={2} /> <strong>Clear Guidance</strong><span>Actionable next steps</span></div>
      </section>
    </main>
  );
}

function PlanCard({ plan }: { plan: typeof plans[0] }) {
  return (
    <article className={`gc-plan-card ${plan.featured ? "featured" : ""}`}>
      {plan.featured && <div className="gc-recommended">Recommended</div>}

      <h2>{plan.name}</h2>
      <p>{plan.description}</p>

      <div className="gc-price">
        <strong>{plan.price}</strong>
        <span>{plan.cadence}</span>
      </div>

      <a className={`gc-btn ${plan.featured ? "gc-btn-primary" : "gc-btn-secondary"}`} href="/goclear/signup">
        {plan.cta}
      </a>

      <h3>{plan.featured ? "Everything in Free, plus:" : plan.name === "Funding Builder Plus" ? "Everything in Portal, plus:" : "Includes:"}</h3>

      <ul className="gc-check-list">
        {plan.includes.map((item) => <li key={item}>{item}</li>)}
        {plan.muted.map((item) => <li className="muted" key={item}>{item}</li>)}
      </ul>
    </article>
  );
}

export function GoClearPricingPage() {
  return (
    <main className="gc-page">
      <Header active="pricing" />

      <section className="gc-container gc-pricing-hero">
        <h1>Choose the Plan That Fits Your Goals</h1>
        <p>All plans include core tools to help you improve readiness and get fundable.</p>

        <div className="gc-billing-toggle">
          <button>Pay Monthly</button>
          <span>Pay Annually</span>
          <em>Save 20%</em>
        </div>
      </section>

      <section className="gc-container gc-plan-grid">
        {plans.map((plan) => <PlanCard plan={plan} key={plan.name} />)}
      </section>

      <section className="gc-container gc-compare">
        <table>
          <thead>
            <tr>
              <th>Compare Plans</th>
              <th>Snapshot</th>
              <th>Portal</th>
              <th>Builder Plus</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Business Readiness Assessment", true, true, true],
              ["Personalized Action Plan", false, true, true],
              ["Business Bankability Tools", false, true, true],
              ["Document & Template Library", false, true, true],
              ["Funding Strategy Session", false, false, true],
              ["Priority Support", false, false, true],
            ].map(([feature, snapshot, portal, builder]) => (
              <tr key={feature as string}>
                <td>{feature}</td>
                <td>{snapshot ? "✓" : "—"}</td>
                <td>{portal ? "✓" : "—"}</td>
                <td>{builder ? "✓" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="gc-container gc-pricing-trust">
        <div><CreditCard size={20} strokeWidth={2} /> <strong>Secure Payments</strong><span>Your payment information is encrypted and secure.</span></div>
        <div><FileCheck size={20} strokeWidth={2} /> <strong>Cancel Anytime</strong><span>No long-term contracts. Cancel anytime.</span></div>
        <div><BadgeCheck size={20} strokeWidth={2} /> <strong>Satisfaction Support</strong><span>We&apos;ll help you choose the right next step.</span></div>
      </section>

      <section className="gc-container gc-compliance-note">
        <p>
          GoClear does not guarantee funding approval or credit score increases. Pricing and promotions may change.
          Checkout should remain test-mode or approval-gated until Stripe frontend integration is verified.
        </p>
      </section>

      <Footer />
    </main>
  );
}

export function GoClearLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(() =>
    new URLSearchParams(window.location.search).get("password-reset") === "success"
      ? "Password updated. Sign in with your new password."
      : ""
  );
  const [resetMode, setResetMode] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setErr("");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      const msg = error.message.toLowerCase();
      if (msg.includes("email not confirmed")) {
        setErr("Please check your email and click the confirmation link before signing in. Check your spam folder if you don't see it.");
      } else if (msg.includes("invalid login credentials")) {
        setErr("Incorrect email or password. Please try again.");
      } else {
        setErr(error.message);
      }
      setBusy(false);
    } else {
      window.location.assign("/client");
    }
  }

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setErr("");
    setNotice("");
    const redirectTo = getPasswordResetRedirectUrl();
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
    if (error) setErr(error.message);
    else setNotice("If this email is registered, a secure password-reset link has been sent. Check spam if it does not arrive.");
    setBusy(false);
  }

  return (
    <main className="gc-page gc-auth-page">
      <Header />
      <section className="gc-container gc-login-card">
        <GoClearLogo />
        <h1>Client Login</h1>
        <p>Access your GoClear portal and continue your readiness journey.</p>

        {!isSupabaseConfigured && (
          <div className="gc-error">Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
        )}

        {resetMode ? (
          <form onSubmit={handleReset}>
            <label>
              Email Address
              <input
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
            {err && <div className="gc-error">{err}</div>}
            {notice && <div className="gc-notice">{notice}</div>}
            <button className="gc-btn gc-btn-primary gc-full-btn" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? "Sending…" : "Send Reset Link"}
            </button>
            <button
              className="gc-btn gc-btn-ghost gc-full-btn"
              type="button"
              onClick={() => { setResetMode(false); setErr(""); setNotice(""); }}
            >
              Back to sign in
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            <label>
              Email Address
              <input
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              Password
              <input
                placeholder="Enter your password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>

            {err && <div className="gc-error">{err}</div>}
            {notice && <div className="gc-notice">{notice}</div>}

            <button className="gc-btn gc-btn-primary gc-full-btn" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? "Signing in…" : "Login"}
            </button>

            <button
              className="gc-btn gc-btn-ghost gc-full-btn"
              type="button"
              onClick={() => { setResetMode(true); setErr(""); setNotice(""); }}
            >
              Forgot password?
            </button>
          </form>
        )}

        <a href="/client" className="gc-login-link">Continue to Client Portal</a>
      </section>
    </main>
  );
}
