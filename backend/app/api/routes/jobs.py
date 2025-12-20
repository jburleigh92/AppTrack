import logging
from typing import List, Dict, Any, Set, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume, ResumeData
from app.db.models.job_posting import JobPosting
from app.services.scraping.greenhouse_api import fetch_all_greenhouse_jobs, fetch_greenhouse_job
from app.core.config import settings
from app.services.intent_analyzer import IntentAnalyzer, IntentProfile, score_intent_alignment

router = APIRouter()
logger = logging.getLogger(__name__)

# Greenhouse company boards to query for manual job search
# Expanded list for broad discovery across industries
# Format: company-slug as used in Greenhouse boards API
# Source: Known public Greenhouse boards (verified Feb 2024)
TARGET_COMPANIES = [
    # Technology - Consumer
    "airbnb", "stripe", "shopify", "coinbase", "dropbox", "instacart",
    "robinhood", "doordash", "gitlab", "notion", "figma", "canva",
    "discord", "duolingo", "reddit", "twitch", "zoom", "slack",
    "asana", "airtable", "miro", "webflow", "vercel", "netlify",

    # Technology - Infrastructure & Cloud
    "databricks", "snowflake", "confluent", "hashicorp", "mongodb",
    "elastic", "planetscale", "cockroachdb", "cloudflare", "fastly",
    "digitalocean", "linode", "fly-io", "render", "railway",

    # Technology - Security & DevOps
    "snyk", "lacework", "wiz", "orca-security", "checkmarx",
    "pagerduty", "datadog", "newrelic", "sentry", "launchdarkly",

    # Technology - Data & Analytics
    "segment", "amplitude", "mixpanel", "heap", "looker",
    "dbt-labs", "fivetran", "airbyte", "hightouch", "census",

    # Fintech & Payments
    "plaid", "chime", "square", "cashapp", "affirm", "klarna",
    "brex", "ramp", "mercury", "unit", "column", "increase",
    "marqeta", "paystack", "checkout", "adyen",

    # Healthcare & Biotech
    "23andme", "color", "tempus", "guardant-health", "grail",
    "moderna", "ginkgo-bioworks", "recursion", "insitro",
    "benchling", "science-37", "headway", "cedar", "devoted-health",

    # E-commerce & Retail
    "faire", "goPuff", "getir", "gorillas", "flink", "jokr",
    "checkout", "bolt", "fast", "primer", "recurly",

    # Real Estate & PropTech
    "opendoor", "redfin", "compass", "zillow", "trulia",
    "divvy-homes", "flyhomes", "properly", "homelight",

    # Transportation & Logistics
    "uber", "lyft", "cruise", "waymo", "nuro", "zoox",
    "flexport", "convoy", "flock-freight", "shippo", "easypost",

    # Climate & Energy
    "climeworks", "carbon-engineering", "twelve", "stripe-climate",
    "wren", "pachama", "watershed", "persefoni",

    # Education & EdTech
    "coursera", "udemy", "outschool", "masterclass", "skillshare",
    "apollo", "2u", "chegg", "quizlet", "brainly",

    # Enterprise Software
    "servicenow", "workday", "okta", "auth0", "onelogin",
    "mulesoft", "talend", "informatica", "collibra", "alation",
    "gong", "chorus", "clari", "outreach", "salesloft",

    # Marketing & Sales Tech
    "hubspot", "marketo", "iterable", "braze", "customer-io",
    "segment-io", "optimizely", "ab-tasty", "vwo",

    # Productivity & Collaboration
    "monday", "clickup", "coda", "roam", "obsidian",
    "linear", "height", "shortcut", "cycle",

    # Developer Tools
    "github", "gitlab", "bitbucket", "circleci", "travisci",
    "buildkite", "semaphore", "codecov", "sonarqube",

    # Design & Creative
    "invision", "framer", "principle", "sketch", "abstract",
    "zeplin", "marvel", "balsamiq", "uxpin",

    # Communication
    "front", "superhuman", "hey", "fastmail", "protonmail",
    "intercom", "drift", "qualified", "chili-piper",
]

