import React from "react";
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
  const iconMap: Record<string, string> = {
    shield: "🛡",
    users: "👥",
    bank: "🏦",
    chart: "📈",
    checklist: "☑",
  };

  return (
    <article className="gc-card gc-feature-card">
      <IconBadge>{iconMap[feature.icon] || "✓"}</IconBadge>
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
            <div className="gc-portrait-card">
              <div className="gc-person-placeholder">
                <span>GoClear</span>
                <strong>Readiness</strong>
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
  return (
    <main className="gc-page gc-auth-page">
      <Header />

      <section className="gc-container gc-auth-shell">
        <div className="gc-signup-form">
          <h1>Welcome to GoClear! 👋</h1>
          <p>Create your account and take the first step toward a stronger, fundable business.</p>

          <label>
            Full Name
            <input placeholder="Enter your full name" />
          </label>

          <label>
            Email Address
            <input placeholder="Enter your email address" type="email" />
          </label>

          <label>
            Password
            <input placeholder="Create a strong password" type="password" />
          </label>

          <ul className="gc-check-list gc-password-list">
            <li>At least 8 characters</li>
            <li>One number</li>
            <li>One uppercase letter</li>
            <li>One special character</li>
          </ul>

          <label>
            Confirm Password
            <input placeholder="Confirm your password" type="password" />
          </label>

          <label>
            Business Name <em>(Optional)</em>
            <input placeholder="Enter your business name" />
          </label>

          <label className="gc-checkbox">
            <input type="checkbox" />
            <span>I agree to GoClear&apos;s <a href="/goclear">Terms of Service</a> and <a href="/goclear">Privacy Policy</a>.</span>
          </label>

          <button className="gc-btn gc-btn-primary gc-full-btn" type="button">Create My Account</button>

          <div className="gc-divider">or sign up with</div>

          <button className="gc-social-btn" type="button">G Continue with Google</button>
          <button className="gc-social-btn" type="button">Continue with Apple</button>

          <p className="gc-secure-line">🔒 Your information is secure and encrypted.</p>
        </div>

        <aside className="gc-benefits-panel">
          <h2>What You&apos;ll Get with GoClear</h2>

          {[
            ["Improve Readiness for Credit", "Understand and strengthen what lenders look for."],
            ["Expert Business Setup Guidance", "Start your business the right way with confidence."],
            ["Build Business Bankability", "Create strong financial foundations and credibility."],
            ["Prepare for Funding", "Get your documents and profile funding-ready."],
            ["Personalized Action Plans", "Step-by-step plans tailored to your business goals."],
          ].map(([title, text]) => (
            <div className="gc-benefit-mini" key={title}>
              <IconBadge>✓</IconBadge>
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
        <div>🛡 <strong>Secure & Private</strong><span>Bank-level encryption</span></div>
        <div>👥 <strong>Trusted Platform</strong><span>Built for businesses</span></div>
        <div>🎧 <strong>Expert Support</strong><span>We&apos;re here to help</span></div>
        <div>✅ <strong>Clear Guidance</strong><span>Actionable next steps</span></div>
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
        <div>🛡 <strong>Secure Payments</strong><span>Your payment information is encrypted and secure.</span></div>
        <div>↻ <strong>Cancel Anytime</strong><span>No long-term contracts. Cancel anytime.</span></div>
        <div>✅ <strong>Satisfaction Support</strong><span>We&apos;ll help you choose the right next step.</span></div>
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
  return (
    <main className="gc-page gc-auth-page">
      <Header />
      <section className="gc-container gc-login-card">
        <GoClearLogo />
        <h1>Client Login</h1>
        <p>Access your GoClear portal and continue your readiness journey.</p>

        <label>
          Email Address
          <input placeholder="Enter your email address" type="email" />
        </label>

        <label>
          Password
          <input placeholder="Enter your password" type="password" />
        </label>

        <button className="gc-btn gc-btn-primary gc-full-btn" type="button">Login</button>
        <a href="/client" className="gc-login-link">Continue to Client Portal</a>

        <p className="gc-secure-line">Supabase frontend auth verification is still required before live login is final.</p>
      </section>
    </main>
  );
}
