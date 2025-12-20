"""
Seed data generator for job_postings index.

Provides realistic job data when external APIs are unavailable.
This data is used to bootstrap the job search system for demos and testing.
"""
from typing import List, Dict, Any
from datetime import datetime


def generate_seed_jobs() -> List[Dict[str, Any]]:
    """
    Generate seed job data for testing and demos.

    Returns realistic job postings across multiple industries,
    roles, and locations.

    Returns:
        List of normalized job dicts ready for JobPosting model
    """
    seed_jobs = [
        # Technology - Software Engineering
        {
            "job_title": "Senior Software Engineer",
            "company_name": "Stripe",
            "location": "Remote - USA",
            "description": "Join Stripe's payments infrastructure team. Build scalable APIs serving millions of requests. Tech stack: Ruby, Go, React, PostgreSQL. 5+ years experience required.",
            "source": "seed",
            "external_url": "https://stripe.com/jobs/listing/senior-software-engineer",
            "external_id": "seed_stripe_swe_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Frontend Engineer",
            "company_name": "Airbnb",
            "location": "San Francisco, CA",
            "description": "Build world-class user experiences for Airbnb's platform. React, TypeScript, GraphQL. Work on search, booking flows, and host tools.",
            "source": "seed",
            "external_url": "https://airbnb.com/careers/frontend-engineer",
            "external_id": "seed_airbnb_fe_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Backend Engineer",
            "company_name": "Coinbase",
            "location": "Remote - USA",
            "description": "Build cryptocurrency exchange infrastructure. Python, Go, Kubernetes. Handle high-throughput trading systems and blockchain integrations.",
            "source": "seed",
            "external_url": "https://coinbase.com/careers/backend-engineer",
            "external_id": "seed_coinbase_be_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Full Stack Engineer",
            "company_name": "Shopify",
            "location": "Toronto, Canada",
            "description": "Build e-commerce tools for millions of merchants. Ruby on Rails, React, GraphQL. Work on checkout, payments, and merchant dashboard.",
            "source": "seed",
            "external_url": "https://shopify.com/careers/fullstack",
            "external_id": "seed_shopify_fs_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Staff Software Engineer",
            "company_name": "Databricks",
            "location": "San Francisco, CA",
            "description": "Lead technical initiatives on data platform. Scala, Spark, distributed systems. Design APIs used by thousands of data engineers.",
            "source": "seed",
            "external_url": "https://databricks.com/careers/staff-engineer",
            "external_id": "seed_databricks_staff_001",
            "extraction_complete": True,
        },

        # Technology - Infrastructure & DevOps
        {
            "job_title": "Site Reliability Engineer",
            "company_name": "GitLab",
            "location": "Remote - Worldwide",
            "description": "Ensure 99.99% uptime for GitLab SaaS. Kubernetes, Terraform, Go. Monitor, scale, and optimize cloud infrastructure.",
            "source": "seed",
            "external_url": "https://gitlab.com/careers/sre",
            "external_id": "seed_gitlab_sre_001",
            "extraction_complete": True,
        },
        {
            "job_title": "DevOps Engineer",
            "company_name": "Snowflake",
            "location": "San Mateo, CA",
            "description": "Build CI/CD pipelines for data cloud platform. Docker, Kubernetes, AWS. Automate deployments and infrastructure provisioning.",
            "source": "seed",
            "external_url": "https://snowflake.com/careers/devops",
            "external_id": "seed_snowflake_devops_001",
            "extraction_complete": True,
        },

        # Technology - Data & ML
        {
            "job_title": "Data Engineer",
            "company_name": "Notion",
            "location": "San Francisco, CA",
            "description": "Build data pipelines and analytics infrastructure. Python, Spark, Airflow, Snowflake. Support product and business analytics.",
            "source": "seed",
            "external_url": "https://notion.so/careers/data-engineer",
            "external_id": "seed_notion_de_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Machine Learning Engineer",
            "company_name": "Figma",
            "location": "Remote - USA",
            "description": "Build ML features for design tools. Python, TensorFlow, PyTorch. Work on auto-layout, smart selection, and content generation.",
            "source": "seed",
            "external_url": "https://figma.com/careers/ml-engineer",
            "external_id": "seed_figma_ml_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Data Scientist",
            "company_name": "Dropbox",
            "location": "Remote - USA",
            "description": "Drive product insights through data analysis. SQL, Python, R. A/B testing, causal inference, and predictive modeling.",
            "source": "seed",
            "external_url": "https://dropbox.com/careers/data-scientist",
            "external_id": "seed_dropbox_ds_001",
            "extraction_complete": True,
        },

        # Technology - Product & Design
        {
            "job_title": "Product Manager",
            "company_name": "Asana",
            "location": "San Francisco, CA",
            "description": "Own product roadmap for work management platform. Define features, prioritize backlog, work with engineering and design.",
            "source": "seed",
            "external_url": "https://asana.com/careers/product-manager",
            "external_id": "seed_asana_pm_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Product Designer",
            "company_name": "Linear",
            "location": "Remote - USA",
            "description": "Design workflows for engineering teams. Figma, prototyping, user research. Ship beautiful, functional product experiences.",
            "source": "seed",
            "external_url": "https://linear.app/careers/designer",
            "external_id": "seed_linear_design_001",
            "extraction_complete": True,
        },

        # Fintech
        {
            "job_title": "Software Engineer - Payments",
            "company_name": "Brex",
            "location": "New York, NY",
            "description": "Build payment processing systems for corporate cards. Java, Python, PostgreSQL. Handle high-value transactions with reliability.",
            "source": "seed",
            "external_url": "https://brex.com/careers/payments-engineer",
            "external_id": "seed_brex_payments_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Backend Engineer - Infrastructure",
            "company_name": "Plaid",
            "location": "San Francisco, CA",
            "description": "Build financial data APIs. Go, Kubernetes, PostgreSQL. Connect banks, fintechs, and consumers securely.",
            "source": "seed",
            "external_url": "https://plaid.com/careers/backend-engineer",
            "external_id": "seed_plaid_be_001",
            "extraction_complete": True,
        },

        # Enterprise Software
        {
            "job_title": "Solutions Engineer",
            "company_name": "Okta",
            "location": "Remote - USA",
            "description": "Help enterprise customers deploy identity solutions. Technical sales, demos, integrations. Work with Fortune 500 companies.",
            "source": "seed",
            "external_url": "https://okta.com/careers/solutions-engineer",
            "external_id": "seed_okta_se_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Integration Specialist",
            "company_name": "Workday",
            "location": "Pleasanton, CA",
            "description": "Configure and integrate HR/Finance systems. REST APIs, SOAP, ETL. Customer-facing technical implementation role.",
            "source": "seed",
            "external_url": "https://workday.com/careers/integration-specialist",
            "external_id": "seed_workday_int_001",
            "extraction_complete": True,
        },

        # Marketing & Sales Tech
        {
            "job_title": "Marketing Operations Specialist",
            "company_name": "HubSpot",
            "location": "Boston, MA",
            "description": "Manage marketing automation platform. Salesforce, APIs, SQL. Build campaigns, reports, and integrations.",
            "source": "seed",
            "external_url": "https://hubspot.com/careers/marketing-ops",
            "external_id": "seed_hubspot_mops_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Customer Success Engineer",
            "company_name": "Segment",
            "location": "San Francisco, CA",
            "description": "Help customers implement data pipelines. JavaScript, APIs, customer training. Technical post-sales support.",
            "source": "seed",
            "external_url": "https://segment.com/careers/cse",
            "external_id": "seed_segment_cse_001",
            "extraction_complete": True,
        },

        # Security
        {
            "job_title": "Security Engineer",
            "company_name": "Snyk",
            "location": "Remote - USA",
            "description": "Build developer security tools. Go, Kubernetes, cloud security. Scan code, containers, and infrastructure for vulnerabilities.",
            "source": "seed",
            "external_url": "https://snyk.io/careers/security-engineer",
            "external_id": "seed_snyk_sec_001",
            "extraction_complete": True,
        },

        # Education Tech
        {
            "job_title": "Software Engineer - Platform",
            "company_name": "Coursera",
            "location": "Mountain View, CA",
            "description": "Build online learning platform. Python, React, microservices. Serve millions of learners worldwide.",
            "source": "seed",
            "external_url": "https://coursera.org/careers/platform-engineer",
            "external_id": "seed_coursera_plat_001",
            "extraction_complete": True,
        },

        # Additional variety for search testing
        {
            "job_title": "Engineering Manager",
            "company_name": "Netlify",
            "location": "Remote - USA",
            "description": "Lead team building web deployment platform. Manage engineers, set roadmap, ship features. Experience with JavaScript, Go, Kubernetes.",
            "source": "seed",
            "external_url": "https://netlify.com/careers/engineering-manager",
            "external_id": "seed_netlify_em_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Principal Engineer",
            "company_name": "Vercel",
            "location": "Remote - Worldwide",
            "description": "Define technical vision for frontend cloud platform. Next.js, React, edge computing. Architect systems at global scale.",
            "source": "seed",
            "external_url": "https://vercel.com/careers/principal-engineer",
            "external_id": "seed_vercel_principal_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Technical Program Manager",
            "company_name": "Slack",
            "location": "San Francisco, CA",
            "description": "Coordinate cross-functional engineering initiatives. Drive platform integrations, APIs, and developer ecosystem projects.",
            "source": "seed",
            "external_url": "https://slack.com/careers/tpm",
            "external_id": "seed_slack_tpm_001",
            "extraction_complete": True,
        },
        {
            "job_title": "QA Engineer",
            "company_name": "Discord",
            "location": "Remote - USA",
            "description": "Build automated testing for real-time communication platform. Selenium, Cypress, performance testing. Ensure quality at scale.",
            "source": "seed",
            "external_url": "https://discord.com/careers/qa-engineer",
            "external_id": "seed_discord_qa_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Mobile Engineer - iOS",
            "company_name": "Duolingo",
            "location": "Pittsburgh, PA",
            "description": "Build language learning app for iOS. Swift, SwiftUI, UIKit. Ship features to 50M+ active users.",
            "source": "seed",
            "external_url": "https://duolingo.com/careers/ios-engineer",
            "external_id": "seed_duolingo_ios_001",
            "extraction_complete": True,
        },
        {
            "job_title": "Mobile Engineer - Android",
            "company_name": "Reddit",
            "location": "Remote - USA",
            "description": "Build Reddit mobile experience. Kotlin, Jetpack Compose, Android SDK. Optimize performance and user engagement.",
            "source": "seed",
            "external_url": "https://reddit.com/careers/android-engineer",
            "external_id": "seed_reddit_android_001",
            "extraction_complete": True,
        },
    ]

    return seed_jobs