# Comprehensive technical skills dictionary for job extraction
# Organized by category for maintainability
TECHNICAL_SKILLS = {
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby",
    "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Shell", "Bash",

    # Web Frameworks & Libraries
    "React", "Angular", "Vue", "Svelte", "Next.js", "Nuxt", "Django", "Flask",
    "FastAPI", "Express", "Node.js", "Spring", "Spring Boot", "Rails", "Laravel",
    "ASP.NET", "jQuery", "Bootstrap", "Tailwind", "Material-UI", "Redux", "GraphQL",

    # Databases & Storage
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
    "DynamoDB", "Oracle", "SQL Server", "MariaDB", "Neo4j", "CouchDB", "InfluxDB",
    "Snowflake", "BigQuery", "Redshift",

    # Cloud & Infrastructure
    "AWS", "Azure", "GCP", "Google Cloud", "Heroku", "DigitalOcean", "Vercel",
    "Netlify", "Cloudflare", "Lambda", "EC2", "S3", "CloudFormation", "ARM",

    # DevOps & Tools
    "Docker", "Kubernetes", "K8s", "Terraform", "Ansible", "Jenkins", "CircleCI",
    "GitHub Actions", "GitLab CI", "Travis CI", "Prometheus", "Grafana", "Datadog",
    "New Relic", "Splunk", "ELK", "Kafka", "RabbitMQ", "Nginx", "Apache",

    # Data & ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Keras", "Scikit-learn",
    "Pandas", "NumPy", "Jupyter", "Spark", "Hadoop", "Airflow", "dbt", "Tableau",
    "Power BI", "Looker", "ML", "AI", "NLP", "Computer Vision", "LLM",

    # Mobile
    "iOS", "Android", "React Native", "Flutter", "SwiftUI", "UIKit", "Jetpack Compose",

    # Testing & Quality
    "Jest", "Pytest", "JUnit", "Selenium", "Cypress", "TestNG", "Mocha", "Chai",
    "TDD", "CI/CD", "QA",

    # Methodologies & Concepts
    "Agile", "Scrum", "Kanban", "Microservices", "REST", "API", "gRPC", "WebSockets",
    "OAuth", "SAML", "JWT", "Git", "GitHub", "GitLab", "Bitbucket", "JIRA",
    "Confluence", "Slack", "Linux", "Unix", "Windows", "macOS",

    # Security
    "Security", "Cybersecurity", "Penetration Testing", "OWASP", "Encryption", "SSL",
    "TLS", "VPN", "Firewall", "IAM",

    # Emerging Tech
    "Blockchain", "Ethereum", "Solidity", "Web3", "NFT", "Cryptocurrency", "Bitcoin",
    "AR", "VR", "IoT", "Edge Computing", "Serverless",

    # Soft Skills (Technical Adjacent)
    "Leadership", "Mentoring", "Architecture", "System Design", "Problem Solving",
    "Communication", "Collaboration", "Code Review"
}

# Skill tier weights for differentiated scoring
# Higher weight = more valuable/distinguishing skill
SKILL_TIERS = {
    # Tier 1: Core distinguishing skills (weight: 3.0)
    "tier1": {
        "Rust", "Go", "Scala", "Elixir", "Kubernetes", "Terraform", "Machine Learning",
        "Deep Learning", "TensorFlow", "PyTorch", "System Design", "Architecture",
        "Distributed Systems", "Microservices", "GraphQL", "gRPC"
    },
    # Tier 2: Important technical skills (weight: 2.0)
    "tier2": {
        "Python", "Java", "TypeScript", "React", "Angular", "Vue", "Django", "Spring",
        "PostgreSQL", "MongoDB", "Redis", "AWS", "Azure", "GCP", "Docker",
        "CI/CD", "Kafka", "Elasticsearch", "Node.js", "FastAPI"
    },
    # Tier 3: Common skills (weight: 1.0)
    "tier3": {
        "JavaScript", "HTML", "CSS", "SQL", "Git", "API", "REST", "Agile",
        "Scrum", "JIRA", "Linux", "Bash"
    }
}

# Role type patterns for intelligent matching
ROLE_TYPES = {
    "ic_engineer": [
        "Software Engineer", "Engineer", "Developer", "Programmer",
        "SWE", "SDE", "Backend Engineer", "Frontend Engineer", "Full Stack Engineer",
        "Platform Engineer", "Infrastructure Engineer"
    ],
    "manager": [
        "Engineering Manager", "Manager", "Team Lead", "Tech Lead Manager",
        "Director", "VP", "Head of", "Chief"
    ],
    "staff_plus": [
        "Staff Engineer", "Staff Software Engineer", "Principal Engineer",
        "Distinguished Engineer", "Fellow", "Architect"
    ],
    "specialist": [
        "Data Scientist", "Data Engineer", "ML Engineer", "Security Engineer",
        "DevOps Engineer", "SRE", "QA Engineer", "Test Engineer"
    ]
}

# Seniority level patterns
SENIORITY_LEVELS = {
    "junior": ["Junior", "Entry", "Associate", "I", "1", "Graduate", "New Grad"],
    "mid": ["Mid", "II", "2", "Software Engineer"],  # Default
    "senior": ["Senior", "Sr", "III", "3", "Lead"],
    "staff_plus": ["Staff", "Principal", "Distinguished", "Fellow", "IV", "V", "4", "5"]
}


def _get_skill_weight(skill: str) -> float:
    """Get weight for a skill based on tier."""
    skill_lower = skill.lower()
    for tier_skill in SKILL_TIERS["tier1"]:
        if tier_skill.lower() == skill_lower:
            return 3.0
    for tier_skill in SKILL_TIERS["tier2"]:
        if tier_skill.lower() == skill_lower:
            return 2.0
    return 1.0  # Tier 3 or unlisted


def _detect_role_type(title: str) -> str:
    """Detect role type from job title."""
    title_lower = title.lower()

    # Check manager first (most specific)
    for pattern in ROLE_TYPES["manager"]:
        if pattern.lower() in title_lower:
            return "manager"

    # Check staff+ (also specific)
    for pattern in ROLE_TYPES["staff_plus"]:
        if pattern.lower() in title_lower:
            return "staff_plus"

    # Check specialist
    for pattern in ROLE_TYPES["specialist"]:
        if pattern.lower() in title_lower:
            return "specialist"

    # Default to IC engineer
    for pattern in ROLE_TYPES["ic_engineer"]:
        if pattern.lower() in title_lower:
            return "ic_engineer"

    return "unknown"


def _detect_seniority(title: str) -> str:
    """Detect seniority level from job title."""
    title_lower = title.lower()

    for pattern in SENIORITY_LEVELS["staff_plus"]:
        if pattern.lower() in title_lower:
            return "staff_plus"

    for pattern in SENIORITY_LEVELS["senior"]:
        if pattern.lower() in title_lower:
            return "senior"

    for pattern in SENIORITY_LEVELS["junior"]:
        if pattern.lower() in title_lower:
            return "junior"

    return "mid"  # Default


def _detect_user_target_role(resume_data: Any) -> Dict[str, str]:
    """
    Infer user's target role type and seniority from resume.

    Uses most recent job title and experience level.
    """
    # Try to get most recent title from experience
    target_role_type = "ic_engineer"  # Default
    target_seniority = "mid"  # Default

    if hasattr(resume_data, 'experience') and resume_data.experience:
        # Get first/most recent experience entry
        exp = resume_data.experience[0] if isinstance(resume_data.experience, list) else resume_data.experience
        if isinstance(exp, dict) and 'title' in exp:
            recent_title = exp['title']
            target_role_type = _detect_role_type(recent_title)
            target_seniority = _detect_seniority(recent_title)

    return {
        "role_type": target_role_type,
        "seniority": target_seniority
    }


def _calculate_weighted_skill_score(matched_skills: Set[str], job_skills: Set[str]) -> float:
    """
    Calculate weighted skill match score.

    Returns score from 0-100 based on weighted skill overlap.
    """
    if not job_skills or not matched_skills:
        return 0.0

    # Calculate weighted intersection
    matched_weight = sum(_get_skill_weight(skill) for skill in matched_skills)
    total_job_weight = sum(_get_skill_weight(skill) for skill in job_skills)

    if total_job_weight == 0:
        return 0.0

    base_score = (matched_weight / total_job_weight) * 100
    return min(base_score, 100.0)


def _calculate_composite_score(
    base_skill_score: float,
    user_target: Dict[str, str],
    job_role_type: str,
    job_seniority: str,
    location: str,
    company: str,
    intent_profile: Optional[IntentProfile] = None,
    job_title: str = "",
    job_description: str = ""
) -> Dict[str, Any]:
    """
    Calculate composite match score with multiple factors including career intent.

    Returns dict with total score and breakdown.
    """
    score_components = {"base_skill_match": base_skill_score}
    total_score = base_skill_score

    # Intent alignment scoring (MOST IMPORTANT - 30% weight)
    # This is the new layer that understands what role the resume is targeting
    intent_score = 0.0
    intent_multiplier = 1.0

    if intent_profile and (job_title or job_description):
        intent_alignment = score_intent_alignment(
            job_title=job_title,
            job_description=job_description,
            intent_profile=intent_profile
        )

        intent_score = intent_alignment["alignment_score"]
        score_components["intent_alignment_score"] = intent_score
        score_components["intent_archetype_match"] = intent_alignment["archetype_score"]
        score_components["intent_orientation_match"] = intent_alignment["orientation_score"]

        # Intent score affects the final score in two ways:
        # 1. Direct contribution (up to +30 points for perfect intent match)
        intent_contribution = (intent_score / 100) * 30
        total_score += intent_contribution

        # 2. Multiplier effect on skill matching (0.7x to 1.3x)
        # Strong intent match boosts skill score, weak match diminishes it
        intent_multiplier = 0.7 + (intent_score / 100) * 0.6
        adjusted_skill_score = base_skill_score * intent_multiplier
        total_score = total_score - base_skill_score + adjusted_skill_score
        score_components["intent_adjusted_skills"] = adjusted_skill_score - base_skill_score

        # Apply deprioritization penalties
        if intent_alignment["deprioritization_penalty"] > 0:
            penalty = intent_alignment["deprioritization_penalty"]
            score_components["intent_deprioritization_penalty"] = -penalty
            total_score -= penalty

    # Role type alignment bonus (reduced weight since intent covers this better)
    if user_target["role_type"] == job_role_type:
        role_bonus = base_skill_score * 0.10  # Reduced from 0.15
        score_components["role_alignment_bonus"] = role_bonus
        total_score += role_bonus
    elif job_role_type == "manager" and user_target["role_type"] == "ic_engineer":
        # Penalize manager roles for IC candidates
        role_penalty = base_skill_score * 0.20  # Reduced from 0.30
        score_components["role_misalignment_penalty"] = -role_penalty
        total_score -= role_penalty

    # Seniority alignment bonus (+8% if match, -12% if too far off)
    seniority_order = {"junior": 0, "mid": 1, "senior": 2, "staff_plus": 3}
    user_level = seniority_order.get(user_target["seniority"], 1)
    job_level = seniority_order.get(job_seniority, 1)
    level_diff = abs(user_level - job_level)

    if level_diff == 0:
        seniority_bonus = base_skill_score * 0.08  # Reduced from 0.10
        score_components["seniority_match_bonus"] = seniority_bonus
        total_score += seniority_bonus
    elif level_diff > 1:
        seniority_penalty = base_skill_score * 0.12  # Reduced from 0.15
        score_components["seniority_gap_penalty"] = -seniority_penalty
        total_score -= seniority_penalty

    # Location fit bonus (+5% for USA/Remote)
    location_lower = location.lower()
    if "remote" in location_lower and ("usa" in location_lower or "united states" in location_lower):
        location_bonus = base_skill_score * 0.05
        score_components["premium_location_bonus"] = location_bonus
        total_score += location_bonus

    # Cap at 100
    total_score = min(total_score, 100.0)
    total_score = max(total_score, 0.0)

    return {
        "total_score": round(total_score, 1),
        "components": score_components,
        "intent_score": round(intent_score, 1) if intent_profile else 0.0
    }


def _extract_skills_from_job(text: str) -> Set[str]:
    """
    Extract technical skills from job description.

    Uses comprehensive skill dictionary to find ALL technical skills mentioned,
    not limited to candidate's resume skills.

    Returns:
        Set of skills found in job description (preserves original case from dictionary)
    """
    if not text:
        return set()

    text_lower = text.lower()
    found_skills = set()

    for skill in TECHNICAL_SKILLS:
        # Use word boundary matching to avoid false positives
        # e.g., "Go" should match "Go programming" but not "Google"
        skill_lower = skill.lower()

        # Simple substring match (can be improved with regex word boundaries)
        if skill_lower in text_lower:
            found_skills.add(skill)

    return found_skills


def _infer_skills_from_title(title: str) -> Set[str]:
    """
    Infer likely technical skills from job title.

    Aggressively extracts skills to maximize matching when job content unavailable.
    Uses multi-pass approach: direct skill mentions, role keywords, seniority hints.
    """
    if not title:
        return set()

    title_lower = title.lower()
    inferred = set()

    # Soft skills to exclude from direct title matching (too generic, cause false positives)
    SOFT_SKILLS = {
        "Leadership", "Mentoring", "Problem Solving", "Communication",
        "Collaboration", "Code Review"
    }

    # PASS 1: Direct skill mentions in title with word boundaries
    # (e.g., "Python Engineer", "React Developer")
    # Excludes soft skills to prevent matching non-technical roles
    import re
    for skill in TECHNICAL_SKILLS:
        if skill in SOFT_SKILLS:
            continue  # Skip soft skills in title matching

        # Use word boundary to prevent false positives (e.g., "digital" matching "Git")
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, title_lower):
            inferred.add(skill)

    # PASS 2: Role-based inference with expanded, comprehensive skill sets
    role_skills = {
        # Frontend roles
        "frontend": {"JavaScript", "TypeScript", "React", "Angular", "Vue", "HTML", "CSS",
                     "Redux", "Webpack", "Git", "API", "Web"},
        "front end": {"JavaScript", "TypeScript", "React", "Angular", "Vue", "HTML", "CSS",
                      "Redux", "Webpack", "Git", "API", "Web"},
        "ui": {"JavaScript", "TypeScript", "React", "HTML", "CSS", "Design"},
        "web developer": {"JavaScript", "HTML", "CSS", "React", "Node.js", "API", "Git"},

        # Backend roles
        "backend": {"API", "Database", "SQL", "Python", "Java", "Go", "Node.js",
                    "Microservices", "REST", "PostgreSQL", "Redis", "Git"},
        "back end": {"API", "Database", "SQL", "Python", "Java", "Go", "Node.js",
                     "Microservices", "REST", "PostgreSQL", "Redis", "Git"},
        "api": {"API", "REST", "GraphQL", "Microservices", "Database", "Python", "Node.js"},

        # Fullstack roles
        "fullstack": {"JavaScript", "TypeScript", "Python", "React", "Node.js", "API",
                      "Database", "SQL", "PostgreSQL", "Git", "HTML", "CSS", "REST"},
        "full stack": {"JavaScript", "TypeScript", "Python", "React", "Node.js", "API",
                       "Database", "SQL", "PostgreSQL", "Git", "HTML", "CSS", "REST"},
        "full-stack": {"JavaScript", "TypeScript", "Python", "React", "Node.js", "API",
                       "Database", "SQL", "PostgreSQL", "Git", "HTML", "CSS", "REST"},

        # Generic engineering (broadest match - catches "Senior Engineer", "Staff Engineer")
        "software engineer": {"Python", "JavaScript", "Java", "Git", "API", "Database", "SQL",
                              "Problem Solving", "System Design", "Agile"},
        "engineer": {"Git", "Problem Solving", "System Design", "API", "Database"},
        "developer": {"Git", "API", "Database", "Problem Solving"},
        "programmer": {"Git", "Problem Solving"},

        # DevOps/Infrastructure
        "devops": {"Docker", "Kubernetes", "CI/CD", "AWS", "Linux", "Terraform", "Git",
                   "Jenkins", "Python", "Bash"},
        "sre": {"Kubernetes", "Docker", "Monitoring", "Linux", "Python", "AWS", "Terraform"},
        "infrastructure": {"Docker", "Kubernetes", "Terraform", "AWS", "Linux", "Networking"},
        "platform": {"Kubernetes", "Docker", "CI/CD", "AWS", "Infrastructure", "Python"},

        # Data roles
        "data engineer": {"Python", "SQL", "Spark", "Airflow", "Kafka", "Database", "ETL"},
        "data scientist": {"Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Statistics"},
        "data": {"Python", "SQL", "Database", "Analytics"},
        "analytics": {"SQL", "Python", "Tableau", "Analytics"},

        # ML/AI roles
        "ml": {"Python", "Machine Learning", "TensorFlow", "PyTorch", "Scikit-learn"},
        "machine learning": {"Python", "Machine Learning", "TensorFlow", "PyTorch", "Deep Learning"},
        "ai": {"Python", "Machine Learning", "TensorFlow", "PyTorch", "AI"},

        # Mobile
        "mobile": {"iOS", "Android", "React Native", "Flutter", "Mobile"},
        "ios": {"Swift", "iOS", "SwiftUI", "UIKit", "Xcode"},
        "android": {"Kotlin", "Java", "Android", "Jetpack Compose"},

        # Security
        "security": {"Security", "Cybersecurity", "Encryption", "Networking", "Linux"},

        # Cloud
        "cloud": {"AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform"},
    }

    for keyword, skills in role_skills.items():
        if keyword in title_lower:
            inferred.update(skills)

    # PASS 3: Return empty if no technical role detected
    # This filters out non-technical roles (Communications, HR, Sales, etc.)
    # Better to have no match than false positive matches
    return inferred


def _generate_match_explanation(
    matched_skills: Set[str],
    job_title: str,
    job_role_type: str,
    job_seniority: str,
    user_target: Dict[str, str],
    score_components: Dict[str, float],
    intent_profile: Optional[IntentProfile] = None
) -> str:
    """
    Generate human-readable match explanation.

    Focus on WHY this job is a good match for the candidate's career intent,
    not just WHAT skills matched.
    """
    explanation_parts = []

    # INTENT FIT (most important - lead with this if strong)
    if intent_profile and "intent_alignment_score" in score_components:
        intent_score = score_components["intent_alignment_score"]

        if intent_score >= 70:
            # Strong intent match - make this the headline
            archetype_name = intent_profile.primary_archetype.replace("_", " ").title()
            explanation_parts.append(f"Strong fit for {archetype_name} role")
        elif intent_score >= 50:
            # Moderate match
            archetype_name = intent_profile.primary_archetype.replace("_", " ").title()
            explanation_parts.append(f"Aligns with {archetype_name} background")
        # Weak intent match (<50) - don't highlight it, let skills speak

    # SKILLS (supporting evidence)
    # Prioritize tier 1 skills (most distinctive)
    tier1_matches = [s for s in matched_skills if _get_skill_weight(s) == 3.0]
    tier2_matches = [s for s in matched_skills if _get_skill_weight(s) == 2.0]
    other_matches = [s for s in matched_skills if _get_skill_weight(s) == 1.0]

    # Add skill evidence
    if tier1_matches:
        standout = sorted(tier1_matches)[:3]  # Top 3
        explanation_parts.append(f"leveraging {', '.join(standout)}")
    elif tier2_matches:
        core = sorted(tier2_matches)[:4]  # Top 4
        explanation_parts.append(f"uses {', '.join(core)}")
    else:
        # Fallback to other matches
        basics = sorted(other_matches)[:3]
        if basics:
            explanation_parts.append(f"involves {', '.join(basics)}")

    # WORK ORIENTATION SIGNALS (add nuance if intent available)
    if intent_profile and "intent_orientation_match" in score_components:
        orientation = intent_profile.work_orientation

        # Highlight orientation if it's a defining characteristic (>0.7)
        if orientation.get("customer_facing", 0) > 0.7:
            if "customer" in job_title.lower() or "solutions" in job_title.lower():
                explanation_parts.append("customer-facing focus")

        if orientation.get("integration_heavy", 0) > 0.7:
            if "integration" in job_title.lower() or "platform" in job_title.lower():
                explanation_parts.append("integration-focused work")

    # SENIORITY FIT
    if "seniority_match_bonus" in score_components:
        explanation_parts.append(f"{job_seniority}-level")

    # WARNINGS (deprioritized roles or misalignments)
    if "intent_deprioritization_penalty" in score_components:
        # Subtle warning without being too negative
        explanation_parts.append("(different focus area)")
    elif "role_misalignment_penalty" in score_components:
        explanation_parts.append("(management-focused)")

    return "; ".join(explanation_parts) if explanation_parts else "Skill overlap"


def _passes_role_domain_filter(job_title: str) -> bool:
    """
    Configuration-driven role domain filter.

    Checks if job title matches the active role domain requirements.
    This is NOT hard-coded - configured via settings.ACTIVE_ROLE_DOMAIN.

    Returns:
        True if job passes filter, False if should be excluded
    """
    active_domain = settings.ACTIVE_ROLE_DOMAIN
    domain_config = settings.ROLE_DOMAINS.get(active_domain, {})

    require_keywords = domain_config.get("require_any", [])
    exclude_keywords = domain_config.get("exclude_any", [])

    title_lower = job_title.lower()

    # If exclude keywords present, check exclusions first
    for exclude_word in exclude_keywords:
        if exclude_word.lower() in title_lower:
            return False

    # If require keywords specified, check requirements
    if require_keywords:
        for require_word in require_keywords:
            if require_word.lower() in title_lower:
                return True
        return False  # No required keyword found

    # Default: pass if no constraints
    return True


def _enrich_job_with_description(company_slug: str, job_id: str, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch full job description for a single job.

    Used for selective enrichment of top candidates.
    Caches in job dict to avoid redundant API calls.

    Returns:
        Updated job dict with 'content' field, or None if fetch fails
    """
    if job.get("content"):
        return job  # Already has content

    # Fetch full job details
    full_job = fetch_greenhouse_job(company_slug, str(job_id))

    if full_job and full_job.get("content"):
        job["content"] = full_job["content"]
        job["enriched"] = True
        return job

    return None


def _extract_skills_from_text(text: str, known_skills: List[str]) -> List[str]:
    """
    Extract skills from job description text by matching against known skills.
    Case-insensitive matching.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = []

    for skill in known_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


@router.get("/search")
def search_jobs(
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Universal job search - no resume required.

    Searches the local job_postings index by keyword, location, or company.
    Returns unscored, unfiltered job listings for browsing.

    Query Parameters:
        keyword: Search in job title (e.g., "engineer", "python", "backend")
        location: Filter by location (e.g., "remote", "san francisco", "usa")
        company: Filter by specific company name (e.g., "stripe", "airbnb")

    Returns:
        List of jobs matching search criteria, sorted by recency (newest first)
    """
    logger.info(
        "job_search.start",
        extra={
            "keyword": keyword,
            "location": location,
            "company": company
        }
    )

    # Query local job_postings table - NO external API calls
    query = db.query(JobPosting)

    # Apply filters using SQL ILIKE for case-insensitive matching
    if keyword:
        query = query.filter(JobPosting.job_title.ilike(f'%{keyword}%'))

    if location:
        query = query.filter(JobPosting.location.ilike(f'%{location}%'))

    if company:
        query = query.filter(JobPosting.company_name.ilike(f'%{company}%'))

    # Order by newest first, limit to 100 results for performance
    jobs = query.order_by(JobPosting.created_at.desc()).limit(100).all()

    # Convert ORM objects to API response format with traceability fields
    filtered_jobs = []
    for job in jobs:
        filtered_jobs.append({
            "id": str(job.id),
            "title": job.job_title,
            "company": job.company_name,
            "url": job.external_url or "",
            "location": job.location or "Location not specified",
            "description": (job.description[:200] + "...") if job.description else "",
            "source": job.source or "unknown",
            "industry": job.industry,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "source_query": job.source_query,
        })

    logger.info(
        "job_search.result",
        extra={
            "jobs_returned": len(filtered_jobs),
            "keyword": keyword,
            "location": location,
            "company": company
        }
    )

    return filtered_jobs


@router.get("/recommended")
def get_recommended_jobs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    AI-powered job recommendations based on active resume.

    Requires active resume with complete parsing. Uses skill matching
    and career intent analysis to provide personalized job recommendations.

    This endpoint preserves the original /discover logic but is now
    explicitly positioned as an optional enhancement to basic job search.

    Raises:
        404: No active resume found
        400: Resume parsing not complete

    Returns:
        List of jobs with match scores, ranked by relevance
    """
    # Get active resume
    resume = db.query(Resume).filter(Resume.is_active == True).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="No active resume found. Please upload a resume first."
        )

    # Get resume data
    resume_data = db.query(ResumeData).filter(
        ResumeData.resume_id == resume.id
    ).first()

    if not resume_data or not resume_data.extraction_complete:
        raise HTTPException(
            status_code=400,
            detail="Resume parsing not complete"
        )

    # Extract skills from resume
    user_skills = resume_data.skills if resume_data.skills else []
    user_skills_set = set(skill.lower() for skill in user_skills) if user_skills else set()

    # Detect user's target role type and seniority
    user_target = _detect_user_target_role(resume_data)

    # Analyze resume intent for job matching
    intent_analyzer = IntentAnalyzer()
    intent_profile = intent_analyzer.analyze_resume_intent(
        resume_data={
            "skills": user_skills,
            "experience": resume_data.experience if resume_data.experience else [],
            "education": resume_data.education if resume_data.education else [],
            "summary": resume_data.summary if hasattr(resume_data, 'summary') else ""
        },
        db=db,
        resume_id=str(resume.id)
    )

    logger.info(
        "matcher.user_profile",
        extra={
            "target_role_type": user_target["role_type"],
            "target_seniority": user_target["seniority"],
            "skills_count": len(user_skills),
            "intent_archetype": intent_profile.primary_archetype,
            "intent_confidence": intent_profile.archetype_confidence
        }
    )

    # Fetch jobs from all target companies
    all_jobs = []
    for company_slug in TARGET_COMPANIES:
        company_jobs = fetch_all_greenhouse_jobs(company_slug)
        # Store company_slug in job for enrichment later
        for job in company_jobs:
            job["_company_slug"] = company_slug
        all_jobs.extend(company_jobs)

    # 1️⃣ ROLE DOMAIN GATE: Configuration-driven title filtering
    # Reduces candidate set before matching
    filtered_jobs = []
    eliminated_role_domain = 0

    for job in all_jobs:
        job_title = job.get("title", "")
        if _passes_role_domain_filter(job_title):
            filtered_jobs.append(job)
        else:
            eliminated_role_domain += 1

    # Log: Jobs after role domain filter
    logger.info(
        "matcher.start",
        extra={
            "jobs_received": len(all_jobs),
            "role_domain_filtered": eliminated_role_domain,
            "jobs_after_filter": len(filtered_jobs),
            "active_domain": settings.ACTIVE_ROLE_DOMAIN,
            "user_skills_count": len(user_skills),
            "resume_id": str(resume.id)
        }
    )

    if not filtered_jobs:
        logger.info(
            "Job discovery: all jobs filtered by role domain",
            extra={
                "resume_id": str(resume.id),
                "jobs_eliminated": eliminated_role_domain,
                "active_domain": settings.ACTIVE_ROLE_DOMAIN
            }
        )
        return []

    # 2️⃣ INITIAL TITLE-BASED MATCHING (to identify top candidates for enrichment)
    # Match jobs to user skills - track elimination reasons
    initial_candidates = []
    match_scores = []

    # Elimination counters
    eliminated_no_content = 0
    eliminated_no_resume_skills = 0
    eliminated_no_job_skills = 0
    eliminated_no_skill_match = 0

    for job in filtered_jobs:
        # Extract job details from Greenhouse API response
        job_id = job.get("id")
        job_title = job.get("title", "")
        company_name = job.get("company_name", "Unknown Company")
        location = job.get("location", {}).get("name", "Location not specified")
        absolute_url = job.get("absolute_url", "")

        # Get job content for skill matching (may be empty from list endpoint)
        job_content = job.get("content", "")

        # Track elimination: no title or content to analyze
        if not job_title and not job_content:
            eliminated_no_content += 1
            continue

        # Track elimination: no resume skills
        if not user_skills:
            eliminated_no_resume_skills += 1
            continue

        # Extract ALL technical skills from job description (if available)
        job_skills_extracted = _extract_skills_from_job(job_content) if job_content else set()

        # CRITICAL: Greenhouse list endpoint doesn't include 'content' field
        # Fall back to title-based skill inference for all jobs
        title_skills = _infer_skills_from_title(job_title)
        job_skills_extracted.update(title_skills)

        # Track elimination: no job skills found (even with title fallback)
        if not job_skills_extracted:
            eliminated_no_job_skills += 1
            continue

        # Calculate skill overlap with user resume
        job_skills_lower = set(skill.lower() for skill in job_skills_extracted)
        matched_skills = job_skills_lower.intersection(user_skills_set)

        # Track elimination: no skill match
        if not matched_skills:
            eliminated_no_skill_match += 1
            continue

        # Job passed all filters - calculate weighted skill score
        # Convert matched_skills back to original case for weight lookup
        matched_skills_cased = set()
        for skill_lower in matched_skills:
            for skill in job_skills_extracted:
                if skill.lower() == skill_lower:
                    matched_skills_cased.add(skill)
                    break

        # Calculate weighted skill match
        base_skill_score = _calculate_weighted_skill_score(matched_skills_cased, job_skills_extracted)

        # Detect job role type and seniority
        job_role_type = _detect_role_type(job_title)
        job_seniority = _detect_seniority(job_title)

        # Calculate composite score with role/seniority bonuses and intent alignment
        composite_result = _calculate_composite_score(
            base_skill_score,
            user_target,
            job_role_type,
            job_seniority,
            location,
            company_name,
            intent_profile=intent_profile,
            job_title=job_title,
            job_description=job_content
        )

        # Generate human-readable explanation
        match_reason = _generate_match_explanation(
            matched_skills_cased,
            job_title,
            job_role_type,
            job_seniority,
            user_target,
            composite_result["components"],
            intent_profile=intent_profile
        )

        # Store candidate for potential enrichment
        initial_candidates.append({
            "job": job,  # Keep original job object for enrichment
            "id": str(job_id),
            "title": job_title,
            "company": company_name,
            "url": absolute_url,
            "location": location,
            "match_reason": match_reason,
            "match_percentage": composite_result["total_score"],
            "initial_score": composite_result["total_score"],
            "base_skill_score": base_skill_score,
            "role_type": job_role_type,
            "seniority": job_seniority,
            "matched_skills": matched_skills_cased,
            "has_content": bool(job_content),
            "source": "greenhouse"
        })

    # 3️⃣ SELECTIVE ENRICHMENT: Fetch full descriptions for top N candidates
    # Sort candidates by initial score to identify top matches
    initial_candidates.sort(key=lambda x: x["initial_score"], reverse=True)

    enriched_count = 0
    enrichment_failed = 0
    candidates_to_enrich = initial_candidates[:settings.MAX_JOBS_TO_ENRICH]

    for candidate in candidates_to_enrich:
        if candidate["has_content"]:
            continue  # Already has content

        job_obj = candidate["job"]
        company_slug = job_obj.get("_company_slug")
        job_id = candidate["id"]

        enriched_job = _enrich_job_with_description(company_slug, job_id, job_obj)
        if enriched_job:
            # Re-extract skills from full description
            full_content = enriched_job.get("content", "")
            job_skills_full = _extract_skills_from_job(full_content)

            # Also include title skills
            title_skills = _infer_skills_from_title(candidate["title"])
            job_skills_full.update(title_skills)

            # Re-calculate match with full content
            job_skills_lower = set(skill.lower() for skill in job_skills_full)
            matched_skills = job_skills_lower.intersection(user_skills_set)

            if matched_skills:
                # Convert to cased skills for weighting
                matched_skills_cased = set()
                for skill_lower in matched_skills:
                    for skill in job_skills_full:
                        if skill.lower() == skill_lower:
                            matched_skills_cased.add(skill)
                            break

                # Re-calculate with weighted scoring
                base_skill_score = _calculate_weighted_skill_score(matched_skills_cased, job_skills_full)

                # Re-calculate composite score with enriched content
                composite_result = _calculate_composite_score(
                    base_skill_score,
                    user_target,
                    candidate["role_type"],
                    candidate["seniority"],
                    candidate["location"],
                    candidate["company"],
                    intent_profile=intent_profile,
                    job_title=candidate["title"],
                    job_description=full_content
                )

                # Re-generate explanation with enriched context
                new_reason = _generate_match_explanation(
                    matched_skills_cased,
                    candidate["title"],
                    candidate["role_type"],
                    candidate["seniority"],
                    user_target,
                    composite_result["components"],
                    intent_profile=intent_profile
                )

                # Update candidate with enriched data
                candidate["match_percentage"] = composite_result["total_score"]
                candidate["match_reason"] = new_reason
                candidate["base_skill_score"] = base_skill_score
                candidate["matched_skills"] = matched_skills_cased
                candidate["has_content"] = True
                candidate["enriched"] = True
                enriched_count += 1
            else:
                # Lost match after enrichment (initial match was weak)
                enrichment_failed += 1
        else:
            enrichment_failed += 1

    logger.info(
        "matcher.enrichment",
        extra={
            "candidates_total": len(initial_candidates),
            "candidates_enriched": enriched_count,
            "enrichment_failed": enrichment_failed,
            "max_to_enrich": settings.MAX_JOBS_TO_ENRICH
        }
    )

    # 4️⃣ SCORING GUARDRAILS: Cap scores for title-only matches
    matched_jobs = []
    for candidate in initial_candidates:
        score = candidate["match_percentage"]

        # Apply score cap if no full content
        if not candidate.get("has_content", False):
            score = min(score, settings.TITLE_ONLY_SCORE_CAP)
            candidate["match_percentage"] = score
            candidate["title_only_match"] = True

        # Only include if still has match after enrichment/capping
        if score > 0:
            # Build final job dict for response
            matched_jobs.append({
                "id": candidate["id"],
                "title": candidate["title"],
                "company": candidate["company"],
                "url": candidate["url"],
                "location": candidate["location"],
                "match_reason": candidate["match_reason"],
                "match_percentage": score,
                "description": candidate["job"].get("content", "")[:200] + "..." if candidate["job"].get("content") else "",
                "source": candidate["source"]
            })

    # 2️⃣ Log: Score distribution (after enrichment and guardrails)
    if matched_jobs:
        scores = [j["match_percentage"] for j in matched_jobs]
        logger.info(
            "matcher.scores",
            extra={
                "min": min(scores),
                "max": max(scores),
                "avg": sum(scores) / len(scores),
                "enriched_count": enriched_count
            }
        )
    else:
        logger.info("matcher.scores", extra={"status": "unavailable"})

    # 3️⃣ Log: Elimination reasons (counts)
    logger.info(
        "matcher.filtered",
        extra={
            "role_domain": eliminated_role_domain,
            "no_content": eliminated_no_content,
            "no_resume_skills": eliminated_no_resume_skills,
            "no_job_skills": eliminated_no_job_skills,
            "no_skill_match": eliminated_no_skill_match
        }
    )

    # Sort by location priority, then match percentage
    def location_priority(job):
        """
        Prioritize jobs by location: USA/Remote first, then international.
        Returns tuple: (location_score, match_percentage) for multi-level sorting.
        """
        location = job.get("location", "").lower()

        # Priority 1: USA + Remote
        if "remote" in location and ("usa" in location or "united states" in location or "us" in location):
            return (3, job["match_percentage"])

        # Priority 2: USA locations
        if "usa" in location or "united states" in location or "us" in location or any(
            state in location for state in ["california", "new york", "texas", "washington", "massachusetts"]
        ):
            return (2, job["match_percentage"])

        # Priority 3: Remote (any location)
        if "remote" in location:
            return (1, job["match_percentage"])

        # Priority 4: International
        return (0, job["match_percentage"])

    matched_jobs.sort(key=location_priority, reverse=True)

    # 4️⃣ Log: Final output count
    logger.info(
        "matcher.result",
        extra={
            "count": len(matched_jobs),
            "resume_id": str(resume.id)
        }
    )

    return matched_jobs
